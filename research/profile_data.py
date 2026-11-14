"""Profile the supplied challenge files without modifying the originals.

Run from any directory with Python 3.10+:
    python research/profile_data.py
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def csv_profile(filename: str, value_column: str, catalog_ids: set[str]) -> dict:
    with (RAW / filename).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    identifiers = [row["productId"] for row in rows]
    distinct = set(identifiers)
    values = [float(row[value_column]) for row in rows]
    matches = distinct & catalog_ids
    return {
        "file": filename,
        "value_column": value_column,
        "rows": len(rows),
        "unique_product_ids": len(distinct),
        "duplicate_product_ids": len(identifiers) - len(distinct),
        "matched_catalog_products": len(matches),
        "orphan_product_ids": len(distinct - catalog_ids),
        "missing_catalog_products": len(catalog_ids - distinct),
        "catalog_coverage_percent": round(100 * len(matches) / len(catalog_ids), 2),
        "minimum": min(values),
        "maximum": max(values),
        "median": statistics.median(values),
    }


def main() -> None:
    products = json.loads(
        (RAW / "valio_aimo_junction26_product_data.json").read_text(encoding="utf-8")
    )
    identifiers = [product["id"] for product in products]
    catalog_ids = set(identifiers)
    synkka = [product.get("synkkaData") or {} for product in products]
    fields = [
        "names", "classifications", "keyIngredients", "unitConversions",
        "nutritionalContent", "medias",
    ]
    classifications = [
        "allergen", "nonAllergen", "nutritionalClaim", "packagingMarkedLabel",
    ]
    substitutions = [
        rule for product in products for rule in product.get("substitutions", [])
    ]
    profile = {
        "review_date": "2026-11-14",
        "scope": "Static challenge data only; API runtime behavior has not been tested.",
        "catalog": {
            "rows": len(products),
            "unique_product_ids": len(catalog_ids),
            "duplicate_product_ids": len(identifiers) - len(catalog_ids),
            "unique_vendor_names": len({p["vendorName"] for p in products}),
            "unique_category_codes": len({p["category"] for p in products}),
            "sales_unit_counts": dict(Counter(p["salesUnit"] for p in products)),
            "base_unit_differs_from_sales_unit": sum(
                p["baseUnit"] != p["salesUnit"] for p in products
            ),
            "products_with_deposits": sum(bool(p["deposits"]) for p in products),
            "products_with_substitution_rules": sum(
                bool(p.get("substitutions")) for p in products
            ),
            "substitution_edges": len(substitutions),
            "substitution_targets_outside_catalog": len({
                rule["substituteProduct"] for rule in substitutions
                if rule["substituteProduct"] not in catalog_ids
            }),
            "nonempty_synkka_fields": {
                field: sum(bool(s.get(field)) for s in synkka) for field in fields
            },
            "products_with_name_in_language": {
                language: sum(
                    any(n.get("language") == language and n.get("value")
                        for n in s.get("names", []))
                    for s in synkka
                ) for language in ["en", "fi", "sv"]
            },
            "products_with_nonempty_classification": {
                name: sum(
                    any(c.get("name") == name and c.get("values")
                        for c in s.get("classifications", []))
                    for s in synkka
                ) for name in classifications
            },
        },
        "delivery_reliability": csv_profile(
            "valio_aimo_junction26_delivery_reliability.csv",
            "deliveryReliability", catalog_ids,
        ),
        "carbon_footprint": csv_profile(
            "valio_aimo_junction26_carbon_footprint.csv",
            "AVG kg CO2-eq/kg", catalog_ids,
        ),
        "interpretation": [
            "Join catalog id to CSV productId and API productId as strings.",
            "Missing classification entries are not proof that an allergen is absent.",
            "Reliability measures historical delivered quantity versus ordered quantity, not an on-time delivery probability.",
            "Carbon numbers are product-group averages per kilogram, not individual-product measurements.",
            "Packaging metadata and unit-code translations are incomplete. Do not guess unsupported conversions.",
            "Synthetic data is restricted to the challenge; it does not establish real product safety or actual commercial offers.",
        ],
    }
    output = ROOT / "research" / "DATA_PROFILE.json"
    output.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(profile, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
