"""Evidence-backed generic product facts and fixed, whole-sales-pack conversion.

Catalog text is descriptive data. Missing claims, package dimensions or origin
remain unknown, and never become proof through keyword matching.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from sys import intern

from . import catalog

D = Decimal
SOURCE = "restricted synthetic Valio Aimo challenge catalog"
# ISO 3166-1 alpha-2 / numeric identifiers present in the challenge catalog.
EU_CODES = dict(zip(
    "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split(),
    "040 056 100 191 196 203 208 233 246 250 276 300 348 372 380 428 440 442 470 528 616 620 642 703 705 724 752".split(),
))
EU = set(EU_CODES) | set(EU_CODES.values())
DIETS = {
    "lactose_free": {"FREE_FROM_LACTOSE"},
    "gluten_free": {"FREE_FROM_GLUTEN"},
    "vegetarian": {"VEGETARIAN", "VEGAN"},
    "vegan": {"VEGAN"},
    "egg_free": {"FREE_FROM_EGGS"},
    "soy_free": {"FREE_FROM_SOY"},
}
ORGANIC_LABELS = {"EU_ORGANIC_FARMING", "SOIL_ASSOCIATION_ORGANIC_SYMBOL"}
_INDEX_CATALOG = None
_SEARCH_INDEX = {}


def positive(value):
    """Read finite positive decimals without permitting NaN or guessed values."""
    try:
        value = D(str(value))
        return value if value.is_finite() and value > 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def finite_text(value, *, nonnegative=False):
    """Keep supplied measurements as exact JSON strings, including zero."""
    try:
        amount = D(str(value))
        if not amount.is_finite() or (nonnegative and amount < 0):
            return None
        return format(amount, "f")
    except (InvalidOperation, TypeError, ValueError):
        return None


def nutrition_facts(source):
    """Retain the declared basis and precision; never compare unlike bases."""
    result = []
    for row in source.get("nutritionalContent", []):
        if not isinstance(row, dict):
            continue
        value = finite_text(row.get("value"), nonnegative=True)
        basis = positive(row.get("basisQuantity"))
        if value is None or basis is None or not all(isinstance(row.get(k), str) and row[k] for k in ["id", "unit", "basisQuantityUnit"]):
            continue
        result.append({
            "id": row["id"], "value": value, "unit": row["unit"],
            "basis_quantity": format(basis, "f"), "basis_unit": row["basisQuantityUnit"],
            "precision": row.get("unitPrecision"),
            "serving_size": finite_text(row.get("servingSize"), nonnegative=True),
            "serving_unit": row.get("servingSizeUnit"),
            "daily_intake_percent": finite_text(row.get("dailyValueIntakePercent"), nonnegative=True),
        })
    return result


def comparable_prices(product, price):
    """EUR per proven physical dimension; no density or package-code guesses."""
    price = finite_text(price, nonnegative=True)
    result = {}
    for key, dimension in [("price_per_kg", "kg_per_sales_unit"), ("price_per_litre", "liters_per_sales_unit")]:
        capacity = positive(product.get(dimension))
        result[key] = format(D(price) / capacity, "f") if price is not None and capacity else None
    return result


def localized(rows):
    rows = [r for r in rows or [] if isinstance(r, dict) and r.get("value")]
    return next((r["value"] for r in rows if r.get("language") == "en"),
                next((r["value"] for r in rows if r.get("language") == "fi"), None))


def classification(s, name):
    return [v for c in s.get("classifications", []) if c.get("name") == name
            for v in c.get("values", []) if isinstance(v, dict)]


def normalize(pid):
    p = catalog.load_catalog().get(str(pid))
    if not p:
        raise ValueError("Product not found in local challenge catalog")
    s = p.get("synkkaData", {})
    name = localized(s.get("names")) or str(pid)
    sales = p.get("salesUnit")
    base = p.get("baseUnit")
    sizes = {positive(u.get("sizeInBaseUnits")) for u in p.get("units", [])
             if u.get("unitId") == sales}
    sizes.discard(None)
    # The identity baseUnit == salesUnit establishes a 1:1 ratio even if the
    # redundant units entry is absent. Conflicting declared values remain unknown.
    size = next(iter(sizes)) if len(sizes) == 1 else D(1) if not sizes and sales == base else None
    mass = None
    volume = None
    pieces = size if base == "ST" else None
    evidence = {}
    if base == "KG" and size:
        mass = size
        evidence["kg"] = "units.sizeInBaseUnits with baseUnit KG"
    elif size:
        weights = set()
        volumes = set()
        for conversion in s.get("unitConversions", []):
            if conversion.get("synkkaPackagingType") != "BASE_UNIT_OR_EACH":
                continue
            weight = conversion.get("netWeight", {})
            amount = positive(weight.get("value"))
            if amount and weight.get("unit") in {"KGM", "GRM"}:
                weights.add(amount / (1000 if weight["unit"] == "GRM" else 1))
            vol = conversion.get("volume", {})
            amount = positive(vol.get("value"))
            volume_factors = {"LTR": D(1), "MLT": D(".001"), "CLT": D(".01")}
            if amount and vol.get("unit") in volume_factors:
                volumes.add(amount * volume_factors[vol["unit"]])
        if len(weights) == 1:
            mass = next(iter(weights)) * size
            evidence["kg"] = "BASE_UNIT_OR_EACH.netWeight × units.sizeInBaseUnits"
        if len(volumes) == 1:
            volume = next(iter(volumes)) * size
            evidence["L"] = "BASE_UNIT_OR_EACH.volume × units.sizeInBaseUnits"
        elif not volumes and base == "ST":
            # Preserve the original gateway's explicit consumer-volume evidence.
            # Multipack expressions cannot be interpreted as consumer-unit volume.
            declarations = re.findall(r"\b(\d+(?:[.,]\d+)?)\s*(?:l|litres?|liters?)\b", name, re.I)
            if len(declarations) == 1 and not re.search(r"\b\d+\s*[x×*]\s*\d", name, re.I):
                amount = positive(declarations[0].replace(",", "."))
                if amount:
                    volume = amount * size
                    evidence["L"] = "supplier name: explicit consumer-unit litres × units.sizeInBaseUnits"
    conversion_issues = []
    # A supplier's explicit multipack mass can expose inconsistent source
    # dimensions, but is never used to establish a missing net-mass conversion.
    # Example: name 4x5kg, base net mass 20kg and sales size 4 conflict (80kg).
    multipacks = []
    for match in re.finditer(r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*[x×*]\s*(\d+(?:[.,]\d+)?)\s*(kg|g)\b", name, re.I):
        count = positive(match[1].replace(",", "."))
        each = positive(match[2].replace(",", "."))
        if count and each:
            multipacks.append(count * each / (1000 if match[3].lower() == "g" else 1))
    for match in re.finditer(r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(kg|g)\s*[x×*]\s*(\d+(?:[.,]\d+)?)(?![\w.,])", name, re.I):
        each = positive(match[1].replace(",", "."))
        count = positive(match[3].replace(",", "."))
        if count and each:
            multipacks.append(count * each / (1000 if match[2].lower() == "g" else 1))
    measured_kg = sales == base == "KG" and size == 1
    if mass and not measured_kg and len(multipacks) == 1 and mass != multipacks[0]:
        conversion_issues.append(
            f"Conflicting package mass: structured conversion gives {mass} kg per sales unit, while the supplier name declares a {multipacks[0]} kg multipack. Supplier clarification required."
        )
        mass = None
        evidence["kg"] = conversion_issues[-1]
    if pieces:
        evidence["pieces"] = "units.sizeInBaseUnits with baseUnit ST; one piece means one consumer unit"
    variable = s.get("variableUnit") is True
    if variable:
        mass = volume = pieces = None
        evidence = {"unavailable": "Variable-weight product has no fixed purchasing conversion"}
    origin = []
    for value in s.get("countriesOfOrigin", []):
        value = str(value).strip().upper()
        if value:
            origin.append(value.zfill(3) if value.isdigit() else value)
    top_origin = str(p.get("countryOfOrigin") or "").strip().upper()
    if top_origin:
        origin.append(EU_CODES.get(top_origin, top_origin))
    out = {
        "id": str(pid), "name": name, "brand": s.get("brand"),
        "manufacturer": [x.get("name") for x in s.get("producers", []) if x.get("name")],
        "vendor": p.get("vendorName"), "category": p.get("category"),
        "claims": sorted({v["id"] for v in classification(s, "nutritionalClaim") if v.get("id")}),
        "organic": True if any(v.get("id") in ORGANIC_LABELS for v in classification(s, "packagingMarkedLabel")) else None,
        "organic_evidence": sorted({v["id"] for v in classification(s, "packagingMarkedLabel") if v.get("id") in ORGANIC_LABELS}),
        "origin_codes": sorted(set(origin)),
        "origin_evidence": "synkkaData.countriesOfOrigin and catalog countryOfOrigin; conflicting records are retained",
        "ingredients": localized(s.get("keyIngredients")),
        "certifications": sorted({str(v.get("id")) for name in ["nutritionalClaim", "packagingMarkedLabel", "dietType", "dietTypeCode", "certification"] for v in classification(s, name) if v.get("id") in {"HALAL", "KOSHER", "NO_PORK"}}),
        "allergens": classification(s, "allergen") + classification(s, "nonAllergen"),
        "storage": localized(s.get("storageInstructions")),
        "min_storage_temperature": finite_text(s.get("minTemperature")),
        "max_storage_temperature": finite_text(s.get("maxTemperature")),
        "nutrition": nutrition_facts(s),
        # The supplied schema contains media IDs only and explicitly excludes
        # files. An ID is not a URL; never synthesize an image endpoint or photo.
        "image_url": None, "image_status": "not_supplied",
        "temperature_condition": p.get("temperatureCondition"),
        "source": SOURCE, "updated_at": s.get("lastUpdated"),
        "sales_unit": sales, "base_unit": base,
        "base_units_per_sales_unit": str(size) if size else None,
        "allowed_lot_size": str(p.get("allowedLotSize", 1)),
        "deleted": p.get("deleted", False), "variable_unit": variable,
        "deposits": p.get("deposits", []),
        "kg_per_sales_unit": str(mass) if mass else None,
        "liters_per_sales_unit": str(volume) if volume else None,
        "pieces_per_sales_unit": str(pieces) if pieces else None,
        "conversion_evidence": evidence, "conversion_issues": conversion_issues,
        "substitutes": [str(v["substituteProduct"]) for v in p.get("substitutions", []) if v.get("substituteProduct")],
    }
    out.update(catalog.supplemental().get(str(pid), {}))
    return out


def brand_matches(actual, requested):
    """Declared brand equality, never inferred manufacturer/brand-family links."""
    def clean(value):
        return re.sub(r"\s+", " ", str(value or "").replace("®", "").replace("™", "")).strip().casefold()
    return bool(clean(actual)) and clean(actual) == clean(requested)


def suitability(product, dietary=None, origin=None, required_brand=None, require_organic=False, excluded_ingredients=None):
    issues = []
    claims = set(product.get("claims", []))
    # GS1 allergen codes and FREE_FROM are explicit supplier declarations.
    # Missing records and UNDECLARED never establish allergy suitability.
    allergen_codes = {
        "lactose_free": {"ML"}, "milk_free": {"AM"}, "peanut_free": {"AP"},
        "nut_free": {"AN", "SA", "SH", "SC", "SP", "SW", "ST", "SR", "SM"},
        "egg_free": {"AE"}, "soy_free": {"AY"}, "fish_free": {"AF", "ABD", "ADQ"},
        "crustacean_free": {"AC"}, "mollusc_free": {"UM"},
        "celery_free": {"BC"}, "mustard_free": {"BM"}, "sesame_free": {"AS"},
        "sulphite_free": {"AU"}, "lupin_free": {"NL"},
        "gluten_free": {"AW", "UW", "GO", "GB", "NR", "GK", "GS"},
    }
    root_code = {key: next(iter(value)) for key, value in allergen_codes.items()}
    root_code.update(nut_free="AN", gluten_free="AW", fish_free="AF")
    declarations = product.get("allergens") or []
    text = str(product.get("name") or "") + " " + str(product.get("ingredients") or "")
    pork_found = bool(re.search(r"\b(?:pork|porcine|swine|bacon|prosciutto|pancetta|porsaan|sianliha|sian|sika|gris|flask|fläsk)\b", text, re.I))
    for diet in dietary or []:
        canonical = str(diet).lower().replace("-", "_").replace(" ", "_")
        label = canonical.replace("_", " ")
        codes = allergen_codes.get(canonical, set())
        contradicted = [v for v in declarations if v.get("id") in codes and v.get("unit") in {"CONTAINS", "MAY_CONTAIN"}]
        if contradicted:
            issues.append(f"Supplier declares contains or may contain an excluded allergen ({label}).")
            continue
        if canonical == "no_pork":
            pork_declared = any(v.get("id") == "PO" and v.get("unit") in {"CONTAINS", "MAY_CONTAIN"} for v in declarations)
            pork_absent = any(v.get("id") == "PO" and v.get("unit") == "FREE_FROM" for v in declarations)
            if pork_found or pork_declared:
                issues.append("Identified pork-containing product is excluded by no pork.")
            elif not pork_absent and not claims.intersection({"VEGAN", "VEGETARIAN", "NO_PORK"}) and "NO_PORK" not in product.get("certifications", []):
                issues.append("No explicit catalog evidence for no pork.")
        elif canonical in {"halal", "kosher"}:
            if canonical.upper() not in product.get("certifications", []):
                issues.append(f"No explicit catalog certification for {canonical}.")
        elif canonical in {"vegan", "vegetarian"}:
            animal_codes = {"AF", "ABD", "ADQ", "AC", "UM", "BF", "CM", "PO"}
            if canonical == "vegan":
                animal_codes |= {"AM", "AE"}
            animal_declared = any(v.get("id") in animal_codes and v.get("unit") == "CONTAINS" for v in declarations)
            if pork_found or animal_declared or not claims.intersection(DIETS[canonical]):
                issues.append(f"No consistent explicit catalog evidence for {label}.")
        elif canonical in allergen_codes:
            supported_claims = DIETS.get(canonical, {"FREE_FROM_" + canonical.removesuffix("_free").upper()})
            explicit_absence = any(v.get("id") == root_code[canonical] and v.get("unit") == "FREE_FROM" for v in declarations)
            if not claims.intersection(supported_claims) and not explicit_absence:
                issues.append(f"No explicit catalog evidence for {label}; unknown is not verified compliant.")
        elif canonical in DIETS:
            if not claims.intersection(DIETS[canonical]):
                issues.append(f"No explicit catalog evidence for {label}.")
        else:
            issues.append(f"Unsupported dietary requirement: {diet}; specialist review required.")
    for excluded in excluded_ingredients or []:
        if re.search(r"\b" + re.escape(str(excluded)) + r"\b", text, re.I):
            issues.append(f"Identified excluded ingredient: {excluded}.")
        else:
            issues.append(f"Catalog cannot verify absence of custom exclusion: {excluded}.")
    if origin and str(origin).lower() not in {"any", "none"}:
        target = str(origin).strip().upper()
        codes = set(product.get("origin_codes", []))
        acceptable = EU if target in {"EU", "EUROPEAN UNION"} else {"FI", "246"} if target in {"FI", "FINLAND", "FINNISH", "246"} else {target, EU_CODES.get(target, target)}
        if not codes or not codes.issubset(acceptable):
            issues.append(f"Origin is unknown or outside the required region ({origin}).")
    if product.get("deleted"):
        issues.append("Product is deleted from the catalog.")
    if required_brand and not brand_matches(product.get("brand"), required_brand):
        issues.append(f"Declared brand is unknown or does not match required brand ({required_brand}).")
    if require_organic and product.get("organic") is not True:
        issues.append("No explicit supported organic packaging-label evidence.")
    return issues


def order_step(product):
    """Use declared weight increments for proven kg sales; keep packs sealed."""
    lot = positive(product.get("allowed_lot_size"))
    if not lot or product.get("variable_unit"):
        return None
    if (product.get("sales_unit") == "KG" and product.get("base_unit") == "KG"
            and positive(product.get("base_units_per_sales_unit")) == 1
            and positive(product.get("kg_per_sales_unit")) == 1):
        return lot
    # Smallest integer multiple of a rational lot is its numerator: a 0.4 lot
    # requires two whole packs, while a 1.5 lot requires three whole packs.
    return D(Fraction(lot).numerator)


def units_for(product, quantity, unit):
    """Round a proven dimension to the supplier increment without float drift."""
    amount = positive(quantity)
    step = order_step(product)
    if not amount or step is None:
        return None
    unit = str(unit).strip().lower()
    factors = {
        "kg": ("kg_per_sales_unit", D(1)), "kilograms": ("kg_per_sales_unit", D(1)),
        "g": ("kg_per_sales_unit", D(".001")), "grams": ("kg_per_sales_unit", D(".001")),
        "l": ("liters_per_sales_unit", D(1)), "litres": ("liters_per_sales_unit", D(1)),
        "liters": ("liters_per_sales_unit", D(1)),
        "ml": ("liters_per_sales_unit", D(".001")),
        "pieces": ("pieces_per_sales_unit", D(1)), "piece": ("pieces_per_sales_unit", D(1)),
        "pcs": ("pieces_per_sales_unit", D(1)),
    }
    if unit in {"package", "packages", "pack", "packs", "sales_unit", "sales_units"}:
        needed = Fraction(amount)
    elif unit in factors:
        field, multiplier = factors[unit]
        capacity = positive(product.get(field))
        if not capacity:
            return None
        needed = Fraction(amount * multiplier) / Fraction(capacity)
    else:
        return None
    steps = needed / Fraction(step)
    return D(-(-steps.numerator // steps.denominator)) * step


def _tokens(text):
    text = unicodedata.normalize("NFKD", str(text).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\b(vanilla|strawberry|banana|sour|condensed)milk\b", r"\1 milk", text)
    # Common compound product nouns must retain their actual purpose. Without
    # splitting, a butterbean is an ordinary substring match for dairy butter.
    text = re.sub(r"\b(butter)(beans?|buns?)\b|\b(flour)(scoops?)\b", lambda m: " ".join(part for part in m.groups() if part), text)
    aliases = {"mince": "minced", "ground": "minced", "tomatoes": "tomato", "tomatos": "tomato", "onions": "onion", "lentils": "lentil", "litres": "l", "liters": "l", "beans": "bean", "buns": "bun", "scoops": "scoop"}
    return [aliases.get(w, w) for w in re.findall(r"[\w]+", text)]


def _index_for(rows):
    global _INDEX_CATALOG, _SEARCH_INDEX
    # Keep only the identity value, not a strong reference to the ~600MiB source
    # object. Reloading the catalog must be able to release its old records.
    if _INDEX_CATALOG != id(rows):
        _INDEX_CATALOG = id(rows)
        _SEARCH_INDEX = {}
    return _SEARCH_INDEX


def _lexical_record(rows, pid, raw):
    """Cache only immutable source text/tokens, never facts or buyer criteria.

    Replacing/reloading the catalog invalidates the whole index. A lightweight
    source signature also detects in-place name/brand/category edits. Prices,
    stock, claims, package dimensions and preferences are always read afresh.
    """
    index = _index_for(rows)
    source = raw.get("synkkaData", {})
    names = source.get("names", [])
    brand_category = str(source.get("brand", "")) + " " + str(raw.get("category", ""))
    signature = (tuple((name.get("language"), name.get("value", "")) for name in names), brand_category)
    cached = index.get(pid)
    if cached is not None and cached[0] == signature:
        return cached[1]
    names_text = " ".join(name.get("value", "") for name in names)
    primary_name = localized(names) or names_text
    primary_terms = _tokens(primary_name)
    # Intern source vocabulary only. Customer query text is never interned or
    # stored in this shared index.
    fields = (
        frozenset(intern(term) for term in _tokens(names_text)),
        frozenset(intern(term) for term in _tokens(brand_category)),
        primary_name,
        frozenset(intern(term) for term in primary_terms),
        len(primary_terms),
        primary_name.casefold(),
    )
    index[pid] = (signature, fields)
    return fields


def ranked_matches(query, *, purpose=False):
    """All lexical matches, independent of quotation and customer eligibility.

    Ranking never changes membership. Unicode/case/punctuation-normalized word
    fragments match every supplied language, brand and category code. A purpose
    warning can prevent automatic recipe substitution, but cannot hide a SKU.
    """
    rows = catalog.load_catalog()
    _index_for(rows)
    query = str(query or '').strip()
    if not query:
        return [(0, str(pid), False) for pid, raw in rows.items() if not raw.get('deleted')]
    if query in rows:
        return [] if rows[query].get('deleted') else [(100000, query, False)]
    terms = set(_tokens(query))
    folded_query = ' '.join(_tokens(query))
    if query and not terms:
        return []
    prepared = {'bread', 'flourmix', 'cake', 'croissant', 'chips', 'sauce', 'patty', 'patties', 'soup', 'pizza', 'dressing', 'chocolate', 'powder', 'flavoured', 'flavored', 'drinkmix', 'biscuit', 'cookies', 'ice', 'cream', 'spreader', 'knife', 'bowl', 'plate', 'burger', 'salad', 'pastry', 'spice', 'mix', 'meatball', 'meatballs', 'bolognese', 'licorice', 'liquorice', 'date', 'dates', 'precooked', 'cooked', 'browned', 'roasted', 'candy', 'caramel', 'bouillon', 'seasoning', 'shaker', 'mill', 'dishwash', 'cleaning', 'casserole', 'bake', 'pancake', 'puree', 'mash', 'juice', 'topping', 'fried', 'prefried', 'pickled', 'sausage', 'coldcut', 'ketchup', 'strips', 'frankfurter', 'granulated', 'nylon', 'jug'}
    prepared.update({'bean', 'bun', 'scoop'})
    proteins = {'beef', 'pork', 'chicken', 'turkey', 'lamb', 'salmon', 'tuna', 'herring'}
    ranked = []
    for pid, raw in rows.items():
        if raw.get('deleted'):
            continue
        name_terms, attributes, primary_name, primary_terms, primary_length, primary_folded = _lexical_record(rows, pid, raw)
        vocabulary = name_terms | attributes | {str(pid)}
        if terms and not all(any(term in token for token in vocabulary) for term in terms):
            continue
        exact_id = query == str(pid)
        names = raw.get('synkkaData', {}).get('names', [])
        exact_name = bool(query) and any(' '.join(_tokens(name.get('value', ''))) == folded_query for name in names)
        category = bool(query) and query.casefold() == str(raw.get('category', '')).casefold()
        exact_tokens = len(terms & name_terms)
        penalties = len((primary_terms & prepared) - terms)
        if terms & proteins:
            penalties += len((primary_terms & proteins) - terms)
        mismatch = False
        if purpose and not (exact_id or exact_name or category):
            mismatch = penalties > 0
            if 'milk' in terms:
                variants = {'vanilla', 'strawberry', 'banana', 'sour', 'condensed', 'evaporated', 'fermented', 'cultured'}
                mismatch |= bool((primary_terms & variants) - terms)
            if 'free' not in terms:
                mismatch |= any(re.search(r'\b' + re.escape(term) + r'[ -]+free\b|\bfree[ -]+from[ -]+' + re.escape(term) + r'\b', primary_name, re.I) for term in terms)
        score = (100000 if exact_id else 10000 if exact_name else 5000 if category else 0) + exact_tokens * 100 + (40 if query.casefold() in primary_folded else 0) - penalties * (60 if purpose else 5) - primary_length
        ranked.append((score, str(pid), bool(mismatch)))
    ranked.sort(key=lambda value: (-value[0], value[1]))
    return ranked


def search_page(query='', limit=20, offset=0, *, category=None, brand=None,
                dietary=None, origin=None, require_organic=False,
                preferred_brand=None, preferred_origin=None, preferred_organic=False,
                excluded_ingredients=None, sort="relevance"):
    """Complete paginated discovery. Only explicit hard filters remove records."""
    matches = ranked_matches(query)
    rows = catalog.load_catalog()
    products = []
    category_counts, brand_counts = {}, {}
    needs_facts = bool(dietary or origin or require_organic or excluded_ingredients or preferred_origin or preferred_organic)
    for score, pid, _ in matches:
        raw = rows[pid]
        cat = str(raw.get('category') or '')
        declared_brand = str(raw.get('synkkaData', {}).get('brand') or '').strip()
        # Cheap source filters precede package/ingredient normalization. No
        # safety, quantity, stock or price fact is cached by this lexical index.
        category_ok = not category or cat.casefold() == str(category).casefold()
        brand_ok = not brand or brand_matches(declared_brand, brand)
        p = normalize(pid) if needs_facts else None
        if p is not None and suitability(p, dietary, origin, require_organic=require_organic, excluded_ingredients=excluded_ingredients):
            continue
        # Disjunctive facets respect all other hard filters, while keeping the
        # current facet's real alternatives available for a direct change.
        if cat and brand_ok:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        if declared_brand and category_ok:
            brand_counts[declared_brand] = brand_counts.get(declared_brand, 0) + 1
        if not category_ok or not brand_ok:
            continue
        preference = int(bool(preferred_brand) and brand_matches(declared_brand, preferred_brand))
        if p is not None:
            preference += int(bool(preferred_origin) and not suitability(p, [], preferred_origin)) + int(preferred_organic and p.get('organic') is True)
        products.append((0 if score >= 10000 else 1, -preference, -score, pid, p))
    if sort in {"name_asc", "name_desc"}:
        # Alphabetical sorting covers the entire filtered catalog before page
        # selection, independent of which products have supplier quotations.
        products.sort(key=lambda row: (_lexical_record(rows, row[3], rows[row[3]])[5], row[3]), reverse=sort == "name_desc")
    else:
        products.sort(key=lambda row: row[:4])
    total = len(products)
    return {'products': [row[4] if row[4] is not None else normalize(row[3]) for row in products[offset:offset + limit]],
            'total': total, 'offset': offset, 'limit': limit,
            'has_more': offset + limit < total,
            'facets': {'categories': [{'value': key, 'label': key, 'count': value} for key, value in sorted(category_counts.items())],
                       'brands': [{'value': key, 'label': key, 'count': value} for key, value in sorted(brand_counts.items(), key=lambda pair: pair[0].casefold())]}}


def search(query, limit=8, dietary=None, origin=None, required_brand=None, require_organic=False, preferred_brand=None, preferred_origin=None, preferred_organic=False):
    """Bounded recommendation shortlist from the same complete lexical index.

    Purpose warnings require explicit choice rather than deleting search hits.
    Hard compliance is ranked, never asserted from name text.
    """
    ranked = ranked_matches(query, purpose=True)
    normalized = []
    for score, pid, mismatch in ranked:
        p = normalize(pid)
        p['purpose_review_required'] = mismatch
        preference = int(bool(preferred_brand) and brand_matches(p.get('brand'), preferred_brand)) + int(bool(preferred_origin) and not suitability(p, [], preferred_origin)) + int(preferred_organic and p.get('organic') is True)
        normalized.append((int(mismatch), len(suitability(p, dietary, origin, required_brand, require_organic)), -preference, -score, pid, p))
    normalized.sort(key=lambda value: value[:5])
    return [value[5] for value in normalized[:max(1, min(int(limit), 50))]]


def discover(query, limit=16, dietary=None, origin=None, retrieval_queries=None, selected_product_id=None, required_brand=None, require_organic=False, preferred_brand=None, preferred_origin=None, preferred_organic=False):
    """Ground semantic query proposals and supplier links in actual catalog IDs.

    An expanded query discovers candidates only. Its provenance stays explicit;
    the order engine requires customer choice before accepting substitutions.
    """
    limit = max(1, min(int(limit), 16))
    criteria = {"required_brand": required_brand, "require_organic": require_organic, "preferred_brand": preferred_brand, "preferred_origin": preferred_origin, "preferred_organic": preferred_organic}
    criteria = {key: value for key, value in criteria.items() if value}
    primary = []
    for product in search(query, limit, dietary, origin, **criteria):
        p = dict(product)
        p["match_method"] = "exact_sku" if str(query).strip() == p["id"] else "category" if str(query).strip() == str(p.get("category")) else "lexical"
        p["match_reason"] = "Purpose differs from the generic request; review before choosing." if p.get("purpose_review_required") else "Exact supplied product ID." if p["match_method"] == "exact_sku" else "Matching catalog category code." if p["match_method"] == "category" else "Catalog name/brand matches the requested search."
        primary.append(p)
    alternatives = []
    for expansion in list(dict.fromkeys(str(q).strip() for q in retrieval_queries or [] if str(q).strip()))[:3]:
        if expansion.casefold() == str(query).strip().casefold():
            continue
        for product in search(expansion, 8, dietary, origin, **criteria):
            alternatives.append(dict(product, match_method="semantic_expansion", match_reason=f"Discovered through the proposed related search: {expansion}. Customer suitability review required."))
    anchors = list(primary)
    if selected_product_id and not any(p["id"] == selected_product_id for p in anchors):
        try:
            anchors.append(normalize(selected_product_id))
        except ValueError:
            pass
    for anchor in anchors:
        for pid in anchor.get("substitutes", []):
            try:
                product = normalize(pid)
            except ValueError:
                continue
            alternatives.append(dict(product, match_method="supplier_substitution", match_reason=f"Catalog supplier substitution link from SKU {anchor['id']}; customer review and all hard checks are still required."))
    # Reserve discovery capacity without hiding an exact original SKU. Avoid
    # letting a broad lexical list consume every available alternative slot.
    ordered = primary[:8] + alternatives + primary[8:] if alternatives else primary
    result = []
    seen = set()
    primary_by_id = {p["id"]: p for p in primary}
    for product in ordered:
        if product["id"] in seen:
            continue
        # A direct match remains direct even when also returned by an expansion.
        product = primary_by_id.get(product["id"], product)
        seen.add(product["id"])
        result.append(product)
        if len(result) >= limit:
            break
    return result
