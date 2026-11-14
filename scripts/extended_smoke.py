"""Verify the hosted account/media/procurement extension with isolated demo users.

Usage: .venv/bin/python scripts/extended_smoke.py --url https://... [--live]
Only simulated orders are confirmed, in registered QA workspaces. The shared
Aurora ledger is read before/after and must remain unchanged. Private generated
account credentials are kept in an ignored 0600 file; reports omit credentials,
cookies, uploaded media and extracted transcripts. Reusing the file recovers the
same accounts; existing synthetic spend is respected and never reset.
"""

import argparse
import json
import os
import re
import secrets
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.config import BUYER, CUSTOMER, LOCAL, access_codes

REPORT = LOCAL / "extended-deployed-report.json"
ACCESS = LOCAL / "extended-test-access.json"
API = "/api/v1"
CARTS = API + "/procurement/sessions"


class SmokeFailure(Exception):
    """Messages contain only fixed check labels and sanitized HTTP metadata."""


def private_write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as file:
        os.fchmod(file.fileno(), 0o600)
        json.dump(value, file, indent=2)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def cookie_flags(response):
    cookies = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookies.load(header)
    cookie = cookies.get("aimo_session")
    return {"http_only": bool(cookie and cookie["httponly"]), "secure": bool(cookie and cookie["secure"]), "same_site": cookie["samesite"].lower() if cookie else None, "max_age": int(cookie["max-age"]) if cookie and cookie["max-age"] else None}


class Smoke:
    def __init__(self, base, live):
        self.base = base
        self.started = time.perf_counter()
        self.last_check = self.started
        self.current = "initialization"
        self.report = {"url": base, "started_at": datetime.now(timezone.utc).isoformat(), "orders": "simulated_only", "live_requested": live, "checks": [], "http_calls": [], "check_count": 0, "status": "running"}
        self.flush()

    def flush(self):
        self.report["elapsed_seconds"] = round(time.perf_counter() - self.started, 3)
        private_write(REPORT, self.report)

    def checked(self, name, condition):
        self.current = name
        if not condition:
            raise SmokeFailure(name)
        now = time.perf_counter()
        self.report["checks"].append({"name": name, "elapsed_ms": round((now - self.last_check) * 1000, 2)})
        self.last_check = now
        self.report["check_count"] = len(self.report["checks"])
        self.flush()
        print(f"PASS {len(self.report['checks']):02d} {name}", flush=True)

    def request(self, client, method, path, expected=200, **options):
        self.current = method + " " + re.sub(r"/procurement/sessions/[^/?]+", "/procurement/sessions/{id}", path.split("?")[0])
        started = time.perf_counter()
        response = client.request(method, path, **options)
        self.report["http_calls"].append({"method": method, "path": self.current.split(" ", 1)[1], "status": response.status_code, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)})
        self.flush()
        statuses = {expected} if isinstance(expected, int) else set(expected)
        if response.status_code not in statuses:
            code = ""
            try:
                detail = response.json().get("detail")
                code = detail.get("code", "") if isinstance(detail, dict) else ""
            except (ValueError, AttributeError):
                pass
            safe_code = code if isinstance(code, str) and re.fullmatch(r"[a-z_]{1,60}", code) else "unspecified"
            raise SmokeFailure(f"{self.current}: HTTP {response.status_code}, code {safe_code}")
        return response

    def data(self, client, method, path, **options):
        return self.request(client, method, path, **options).json()

    def action(self, client, cart, operation, **payload):
        return self.data(client, "POST", CARTS + "/" + cart["id"] + "/actions", json={"version": cart["version"], "action": operation, **payload})


def line_named(cart, word):
    matches = [line for line in cart["lines"] if word in line["requested_label"].casefold()]
    if len(matches) != 1:
        raise SmokeFailure("Expected one measured " + word + " line")
    return matches[0]


def account_state(base):
    if ACCESS.exists():
        if ACCESS.stat().st_mode & 0o077:
            raise SmokeFailure("Private QA account file permissions must be 0600")
        state = json.loads(ACCESS.read_text())
        if state.get("url") == base:
            return state
    suffix = uuid.uuid4().hex[:14]
    state = {"url": base, "accounts": {key: {"username": "ext-" + key + "-" + suffix, "password": secrets.token_urlsafe(24), "registered": False} for key in ["a", "b"]}}
    private_write(ACCESS, state)
    return state


