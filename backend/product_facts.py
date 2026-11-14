"""Evidence-backed generic product facts and fixed, whole-sales-pack conversion.

Catalog text is descriptive data. Missing claims, package dimensions or origin
remain unknown, and never become proof through keyword matching.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from fractions import Fraction

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


def suitability(product, dietary=None, origin=None):
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
    aliases = {"mince": "minced", "ground": "minced", "tomatoes": "tomato", "tomatos": "tomato", "onions": "onion", "lentils": "lentil", "litres": "l", "liters": "l"}
    return [aliases.get(w, w) for w in re.findall(r"[\w]+", text) if len(w) > 1 or w.isdigit()]


def search(query, limit=8, dietary=None, origin=None):
    """Rank multilingual catalog names, brand and category; verify facts separately."""
    rows = catalog.load_catalog()
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
    for pid, raw in rows.items():
        if raw.get("deleted"):
            continue
        s = raw.get("synkkaData", {})
        names = " ".join(x.get("value", "") for x in s.get("names", []))
        name_terms = set(_tokens(names))
        attributes = set(_tokens(str(s.get("brand", "")) + " " + str(raw.get("category", ""))))
        if not terms.issubset(name_terms | attributes):
            continue
        primary_name = localized(s.get("names")) or names
        primary_terms = _tokens(primary_name)
        if any(re.search(r"\b" + re.escape(term) + r"[ -]+free\b|\bfree[ -]+from[ -]+" + re.escape(term) + r"\b", primary_name, re.I) for term in terms):
            continue
        # A matched ingredient inside a prepared food (salt in chips, butter in
        # croissants, lentils in sauce) is weaker evidence of the requested
        # product's purpose. These are ranking hints, never suitability proof.
        prepared = {"bread", "flour", "flourmix", "cake", "croissant", "chips", "sauce", "patty", "patties", "soup", "pizza", "dressing", "chocolate", "powder", "flavoured", "flavored", "drinkmix", "biscuit", "cookies", "ice", "cream", "cocoa", "spreader", "knife", "bowl", "plate", "burger", "salad", "pastry", "spice", "mix", "meatball", "meatballs", "bolognese", "licorice", "liquorice", "date", "dates", "precooked", "cooked", "brown", "browned", "roasted", "herring", "fish", "candy", "caramel", "macarons", "bouillon", "seasoning", "shaker", "mill", "menage", "dishwash", "diswash", "cleaning", "casserole", "bake", "pancake", "puree", "mash", "juice", "topping", "jellies", "fried", "prefried", "pickled", "ring", "rings", "oat", "sausage", "coldcut", "ketchup", "strips", "chicken", "frankfurter", "ball", "balls", "multipack", "granulated", "nylon", "svr", "jug", "liver", "hartshorn"}
        penalties = len((set(primary_terms) & prepared) - terms)
        if not terms.issubset(set(primary_terms) | attributes):
            penalties += 1
        proteins = {"beef", "pork", "chicken", "turkey", "lamb", "salmon", "tuna", "herring"}
        if terms & proteins:
            penalties += len((set(primary_terms) & proteins) - terms)
        # Dried/ground aromatic vegetables materially differ from raw recipe
        # ingredients. Explicitly requested preparation terms remain exempt.
        if "onion" in terms and "minced" not in terms and "minced" in primary_terms:
            penalties += 1
        score = (len(terms & name_terms) * 100
                 + (15 if query.casefold() in primary_name.casefold() else 0)
                 - penalties * 60 - len(primary_terms))
        ranked.append((score, str(pid)))
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
    normalized.sort(key=lambda p: (len(suitability(p, dietary, origin)),
                                   -scores[p["id"]], p["id"]))
    return normalized[:max(1, min(int(limit), 20))]
