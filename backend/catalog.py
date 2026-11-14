"""Local static search; source text is data, never an instruction."""

import csv
import json
import re
from decimal import Decimal
from functools import lru_cache
from .config import ROOT

DEFAULT_IDS = ["464306", "464398", "465039"]


@lru_cache(maxsize=1)
def load_catalog():
    path = ROOT / "data/raw/valio_aimo_junction26_product_data.json"
    if not path.exists():
        return {}
    return {str(p["id"]): p for p in json.loads(path.read_text())}


@lru_cache(maxsize=1)
def supplemental():
    out = {}
    for filename, col, key in [
        (
            "valio_aimo_junction26_delivery_reliability.csv",
            "deliveryReliability",
            "reliability",
        ),
        (
            "valio_aimo_junction26_carbon_footprint.csv",
            "AVG kg CO2-eq/kg",
            "carbon_group_estimate",
        ),
    ]:
        p = ROOT / "data/raw" / filename
        if p.exists():
            with p.open() as f:
                for row in csv.DictReader(f):
                    try:
                        out.setdefault(str(row["productId"]), {})[key] = float(row[col])
                    except (ValueError, KeyError):
                        pass
    return out


def normalize(p):
    s = p.get("synkkaData", {})
    names = s.get("names", [])
    name = next((n["value"] for n in names if n.get("language") == "en"), str(p["id"]))
    claims = [
        v.get("id")
        for c in s.get("classifications", [])
        if c.get("name") == "nutritionalClaim"
        for v in c.get("values", [])
    ]
    free = True if "FREE_FROM_LACTOSE" in claims else None
    volume = None
    source = None
    for u in s.get("unitConversions", []):
        v = u.get("volume", {})
        if (
            u.get("synkkaPackagingType") == "BASE_UNIT_OR_EACH"
            and v.get("unit") == "LTR"
        ):
            volume = Decimal(str(v["value"]))
            source = "synkkaData.unitConversions BASE_UNIT_OR_EACH.volume LTR"
    # A declared consumer-unit volume in the supplier name is dimensional evidence,
    # unlike gross weight or an assumed density. Only explicit litre declarations.
    if volume is None:
        m = re.search(r"\b(\d+(?:[.,]\d+)?)\s+l\b", name, re.I)
        if m:
            volume = Decimal(m.group(1).replace(",", "."))
            source = "supplier English name: declared consumer-unit litres"
    sales_size = next(
        (
            Decimal(str(u["sizeInBaseUnits"]))
            for u in p.get("units", [])
            if u.get("unitId") == p.get("salesUnit")
        ),
        None,
    )
    liters = (
        volume * sales_size
        if volume is not None and sales_size is not None and p.get("baseUnit") == "ST"
        else None
    )
    out = {
        "id": str(p["id"]),
        "name": name,
        "sales_unit": p.get("salesUnit"),
        "base_unit": p.get("baseUnit"),
        "base_units_per_sales_unit": str(sales_size)
        if sales_size is not None
        else None,
        "liters_per_sales_unit": str(liters) if liters is not None else None,
        "volume_evidence": source,
        "diet_evidence": "FREE_FROM_LACTOSE classification"
        if free
        else "No explicit lactose-free classification",
        "lactose_free": free,
        "contains_milk": True
        if any(
            v.get("id") == "AM" and v.get("unit") == "CONTAINS"
            for c in s.get("classifications", [])
            if c.get("name") == "allergen"
            for v in c.get("values", [])
        )
        else None,
        "allowed_lot_size": str(p.get("allowedLotSize", 1)),
        "deleted": p.get("deleted", False),
        "deposits": p.get("deposits", []),
        "variable_unit": s.get("variableUnit", False),
        "substitutes": [
            str(v.get("substituteProduct")) for v in p.get("substitutions", [])
        ],
        "evidence_source": "restricted synthetic challenge catalog; no real product safety certification",
    }
    out.update(supplemental().get(str(p["id"]), {}))
    return out


def product(pid):
    p = load_catalog().get(str(pid))
    if not p:
        raise ValueError("Product not found in local catalog")
    return normalize(p)


def search(query, limit=10):
    # One catalog index for the original outside-agent route and Product Workspace.
    from .product_facts import search_page
    return [normalize(load_catalog()[p["id"]]) | p for p in search_page(query, limit=limit)["products"]]
