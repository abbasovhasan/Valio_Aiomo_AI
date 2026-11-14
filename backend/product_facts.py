"""Evidence-backed generic product facts and fixed, whole-sales-pack conversion.

Catalog text is descriptive data. Missing claims, package dimensions or origin
remain unknown, and never become proof through keyword matching.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_CEILING
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
            if amount and vol.get("unit") in {"LTR", "MLT"}:
                volumes.add(amount / (1000 if vol["unit"] == "MLT" else 1))
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
    if mass and len(multipacks) == 1 and mass != multipacks[0]:
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
        "allergens": classification(s, "allergen"),
        "storage": localized(s.get("storageInstructions")),
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


def suitability(product, dietary=None, origin=None, required_brand=None, require_organic=False):
    issues = []
    claims = set(product.get("claims", []))
    for diet in dietary or []:
        canonical = str(diet).lower().replace("-", "_").replace(" ", "_")
        supported = DIETS.get(canonical)
        if not supported:
            issues.append(f"Unsupported dietary requirement: {diet}; specialist review required.")
        elif not claims.intersection(supported):
            issues.append(f"No explicit catalog evidence for {canonical.replace('_', ' ')}.")
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


def units_for(product, quantity, unit):
    """Round a dimensionally proven request to sealed whole sales units.

    Integer numerator is the smallest whole-pack count compatible with a rational
    allowedLotSize, e.g. 0.4 => 2 whole packs, 1.5 => 3 whole packs.
    """
    amount = positive(quantity)
    lot = positive(product.get("allowed_lot_size"))
    if not amount or not lot or product.get("variable_unit"):
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
        needed = amount
    elif unit in factors:
        field, multiplier = factors[unit]
        capacity = positive(product.get(field))
        if not capacity:
            return None
        needed = amount * multiplier / capacity
    else:
        return None
    step = D(Fraction(lot).numerator)
    return (needed / step).to_integral_value(rounding=ROUND_CEILING) * step


def _tokens(text):
    text = unicodedata.normalize("NFKD", str(text).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\b(vanilla|strawberry|banana|sour|condensed)milk\b", r"\1 milk", text)
    aliases = {"mince": "minced", "ground": "minced", "tomatoes": "tomato", "tomatos": "tomato", "onions": "onion", "lentils": "lentil", "litres": "l", "liters": "l"}
    return [aliases.get(w, w) for w in re.findall(r"[\w]+", text) if len(w) > 1 or w.isdigit()]


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


def search(query, limit=8, dietary=None, origin=None, required_brand=None, require_organic=False, preferred_brand=None, preferred_origin=None, preferred_organic=False):
    """Rank multilingual catalog names, brand and category; verify facts separately."""
    rows = catalog.load_catalog()
    _index_for(rows)
    query = str(query).strip()
    if query in rows:
        return [normalize(query)]
    terms = set(_tokens(query)) - {"the", "some", "of", "product", "products"}
    # Dietary words describe a verified attribute, rather than requiring the name
    # to repeat that attribute. Keep them for searches without structured diet.
    if dietary:
        terms -= {"lactose", "gluten", "free", "vegetarian", "vegan"}
    if not terms:
        return []
    ranked = []
    query_folded = query.casefold()
    excluded_name_patterns = [re.compile(r"\b" + re.escape(term) + r"[ -]+free\b|\bfree[ -]+from[ -]+" + re.escape(term) + r"\b", re.I) for term in terms]
    for pid, raw in rows.items():
        if raw.get("deleted"):
            continue
        name_terms, attributes, primary_name, primary_terms, primary_length, primary_folded = _lexical_record(rows, pid, raw)
        if not terms.issubset(name_terms | attributes):
            continue
        if "milk" in terms:
            # These named variants materially change generic milk's purpose.
            # Exclude known unrequested variants even if no plain product exists;
            # a low price, brand match or complete diet claim cannot repair it.
            variants = {"vanilla", "strawberry", "banana", "sour", "condensed", "evaporated", "fermented", "cultured"}
            if (primary_terms & variants) - terms:
                continue
        if any(pattern.search(primary_name) for pattern in excluded_name_patterns):
            continue
        # A matched ingredient inside a prepared food (salt in chips, butter in
        # croissants, lentils in sauce) is weaker evidence of the requested
        # product's purpose. These are ranking hints, never suitability proof.
        prepared = {"bread", "flour", "flourmix", "cake", "croissant", "chips", "sauce", "patty", "patties", "soup", "pizza", "dressing", "chocolate", "powder", "flavoured", "flavored", "drinkmix", "biscuit", "cookies", "ice", "cream", "cocoa", "spreader", "knife", "bowl", "plate", "burger", "salad", "pastry", "spice", "mix", "meatball", "meatballs", "bolognese", "licorice", "liquorice", "date", "dates", "precooked", "cooked", "brown", "browned", "roasted", "herring", "fish", "candy", "caramel", "macarons", "bouillon", "seasoning", "shaker", "mill", "menage", "dishwash", "diswash", "cleaning", "casserole", "bake", "pancake", "puree", "mash", "juice", "topping", "jellies", "fried", "prefried", "pickled", "ring", "rings", "oat", "sausage", "coldcut", "ketchup", "strips", "chicken", "frankfurter", "ball", "balls", "multipack", "granulated", "nylon", "svr", "jug", "liver", "hartshorn"}
        penalties = len((primary_terms & prepared) - terms)
        if not terms.issubset(primary_terms | attributes):
            penalties += 1
        proteins = {"beef", "pork", "chicken", "turkey", "lamb", "salmon", "tuna", "herring"}
        if terms & proteins:
            penalties += len((primary_terms & proteins) - terms)
        # Dried/ground aromatic vegetables materially differ from raw recipe
        # ingredients. Explicitly requested preparation terms remain exempt.
        if "onion" in terms and "minced" not in terms and "minced" in primary_terms:
            penalties += 1
        score = (len(terms & name_terms) * 100
                 + (15 if query_folded in primary_folded else 0)
                 - penalties * 60 - primary_length)
        ranked.append((score, str(pid)))
    if _INDEX_CATALOG == id(rows) and len(_SEARCH_INDEX) > len(rows):
        index = _SEARCH_INDEX
        for pid in tuple(index):
            if pid not in rows:
                index.pop(pid, None)
    # Never truncate before suitability ranking; otherwise the first catalog
    # records can conceal the only explicitly compliant gluten-free variant.
    ranked.sort(key=lambda x: (-x[0], x[1]))
    # Strong name-purpose mismatches must not outrank relevant products merely
    # because their dietary claims are more complete. Preserve the best lexical
    # band before ranking verified suitability within it.
    if ranked:
        best_score = ranked[0][0]
        ranked = [(score, pid) for score, pid in ranked if score >= best_score - 45]
    scores = {pid: score for score, pid in ranked}
    normalized = [normalize(pid) for _, pid in ranked]
    def preference_count(p):
        return int(bool(preferred_brand) and brand_matches(p.get("brand"), preferred_brand)) + int(bool(preferred_origin) and not suitability(p, [], preferred_origin)) + int(preferred_organic and p.get("organic") is True)
    normalized.sort(key=lambda p: (len(suitability(p, dietary, origin, required_brand, require_organic)),
                                   -preference_count(p), -scores[p["id"]], p["id"]))
    return normalized[:max(1, min(int(limit), 20))]


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
        p["match_reason"] = "Exact supplied product ID." if p["match_method"] == "exact_sku" else "Matching catalog category code." if p["match_method"] == "category" else "Catalog name/brand matches the requested search."
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
