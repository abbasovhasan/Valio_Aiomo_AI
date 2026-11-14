"""Independent, dataset-driven catalog API checks; no orders or external calls.

The raw files remain private. Only aggregate counts and selected check identifiers
are written to an ignored report. Run against an isolated local app by default:
  .venv/bin/python scripts/catalog_qa.py
  .venv/bin/python scripts/catalog_qa.py --url http://127.0.0.1:8012
The HTTP option uses the existing buyer credential without printing it. All
quotations explicitly use authored fixture mode and no confirmation endpoint runs.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
import tempfile
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_FILES = (
    "valio_aimo_junction26_product_data.json",
    "valio_aimo_junction26_product_data_schema.json",
    "valio_aimo_junction26_delivery_reliability.csv",
    "valio_aimo_junction26_carbon_footprint.csv",
)


def fold(text):
    value = unicodedata.normalize("NFKD", str(text).casefold())
    return "".join(c for c in value if not unicodedata.combining(c))


def source_names(raw):
    return [n.get("value", "") for n in raw.get("synkkaData", {}).get("names", [])
            if isinstance(n, dict) and n.get("value")]


def active_records(rows):
    return {str(pid): row for pid, row in rows.items() if not row.get("deleted")}


def source_claims(raw):
    return {v.get("id") for c in raw.get("synkkaData", {}).get("classifications", [])
            if c.get("name") == "nutritionalClaim" for v in c.get("values", [])
            if isinstance(v, dict) and v.get("id")}


def category_groups(rows):
    out = collections.defaultdict(set)
    for pid, row in active_records(rows).items():
        if row.get("category") is not None:
            out[str(row["category"])].add(pid)
    return out


def inventory(raw_dir=ROOT / "data/raw"):
    result = {}
    for filename in DATA_FILES:
        path = raw_dir / filename
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
        entry = {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}
        if path.suffix == ".csv":
            with path.open() as f:
                reader = csv.DictReader(f)
                entry["columns"] = reader.fieldnames
                entry["records"] = sum(1 for _ in reader)
        result[filename] = entry
    return result


def representative_queries(rows):
    """Choose examples from source names, not hand-picked successful SKUs."""
    active = active_records(rows)
    result = []
    for language in ("en", "fi", "sv"):
        choices = []
        for pid, raw in active.items():
            for name in raw.get("synkkaData", {}).get("names", []):
                text = name.get("value", "")
                if name.get("language") == language and 8 <= len(text) <= 70:
                    choices.append((str(raw.get("category", "")), pid, text))
        if choices:
            _, pid, text = sorted(choices)[len(choices) // 2]
            result.append({"kind": "localized_" + language, "q": text, "id": pid})
    counts = collections.Counter()
    for raw in active.values():
        # Count once per product, independently of multilingual repetitions.
        counts.update({word for name in source_names(raw)
                       for word in re.findall(r"[a-z]{5,}", fold(name))})
    common = sorted((count, word) for word, count in counts.items() if 30 <= count <= 700)
    if common:
        _, word = common[len(common) // 2]
        expected = {pid for pid, raw in active.items()
                    if any(word in fold(name) for name in source_names(raw))}
        result.append({"kind": "partial", "q": word[:4], "expected_subset": expected})
    hyphenated = [(pid, name) for pid, raw in active.items() for name in source_names(raw)
                  if 8 <= len(name) <= 70 and re.search(r"[A-Za-zÅÄÖåäö]-[A-Za-zÅÄÖåäö]", name)]
    if hyphenated:
        pid, name = sorted(hyphenated)[len(hyphenated) // 2]
        result.append({"kind": "hyphen", "q": name.replace("-", " "), "id": pid})
    return result


def fixed_pack_case(raw, unit):
    """Read a conservative source conversion without calling purchasing code."""
    source = raw.get("synkkaData", {})
    if source.get("variableUnit") or raw.get("deleted") or raw.get("deposits"):
        return None
    try:
        lot = Decimal(str(raw.get("allowedLotSize", 1)))
        if not lot.is_finite() or lot <= 0 or Fraction(lot).numerator > 3:
            return None
        sizes = {Decimal(str(item["sizeInBaseUnits"])) for item in raw.get("units", [])
                 if item.get("unitId") == raw.get("salesUnit")}
        if not sizes and raw.get("salesUnit") == raw.get("baseUnit"):
            sizes = {Decimal(1)}
        if len(sizes) != 1:
            return None
        size = next(iter(sizes))
        if not size.is_finite() or size <= 0:
            return None
        capacity = Decimal(1) if unit == "packages" else None
        if unit == "kg" and raw.get("baseUnit") == "KG":
            capacity = size
        elif unit == "pieces" and raw.get("baseUnit") == "ST":
            capacity = size
        elif unit in {"kg", "L"}:
            facts = set()
            field = "netWeight" if unit == "kg" else "volume"
            multipliers = {"KGM": Decimal(1), "GRM": Decimal(".001")} if unit == "kg" else {"LTR": Decimal(1), "MLT": Decimal(".001")}
            for conversion in source.get("unitConversions", []):
                if conversion.get("synkkaPackagingType") == "BASE_UNIT_OR_EACH":
                    value = conversion.get(field, {})
                    if value.get("unit") in multipliers:
                        facts.add(Decimal(str(value["value"])) * multipliers[value["unit"]])
            if len(facts) == 1:
                capacity = next(iter(facts)) * size
        if capacity is None or not capacity.is_finite() or not Decimal(".01") <= capacity <= 50:
            return None
        # A name-declared multipack can conflict with structured source evidence.
        # Do not make this conversion sample depend on resolving that ambiguity.
        if unit == "kg" and any(re.search(r"\d\s*[x×*]\s*\d|\d\s*(?:kg|g)\s*[x×*]", name, re.I) for name in source_names(raw)):
            return None
        return {"id": str(raw["id"]), "category": str(raw.get("category")),
                "unit": unit, "capacity": capacity, "lot": lot,
                "quantity": capacity * Decimal("1.25")}
    except (InvalidOperation, KeyError, TypeError, ValueError):
        return None


def representative_cart_cases(rows):
    out = []
    used_categories = set()
    active = sorted(active_records(rows).values(), key=lambda row: (str(row.get("category")), str(row["id"])))
    for index, unit in enumerate(("kg", "L", "pieces", "packages")):
        eligible = []
        for raw in active:
            if str(raw.get("category")) in used_categories:
                continue
            case = fixed_pack_case(raw, unit)
            if case and case["quantity"] == case["quantity"].quantize(Decimal(".001")):
                eligible.append(case)
        if eligible:
            # Spread samples through the catalog rather than choosing the first
            # four dairy records merely because source IDs/categories sort first.
            case = eligible[len(eligible) * (index + 1) // 5]
            out.append(case)
            used_categories.add(case["category"])
    return out


def category_representatives(rows):
    result = []
    for category, ids in sorted(category_groups(rows).items()):
        choices = [(len(name), pid, name) for pid in sorted(ids)
                   for name in source_names(rows[pid])
                   if 1 <= len(name) <= 100 and any(char.isalnum() for char in name)]
        if not choices:
            raise AssertionError("A source category needs a bounded searchable name")
        _, pid, name = min(choices)
        result.append({"category": category, "id": pid, "q": name, "count": len(ids)})
    return result


def expected_sales_units(quantity, capacity, lot):
    exact = Fraction(Decimal(str(quantity))) / Fraction(capacity)
    step = Fraction(lot).numerator
    return Decimal(-(-exact.numerator // (exact.denominator * step)) * step)


def all_pages(client, params, *, page_size=50):
    products = []
    offset = 0
    total = None
    while True:
        response = client.get("/api/v1/products", params={"mode": "fixture", "date": str(date.today() + timedelta(days=2)), "apply_preferences": "false", **params, "limit": page_size, "offset": offset})
        assert response.status_code == 200, f"Catalog HTTP {response.status_code}: {response.text[:250]}"
        payload = response.json()
        assert all(key in payload for key in ("products", "total", "offset", "limit", "has_more", "facets", "applied_filters")), "Missing paginated catalog contract"
        assert payload["offset"] == offset and payload["limit"] == page_size
        assert total is None or total == payload["total"], "Total changed between static pages"
        total = payload["total"]
        page = payload["products"]
        products.extend(page)
        assert len({p["id"] for p in products}) == len(products), "Duplicate products across pages"
        assert payload["has_more"] == (offset + len(page) < total), "Incorrect continuation"
        if not payload["has_more"]:
            assert len(products) == total, "Incomplete catalog pagination"
            return products, payload
        assert page, "Pagination did not advance"
        offset += len(page)
        assert offset <= 20000, "Unexpected catalog growth/pagination loop"


def run_matrix(client, rows, report):
    started = time.perf_counter()
    def check(name, fn):
        check_started = time.perf_counter()
        try:
            detail = fn()
            report["checks"].append({"name": name, "passed": True, "detail": detail})
        except Exception as exc:
            report["checks"].append({"name": name, "passed": False, "error": str(exc)[:350]})
        report["checks"][-1]["elapsed_ms"] = round((time.perf_counter() - check_started) * 1000, 2)

    groups = category_groups(rows)
    category = max(groups, key=lambda key: (len(groups[key]), key))
    def category_check():
        products, _ = all_pages(client, {"q": "", "category": category})
        assert {p["id"] for p in products} == groups[category], "Category missed or invented actual products"
        return {"category": category, "actual_matches": len(products)}
    check("Full dynamically chosen category across pages", category_check)
    def every_category():
        for example in category_representatives(rows):
            response = client.get("/api/v1/products", params={"q": "", "category": example["category"], "limit": 1, "mode": "fixture", "apply_preferences": "false"})
            assert response.status_code == 200, f"Category {example['category']} HTTP {response.status_code}"
            assert response.json()["total"] == example["count"], f"Category {example['category']} lost actual source records"
            named = client.get("/api/v1/products", params={"q": example["q"], "category": example["category"], "limit": 50, "mode": "fixture", "apply_preferences": "false"})
            assert named.status_code == 200, f"Name in category {example['category']} HTTP {named.status_code}"
            assert example["id"] in {product["id"] for product in named.json()["products"]}, f"Actual exact source name in category {example['category']} not findable"
        return {"categories": len(category_representatives(rows)), "checks_per_category": 2}
    check("Every actual category count and an exact source name through API", every_category)
    for case in representative_queries(rows):
        def query_check(case=case):
            products, _ = all_pages(client, {"q": case["q"]})
            ids = {p["id"] for p in products}
            assert ids.issubset(rows), "Search invented product IDs"
            if "id" in case:
                assert case["id"] in ids, "Actual source name not found"
            if "expected_subset" in case:
                assert case["expected_subset"].issubset(ids), "Partial name missed actual matches"
            return {"matches": len(ids)}
        check("Actual source " + case["kind"] + " search", query_check)
    def no_match():
        products, payload = all_pages(client, {"q": "zzqacatalogunfindable8fc249ad"})
        assert products == [] and payload["total"] == 0
        return {"matches": 0}
    check("No-match result is explicit and empty", no_match)
    for case in representative_cart_cases(rows):
        def cart_check(case=case):
            response = client.post("/api/v1/procurement/sessions/from-product", json={"product_id": case["id"], "quantity": str(case["quantity"]), "unit": case["unit"], "date": str(date.today() + timedelta(days=2)), "mode": "fixture", "apply_preferences": False})
            assert response.status_code == 200, f"Product-to-cart HTTP {response.status_code}: {response.text[:200]}"
            session = response.json()
            line = session["lines"][0]
            assert line["selected_product_id"] == case["id"]
            chosen = next(p for p in line["candidates"] if p["id"] == case["id"])
            units = expected_sales_units(case["quantity"], case["capacity"], case["lot"])
            assert Decimal(chosen["quantity_sales_units"]) == units, "Incorrect whole-pack rounding"
            assert chosen["unit_price"] is not None and chosen["line_total"] is not None, "Authored available price not quoted"
            assert Decimal(chosen["line_total"]) == (Decimal(chosen["unit_price"]) * units).quantize(Decimal(".01"))
            assert session.get("receipt") is None
            return {"category": case["category"], "unit": case["unit"], "sales_units": str(units)}
        check("Dynamic " + case["unit"] + " catalog selection and correct pack subtotal", cart_check)
    report["check_count"] = len(report["checks"])
    report["passed"] = sum(check["passed"] for check in report["checks"])
    report["status"] = "passed" if report["passed"] == report["check_count"] else "failed"
    report["elapsed_seconds"] = round(time.perf_counter() - started, 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Optional existing local/hosted origin; no order commitment")
    parser.add_argument("--output", type=Path, default=ROOT / ".local/catalog-qa-report.json")
    args = parser.parse_args()
    from backend import catalog
    from backend.config import access_codes
    rows = catalog.load_catalog()
    if not rows:
        parser.error("The original private catalog must be installed first")
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "scope": "Actual four private source datasets to authenticated API and fixture cart; no confirm/provider calls", "orders_created": 0, "source_inventory": inventory(), "active_products": len(active_records(rows)), "categories": len(category_groups(rows)), "checks": []}
    if args.url:
        import httpx
        with httpx.Client(base_url=args.url, timeout=60) as client:
            response = client.post("/api/v1/session", json={"access_code": access_codes()["buyer"]})
            assert response.status_code == 200, "Buyer authentication failed"
            run_matrix(client, rows, report)
    else:
        from fastapi.testclient import TestClient
        from backend.app import create_app
        from backend.store import Store
        with tempfile.TemporaryDirectory(prefix="aimo-catalog-qa-") as directory:
            store = Store(Path(directory) / "qa.sqlite3", postgres=False)
            with TestClient(create_app(store)) as client:
                response = client.post("/api/v1/session", json={"access_code": access_codes()["buyer"]})
                assert response.status_code == 200, "Buyer authentication failed"
                run_matrix(client, rows, report)
                assert store.spent() == 0, "QA must not commit orders"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({"status": report["status"], "passed": report["passed"], "checks": report["check_count"], "elapsed_seconds": report["elapsed_seconds"], "report": str(args.output)}, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
