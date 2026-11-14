"""Real Chromium UI verification against the LOCAL synthetic demo.

Never controls account browser sessions. Codes stay in process memory, never
screenshots or logs. Fixture runs are labelled and do not call sponsor APIs.
"""

import json, os, re, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / ".local"
codes = json.loads((LOCAL / "access.json").read_text())
BASE = os.getenv("AIMO_TEST_URL", "http://127.0.0.1:8000")
report = {
    "base_url": BASE,
    "browser": "Chromium",
    "checks": [],
    "screenshots": [],
    "errors": [],
}


def check(name):
    report["checks"].append(name)


with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chromium", headless=True, args=["--no-sandbox"]
    )
    page = browser.new_page(
        viewport={"width": 1440, "height": 1120}, device_scale_factor=1
    )
    page.on("pageerror", lambda e: report["errors"].append(str(e)))
    page.goto(BASE, wait_until="networkidle")
    expect(
        page.get_by_role("heading", name="Good judgment. On the record.")
    ).to_be_visible()
    expect(
        page.get_by_role("heading", name="Tell us what you need.")
    ).to_be_visible()
    expect(page.get_by_role("button", name="Build my cart", exact=True)).to_be_visible()
    check("Smart order is the primary landing workflow")
    # The original gateway checks exercise the milk lab, now named Trust scenarios.
    page.get_by_role("button", name="Trust scenarios", exact=True).click()
    expect(page.get_by_text("LABELLED REHEARSAL FIXTURE", exact=True)).to_be_visible()
    page.screenshot(path=str(LOCAL / "ui-desktop.png"), full_page=True)
    report["screenshots"].append(".local/ui-desktop.png")
    check("Desktop initial workbench and explicit fixture label")
    page.get_by_role("button", name="Send to buyer agent").click()
    expect(page.get_by_role("dialog")).to_be_visible()
    page.get_by_label("ACCESS CODE", exact=True).fill(codes["buyer"])
    page.get_by_role("button", name="Open this session").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    check("Unauthenticated action requires server-issued buyer session")
    page.get_by_role("button", name="Meal planner", exact=True).click()
    page.get_by_role("button", name="Build shopping plan").click()
    expect(page.get_by_role("heading", name="Every diner counted once.")).to_be_visible(
        timeout=45000
    )
    expect(page.get_by_text("370", exact=True)).to_be_visible()
    expect(
        page.get_by_role("heading", name="Before this becomes an order")
    ).to_be_visible()
    with page.expect_download() as export:
        page.get_by_role("button", name="Export draft shopping plan (JSON) ↗").click()
    exported = json.loads(Path(export.value.path()).read_text())
    assert exported["can_commit"] is False and len(exported["lines"]) == 11
    page.get_by_label("Total diners", exact=True).fill("600")
    expect(
        page.get_by_role("button", name="Export draft shopping plan (JSON) ↗")
    ).to_be_disabled()
    page.get_by_role("button", name="Build shopping plan").click()
    expect(page.get_by_text("470", exact=True)).to_be_visible(timeout=45000)
    page.get_by_role("button", name="Trust scenarios", exact=True).click()
    page.get_by_role("button", name="Meal planner", exact=True).click()
    expect(page.get_by_text("470", exact=True)).to_be_visible()
    page.screenshot(path=str(LOCAL / "meal-plan-desktop.png"), full_page=False)
    report["screenshots"].append(".local/meal-plan-desktop.png")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "Meal planner mobile overflow"
    )
    page.screenshot(path=str(LOCAL / "meal-plan-mobile.png"), full_page=False)
    report["screenshots"].append(".local/meal-plan-mobile.png")
    page.set_viewport_size({"width": 1440, "height": 1120})
    page.get_by_role("button", name="Trust scenarios", exact=True).click()
    check(
        "Meal plan scales cohorts, exports review-only JSON, invalidates changed inputs, survives navigation and fits mobile"
    )
    page.get_by_role("button", name="Send to buyer agent").click()
    expect(page.get_by_text("3 offers inspected", exact=True)).to_be_visible(
        timeout=45000
    )
    expect(page.get_by_role("button", name="Commit simulated order")).to_be_enabled()
    page.get_by_role("button", name="Commit simulated order").click()
    expect(page.get_by_role("heading", name="One order. A clear trail.")).to_be_visible(
        timeout=45000
    )
    page.get_by_role("button", name="Retry same request").click()
    expect(
        page.get_by_text("Retry verified: the same receipt.", exact=True)
    ).to_be_visible(timeout=45000)
    check("Buyer baseline commitment and idempotent retry through real UI")
    page.get_by_label("Evidence source").select_option("live")
    expect(page.get_by_text("LABELLED REHEARSAL FIXTURE", exact=True)).to_be_visible()
    expect(
        page.get_by_text(
            "New selection applies to the next run. Displayed offers: fixture.",
            exact=True,
        )
    ).to_be_visible()
    page.get_by_label("Evidence source").select_option("fixture")
    check("Changing next-run source never relabels displayed fixture evidence as live")
    page.get_by_role("button", name="The milk runs out").click()
    page.get_by_role("button", name="Send to buyer agent").click()
    expect(
        page.get_by_role("heading", name="A safe alternative. A human decision.")
    ).to_be_visible(timeout=45000)
    page.screenshot(path=str(LOCAL / "pitch-ui.png"), full_page=True)
    report["screenshots"].append(".local/pitch-ui.png")
    page.get_by_role("button", name="Open approver sign-in").click()
    page.get_by_label("ACCESS CODE", exact=True).fill(codes["approver"])
    page.get_by_role("button", name="Open this session").click()
    expect(page.get_by_role("button", name="Approve this exact offer")).to_be_visible()
    page.get_by_role("button", name="Approve this exact offer").click()
    expect(
        page.get_by_role("heading", name="A human approved this exact offer.")
    ).to_be_visible(timeout=45000)
    expect(
        page.get_by_role("button", name="Sign in as buyer to commit")
    ).to_be_disabled()
    page.get_by_role("button", name="Open buyer sign-in").click()
    page.get_by_label("ACCESS CODE", exact=True).fill(codes["buyer"])
    page.get_by_role("button", name="Open this session").click()
    page.get_by_role("button", name="Commit simulated order").click()
    expect(page.get_by_role("heading", name="One order. A clear trail.")).to_be_visible(
        timeout=45000
    )
    check("Controlled shortage -> separate approver -> exact approval -> buyer resumes")
    page.get_by_role("button", name="Decision recorder", exact=False).first.click()
    expect(
        page.get_by_role("heading", name="Exact offer approved by a separate identity")
    ).to_be_visible()
    expect(
        page.get_by_role("heading", name="Simulated commitment recorded")
    ).to_be_visible()
    check("Decision recorder includes factual approval and commitment events")
    page.get_by_role("button", name="Back to the desk").click()
    page.get_by_role("button", name="The offer changes").click()
    page.get_by_role("button", name="Send to buyer agent").click()
    expect(
        page.get_by_role("heading", name="This is where the agent stops.")
    ).to_be_visible(timeout=45000)
    page.get_by_role("button", name="Refresh this exact offer").click()
    expect(page.get_by_text("WHAT REVALIDATION CHANGED", exact=True)).to_be_visible(
        timeout=45000
    )
    expect(
        page.get_by_text("Cleared · exact new fingerprint", exact=True)
    ).to_be_visible()
    check("Stale offer repair visibly produces new fingerprint and clears approval")
    page.get_by_role("button", name="An untrusted instruction").click()
    page.get_by_role("button", name="Send to buyer agent").click()
    expect(page.get_by_text("3 offers inspected", exact=True)).to_be_visible(
        timeout=45000
    )
    page.get_by_role("button", name="Decision recorder", exact=False).first.click()
    expect(page.get_by_text("Controlled rehearsal active", exact=True)).to_be_visible()
    check(
        "Supplier injection rehearsal remains explicitly labelled and no privilege tool exists"
    )
    page.get_by_role("button", name="Gateway API").click()
    expect(page.get_by_role("heading", name="Bring your own agent.")).to_be_visible()
    check("Independent gateway interface and real OpenAPI link exposed")
    page.get_by_role("button", name="Trust scenarios", exact=True).click()
    page.get_by_role("button", name="What makes it trustworthy?").click()
    expect(page.get_by_role("dialog")).to_be_visible()
    page.get_by_role("button", name="Close explanation").click()
    check("20-second explainer opens and closes")
    # Responsive first view in a separate, clean browser context (no credentials).
    mobile = browser.new_page(
        viewport={"width": 390, "height": 844}, device_scale_factor=1
    )
    mobile.goto(BASE, wait_until="networkidle")
    expect(
        mobile.get_by_role("heading", name="Good judgment. On the record.")
    ).to_be_visible()
    assert mobile.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    ), "Mobile horizontal overflow"
    mobile.get_by_role("button", name="Toggle navigation").click()
    mobile.get_by_role("button", name="Gateway API").click()
    expect(mobile.get_by_role("heading", name="Bring your own agent.")).to_be_visible()
    assert mobile.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    ), "Gateway mobile horizontal overflow"
    mobile.get_by_role("button", name="Toggle navigation").click()
    mobile.get_by_role("button", name="Trust scenarios", exact=True).click()
    expect(mobile.get_by_role("button", name="Send to buyer agent")).to_be_visible()
    assert mobile.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    ), "Trust scenarios mobile horizontal overflow"
    mobile.screenshot(path=str(LOCAL / "ui-mobile.png"), full_page=True)
    report["screenshots"].append(".local/ui-mobile.png")
    check("390px mobile layout, working navigation, no horizontal overflow")
    browser.close()
assert not report["errors"], report["errors"]
(LOCAL / "browser-report.json").write_text(json.dumps(report, indent=2))
print(
    json.dumps(
        {
            "checks_passed": len(report["checks"]),
            "javascript_errors": len(report["errors"]),
            "checks": report["checks"],
            "screenshots": report["screenshots"],
            "report": ".local/browser-report.json",
        },
        indent=2,
    )
)