def login_account(smoke, client, state, key, remember):
    account = state["accounts"][key]
    if not account.get("registered"):
        response = smoke.request(client, "POST", API + "/auth/register", expected={201, 409}, json={"name": "Extension QA kitchen " + key.upper(), "username": account["username"], "password": account["password"], "invite_code": access_codes()["buyer"], "remember_me": remember})
        if response.status_code == 201:
            account["registered"] = True
            account["workspace_id"] = response.json()["workspace_id"]
            private_write(ACCESS, state)
            return response
    response = smoke.request(client, "POST", API + "/auth/login", json={"username": account["username"], "password": account["password"], "remember_me": remember})
    account.update(registered=True, workspace_id=response.json()["workspace_id"])
    private_write(ACCESS, state)
    return response


def verify(base, live):
    smoke = Smoke(base, live)
    timeout = httpx.Timeout(180, connect=15, write=30, pool=15)
    try:
        state = account_state(base)
        with httpx.Client(base_url=base, timeout=timeout, follow_redirects=False) as public, httpx.Client(base_url=base, timeout=timeout) as shared, httpx.Client(base_url=base, timeout=timeout) as a, httpx.Client(base_url=base, timeout=timeout) as b:
            health = smoke.request(public, "GET", "/health")
            smoke.checked("Hosted health and persistent storage", health.json().get("status") == "ok" and health.json().get("storage") in {"sqlite", "postgres"})
            smoke.request(public, "GET", CARTS + "/not-owned", expected=401)
            smoke.checked("Private cart requires authentication", True)
            policy = health.headers.get("permissions-policy", "")
            smoke.checked("Same-origin camera and microphone allowed", "camera=(self)" in policy and "microphone=(self)" in policy)
            schema = smoke.data(public, "GET", "/openapi.json")
            refs = schema["paths"]
            ref = refs[CARTS]["post"]["responses"]["200"]["content"]["application/json"]["schema"].get("$ref", "")
            verify_ref = refs[CARTS + "/{id}/verify"]["get"]["responses"]["200"]["content"]["application/json"]["schema"].get("$ref", "")
            smoke.checked("Hosted OpenAPI validates cart and receipt responses", ref.endswith("/ProcurementSessionResponse") and verify_ref.endswith("/ReceiptVerificationResponse"))
            smoke.checked("Hosted OpenAPI exposes typed image and audio input", all(refs[API + "/input/" + kind]["post"]["responses"]["200"]["content"]["application/json"]["schema"].get("$ref", "").endswith("/InputTextResponse") for kind in ["image", "audio"]))

            smoke.data(shared, "POST", API + "/session", json={"access_code": access_codes()["buyer"]})
            default_before = Decimal(smoke.data(shared, "GET", API + "/workspace")["mandate"]["spent"])
            smoke.checked("Shared demonstration ledger read without commitment", smoke.data(shared, "GET", API + "/session")["buyer_id"] == BUYER)

            ra = login_account(smoke, a, state, "a", True)
            rb = login_account(smoke, b, state, "b", False)
            ia, ib = ra.json(), rb.json()
            smoke.checked("Two isolated registered buyer workspaces", ia["role"] == ib["role"] == "buyer" and ia["buyer_id"] != ib["buyer_id"] and ia["customer_id"] != ib["customer_id"] and ia["buyer_id"] != BUYER and ib["buyer_id"] != BUYER)
            fa, fb = cookie_flags(ra), cookie_flags(rb)
            smoke.checked("Remember Me cookie is secure, HttpOnly and persistent 30 days", fa == {"http_only": True, "secure": True, "same_site": "strict", "max_age": 2592000})
            smoke.checked("Unchecked Remember Me creates only a secure session cookie", fb == {"http_only": True, "secure": True, "same_site": "strict", "max_age": None})
            now = datetime.now(timezone.utc)
            smoke.checked("Server session lifetimes match Remember Me choices", 29 <= (datetime.fromisoformat(ia["session_expires_at"]) - now).total_seconds() / 86400 <= 30 and 7.8 <= (datetime.fromisoformat(ib["session_expires_at"]) - now).total_seconds() / 3600 <= 8)
            with httpx.Client(base_url=base, timeout=timeout, cookies=a.cookies) as restored:
                smoke.checked("Remembered identity survives an independent HTTP client", smoke.data(restored, "GET", API + "/session")["buyer_id"] == ia["buyer_id"])
            smoke.checked("Private identity explicitly binds the example supplier account", ia["commercial_customer_id"] == CUSTOMER and ia["customer_id"] != CUSTOMER and "not a supplier customer contract" in ia["commercial_account_note"])
            spent_before = Decimal(smoke.data(a, "GET", API + "/workspace")["mandate"]["spent"])
            smoke.checked("QA workspace has room below its synthetic cumulative cap", spent_before + Decimal("2500") < Decimal("6000"))

            preferences = {"preferred_brand": "Valio", "preferred_origin": "finland", "preferred_organic": False, "priority": "cheapest"}
            saved = smoke.data(a, "PUT", API + "/preferences", json=preferences)
            reloaded = smoke.data(a, "GET", API + "/preferences")
            smoke.checked("Customer preferences save and reload", all(saved[k] == v for k, v in preferences.items()) and all(reloaded[k] == v for k, v in preferences.items()))
            other = smoke.data(b, "GET", API + "/preferences")
            smoke.checked("Saved preferences stay isolated from the second account", other.get("preferred_brand") is None and other.get("preferred_origin") is None)
            day = datetime.now(ZoneInfo("Europe/Helsinki")).date() + timedelta(days=2)
            cart = smoke.data(a, "POST", CARTS, json={"message": "20 litres of lactose-free milk and 1 kg of butter", "date": day.isoformat(), "mode": "fixture", "use_model": False, "apply_preferences": True})
            milk, butter = line_named(cart, "milk"), line_named(cart, "butter")
            smoke.checked("Personal two-product cart applies saved preferences", len(cart["lines"]) == 2 and milk["quantity"] == "20" and butter["quantity"] == "1" and cart["constraints"]["delivery_date"] == day.isoformat() and cart["constraints"]["preferences"] == "cheapest" and all(line.get("preferred_brand") == "Valio" and line.get("preferred_origin") == "finland" for line in cart["lines"]) and cart["can_confirm"])
            smoke.checked("Fixture commercial facts are labelled and supplier binding is explicit", cart["commercial_customer_id"] == CUSTOMER and cart["customer_id"] == ia["customer_id"] and {c["source"] for line in cart["lines"] for c in line["candidates"]} == {"authored_fixture"})
            smoke.request(b, "GET", CARTS + "/" + cart["id"], expected=404)
            smoke.checked("Another customer cannot read the private cart", True)
            smoke.request(a, "POST", CARTS + "/" + cart["id"] + "/approve", expected=403, json={"fingerprint": cart["offer"]["fingerprint"]})
            smoke.checked("A buyer cannot approve its own basket", True)
            old_version = cart["version"]
            butter_before = (butter["id"], butter["selected_product_id"], butter["quantity"])
            for number in [1, 2]:
                cart = smoke.action(a, cart, "message", message="Choose cheaper milk")
                unchanged = line_named(cart, "butter")
                smoke.checked(f"Cheaper follow-up {number} preserves the unrelated butter selection", (unchanged["id"], unchanged["selected_product_id"], unchanged["quantity"]) == butter_before and cart["can_confirm"] and not cart.get("ambiguities"))
            smoke.request(a, "POST", CARTS + "/" + cart["id"] + "/actions", expected=409, json={"version": old_version, "action": "quote"})
            smoke.checked("Stale cart versions are rejected", True)
            cart = smoke.action(a, cart, "set_date", date=(day + timedelta(days=1)).isoformat())
            smoke.checked("Explicit delivery-date change persists and requotes", cart["constraints"]["delivery_date"] == (day + timedelta(days=1)).isoformat() and cart["can_confirm"])
            cart = smoke.action(a, cart, "set_budget", budget="0.01")
            smoke.checked("A hard customer budget blocks confirmation", not cart["can_confirm"] and cart["offer"] is None and cart["order_status"] != "READY_TO_ORDER")
            cart = smoke.action(a, cart, "set_budget", budget="500")
            smoke.checked("Explicit budget correction restores the complete cart", cart["can_confirm"] and cart["constraints"]["budget"] == "500")
            small_key = "extended-small-" + uuid.uuid4().hex
            exact = {"fingerprint": cart["offer"]["fingerprint"]}
            closed = smoke.data(a, "POST", CARTS + "/" + cart["id"] + "/confirm", json=exact, headers={"Idempotency-Key": small_key})
            receipt = closed["receipt"]
            smoke.checked("Small registered-workspace order is only simulated", receipt["simulated"] is True and receipt["status"] == "simulated" and receipt["buyer_id"] == ia["buyer_id"] and receipt["customer_id"] == ia["customer_id"])
            replay = smoke.data(a, "POST", CARTS + "/" + cart["id"] + "/confirm", json=exact, headers={"Idempotency-Key": small_key})
            smoke.checked("Same-key confirmation returns the same receipt", replay["receipt"]["id"] == receipt["id"] and replay["receipt"]["idempotent_replay"])
            proof = smoke.data(a, "GET", CARTS + "/" + cart["id"] + "/verify")
            smoke.checked("Read-only receipt verification confirms record and tenant scope", proof["integrity_valid"] and proof["scope_valid"] and proof["simulated"])
            with httpx.Client(base_url=base, timeout=timeout, cookies=a.cookies) as restored:
                recovered = smoke.data(restored, "GET", CARTS + "/" + cart["id"])
                smoke.checked("Saved cart and receipt recover through a fresh client", recovered["receipt"]["id"] == receipt["id"])

            approval_cart = smoke.data(a, "POST", CARTS, json={"message": "1500 litres of lactose-free milk", "date": day.isoformat(), "mode": "fixture", "use_model": False, "apply_preferences": False})
            approval_cart = smoke.action(a, approval_cart, "set_query", line_id=approval_cart["lines"][0]["id"], query="464306")
            smoke.checked("Exact SKU fixture basket requires a separate 1725 EUR approval", approval_cart["cart"]["subtotal"] == "1725.00" and approval_cart["lines"][0]["selected_product_id"] == "464306" and approval_cart["approval"]["status"] == "required" and not approval_cart["can_confirm"])
            fingerprint = {"fingerprint": approval_cart["offer"]["fingerprint"]}
            approval_path = CARTS + "/" + approval_cart["id"]
            blocked = smoke.request(a, "POST", approval_path + "/confirm", expected={403, 409}, json=fingerprint, headers={"Idempotency-Key": "extended-unapproved-" + uuid.uuid4().hex})
            smoke.checked("Unapproved spending cannot be confirmed by the buyer", blocked.json().get("detail", {}).get("code") in {"confirmation_blocked", "approval_required"})
            manager = smoke.data(a, "POST", API + "/session", json={"access_code": access_codes()["approver"], "workspace_id": ia["workspace_id"]})
            smoke.checked("Separate manager code selects the exact private workspace", manager["role"] == "approver" and manager["buyer_id"] == ia["buyer_id"] and manager["customer_id"] == ia["customer_id"])
            approved = smoke.data(a, "POST", approval_path + "/approve", json=fingerprint)
            smoke.checked("Manager approval binds the exact current fingerprint", approved["offer"]["approved"] and approved["approval"]["approved"] and approved["offer"]["fingerprint"] == fingerprint["fingerprint"])
            buyer_login = smoke.data(a, "POST", API + "/auth/login", json={"username": state["accounts"]["a"]["username"], "password": state["accounts"]["a"]["password"], "remember_me": True})
            smoke.checked("Account login resumes the buyer without manager authority", buyer_login["role"] == "buyer" and buyer_login["buyer_id"] == ia["buyer_id"])
            approved_receipt = smoke.data(a, "POST", approval_path + "/confirm", json=fingerprint, headers={"Idempotency-Key": "extended-approved-" + uuid.uuid4().hex})["receipt"]
            smoke.checked("Approved basket creates a tenant-scoped simulated receipt", approved_receipt["simulated"] and approved_receipt["total"] == "1725.00" and approved_receipt["buyer_id"] == ia["buyer_id"] and approved_receipt["approval"]["fingerprint"] == fingerprint["fingerprint"])
            smoke.request(b, "GET", approval_path + "/verify", expected=404)
            smoke.checked("Another customer cannot verify the private receipt", True)

            image = LOCAL / "benchmark-shopping-list.png"
            audio = LOCAL / "benchmark-shopping-list.wav"
            if not audio.is_file():
                audio = LOCAL / "benchmark-procurement.wav"
            smoke.checked("Authored benchmark media files are available", image.is_file() and audio.is_file())
            before_media = smoke.data(a, "GET", CARTS + "/" + cart["id"])
            with image.open("rb") as file:
                ocr = smoke.data(a, "POST", API + "/input/image?provider=local", files={"file": ("fixture.png", file, "image/png")})
            smoke.checked("Actual local OCR returns editable milk and butter text", ocr["review_required"] is True and ocr["source"].startswith("Local Tesseract") and all(word in ocr["text"].casefold() for word in ["milk", "butter"]))
            smoke.report["ocr"] = {"source": ocr["source"], "elapsed_ms": ocr["elapsed_ms"], "required_terms_verified": ["milk", "butter"]}
            with audio.open("rb") as file:
                speech = smoke.data(a, "POST", API + "/input/audio", files={"file": ("fixture.wav", file, "audio/wav")})
            smoke.checked("Actual local speech recognition returns editable milk and butter text", speech["review_required"] is True and speech["source"].startswith("Local Whisper") and all(word in speech["text"].casefold() for word in ["milk", "butter"]))
            smoke.report["audio"] = {"source": speech["source"], "elapsed_ms": speech["elapsed_ms"], "required_terms_verified": ["milk", "butter"]}
            with image.open("rb") as file:
                refused = smoke.request(a, "POST", API + "/input/image?provider=nvidia&cloud_consent=false", expected=422, files={"file": ("fixture.png", file, "image/png")})
            smoke.checked("Explicit cloud OCR denial prevents external reading", refused.json().get("detail", {}).get("code") == "cloud_consent_required")
            with image.open("rb") as file:
                smoke.request(a, "POST", API + "/input/image", expected=403, headers={"Origin": "https://unrelated.example"}, files={"file": ("fixture.png", file, "image/png")})
            smoke.checked("Cross-origin authenticated uploads are rejected", True)
            after_media = smoke.data(a, "GET", CARTS + "/" + cart["id"])
            smoke.checked("Media extraction does not mutate the saved cart or receipt", before_media["version"] == after_media["version"] and before_media["receipt"]["id"] == after_media["receipt"]["id"])
            if live:
                live_cart = smoke.data(a, "POST", CARTS, json={"message": "20 litres of lactose-free milk and 1 kg of butter. Choose the cheapest suitable products.", "date": day.isoformat(), "mode": "live", "use_model": True, "apply_preferences": True})
                smoke.checked("Live NVIDIA typed interpretation extracts both products", live_cart.get("interpretation_source") == "NVIDIA typed interpretation" and len(live_cart["lines"]) == 2 and line_named(live_cart, "milk") and line_named(live_cart, "butter"))
                sources = {c["source"] for line in live_cart["lines"] for c in line["candidates"]}
                smoke.checked("Live Valio quote uses the example commercial account within the private workspace", sources == {"live_valio_sandbox"} and live_cart["commercial_customer_id"] == CUSTOMER and live_cart["customer_id"] == ia["customer_id"] and live_cart["receipt"] is None)
                smoke.report["live"] = {"interpretation_source": live_cart["interpretation_source"], "price_sources": sorted(sources), "order_status": live_cart["order_status"], "committed": False}
            final_a = Decimal(smoke.data(a, "GET", API + "/workspace")["mandate"]["spent"])
            final_b = Decimal(smoke.data(b, "GET", API + "/workspace")["mandate"]["spent"])
            final_default = Decimal(smoke.data(shared, "GET", API + "/workspace")["mandate"]["spent"])
            smoke.checked("Only the registered QA ledger spends and remains below 6000 EUR", final_a == spent_before + Decimal(receipt["total"]) + Decimal("1725.00") and final_a < Decimal("6000") and final_b == 0)
            smoke.checked("Shared Aurora synthetic spending remains unchanged", final_default == default_before)
            smoke.report["synthetic_spend"] = {"registered_before": str(spent_before), "registered_after": str(final_a), "shared_unchanged": True, "second_account": str(final_b)}
            smoke.request(b, "DELETE", API + "/session")
            smoke.checked("Logout revokes the second account session", smoke.data(b, "GET", API + "/session").get("role") is None)
            smoke.report["status"] = "passed"
            smoke.flush()
            print(f"PASS {smoke.report['check_count']} checks in {smoke.report['elapsed_seconds']:.2f}s; report: {REPORT}", flush=True)
            return 0
    except Exception as exc:
        # Never print a response body, request payload, cookie or exception repr.
        smoke.report["status"] = "failed"
        smoke.report["failure"] = {"check": smoke.current, "type": type(exc).__name__, "message": str(exc) if isinstance(exc, SmokeFailure) else "Verification could not finish; no secret payload was recorded."}
        smoke.flush()
        print(f"FAIL after {smoke.report['check_count']} checks: {smoke.current} ({type(exc).__name__}); see {REPORT}", file=sys.stderr, flush=True)
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    parts = urlsplit(base)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment or parts.path:
        parser.error("Use a credential-free HTTPS origin without a path, query or fragment.")
    return verify(base, args.live)


if __name__ == "__main__":
    raise SystemExit(main())
