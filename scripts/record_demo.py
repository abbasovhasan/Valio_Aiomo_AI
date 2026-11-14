"""Record a real, local, visibly labelled FIXTURE demonstration. No uploads.

Requires running localhost server, browser dev dependencies and ffmpeg. Commits
only simulated examples. Reset the synthetic demo ledger explicitly before use.
The buyer session is established before filming; separate approver login is shown
with a masked password field. Access codes are never printed or captured as text.
"""

import json, subprocess, time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".local/demo"
OUT.mkdir(parents=True, exist_ok=True)
codes = json.loads((ROOT / ".local/access.json").read_text())
cues = []
begin = None


def caption(text):
    cues.append([time.monotonic() - begin, text])


def hold(page, seconds=3):
    page.wait_for_timeout(seconds * 1000)


with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chromium", headless=True, slow_mo=130, args=["--no-sandbox"]
    )
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 1024},
        record_video_dir=str(OUT),
        record_video_size={"width": 1440, "height": 1024},
    )
    r = ctx.request.post(
        "http://127.0.0.1:8000/api/v1/session", data={"access_code": codes["buyer"]}
    )
    assert r.status == 200
    page = ctx.new_page()
    begin = time.monotonic()
    caption(
        "Aimo Order Desk — a real local fixture rehearsal. All orders are simulated."
    )
    page.goto("http://127.0.0.1:8000", wait_until="networkidle")
    hold(page, 4)
    caption(
        "The kitchen delegates at least 1,000 L of lactose-free milk. Hard rules stay hard."
    )
    page.get_by_role("button", name="The milk runs out").click()
    hold(page, 2)
    page.get_by_role("button", name="Send to buyer agent").click()
    expect(
        page.get_by_role("heading", name="A safe alternative. A human decision.")
    ).to_be_visible(timeout=45000)
    caption(
        "A controlled shortage blocks the €1,150 preferred offer. The compliant alternative costs €1,870."
    )
    page.locator(".offer-list").scroll_into_view_if_needed()
    hold(page, 5)
    page.locator(".offer-main").nth(1).click()
    hold(page, 4)
    caption(
        "Inspect the evidence: real pack dimensions, dietary proof, date, price and delegated spend."
    )
    page.locator(".offer-detail").scroll_into_view_if_needed()
    hold(page, 6)
    page.locator(".action-slip").scroll_into_view_if_needed()
    hold(page, 2)
    caption(
        "The buyer cannot approve itself. A separately authenticated human reviews this exact offer."
    )
    page.get_by_role("button", name="Open approver sign-in").click()
    hold(page, 2)
    page.get_by_label("ACCESS CODE", exact=True).fill(codes["approver"])
    page.get_by_role("button", name="Open this session").click()
    expect(page.get_by_role("button", name="Approve this exact offer")).to_be_visible()
    hold(page, 2)
    page.get_by_role("button", name="Approve this exact offer").click()
    expect(
        page.get_by_role("heading", name="A human approved this exact offer.")
    ).to_be_visible(timeout=45000)
    caption(
        "Approval binds buyer, basket, litres, date, total, evidence version and expiry. The approver cannot commit."
    )
    hold(page, 4)
    page.get_by_role("button", name="Open buyer sign-in").click()
    page.get_by_label("ACCESS CODE", exact=True).fill(codes["buyer"])
    page.get_by_role("button", name="Open this session").click()
    page.get_by_role("button", name="Commit simulated order").click()
    expect(page.get_by_role("heading", name="One order. A clear trail.")).to_be_visible(
        timeout=45000
    )
    caption(
        "The gateway refreshes supplier evidence and checks shared spending inside a transaction. One simulated receipt."
    )
    page.locator(".receipt-card").scroll_into_view_if_needed()
    hold(page, 5)
    page.get_by_role("button", name="Retry same request").click()
    expect(
        page.get_by_text("Retry verified: the same receipt.", exact=True)
    ).to_be_visible(timeout=45000)
    caption(
        "Retry the request: the same receipt returns. No duplicate order. No second spend."
    )
    page.locator(".receipt-card").scroll_into_view_if_needed()
    hold(page, 4)
    page.get_by_role("button", name="Open the decision recorder").click()
    expect(
        page.get_by_role("heading", name="Decisions leave fingerprints.")
    ).to_be_visible()
    caption(
        "The decision recorder exposes factual evidence and enforced boundaries, including approval and commitment."
    )
    page.get_by_role(
        "heading", name="Exact offer approved by a separate identity"
    ).scroll_into_view_if_needed()
    hold(page, 4)
    page.get_by_role("button", name="Back to the desk").click()
    page.get_by_role("button", name="The offer changes").click()
    page.get_by_role("button", name="Send to buyer agent").click()
    expect(
        page.get_by_role("heading", name="This is where the agent stops.")
    ).to_be_visible(timeout=45000)
    caption(
        "Now expire the offer deliberately. A previous decision cannot authorise stale evidence."
    )
    page.locator(".action-slip").scroll_into_view_if_needed()
    hold(page, 3)
    page.get_by_role("button", name="Refresh this exact offer").click()
    expect(page.get_by_text("WHAT REVALIDATION CHANGED", exact=True)).to_be_visible(
        timeout=45000
    )
    page.locator(".comparison-slip").scroll_into_view_if_needed()
    caption(
        "Rewind & Repair: fresh evidence, a new fingerprint, no inherited approval. The dietary rule is unchanged."
    )
    hold(page, 6)
    page.get_by_role("button", name="Gateway API").click()
    hold(page, 2)
    caption(
        "Any outside agent can use the same typed HTTP gateway. Live NVIDIA, Valio and Aiven proof is separately recorded."
    )
    page.locator(".architecture-flow").scroll_into_view_if_needed()
    hold(page, 5)
    duration = time.monotonic() - begin
    video = page.video
    ctx.close()
    source = video.path()
    browser.close()


def timestamp(sec):
    t = round(sec * 1000)
    return f"{t // 3600000:02}:{t // 60000 % 60:02}:{t // 1000 % 60:02},{t % 1000:03}"


srt = OUT / "captions.srt"
srt.write_text(
    "\n\n".join(
        f"{i + 1}\n{timestamp(start)} --> {timestamp(cues[i + 1][0] if i + 1 < len(cues) else duration)}\n{text}"
        for i, (start, text) in enumerate(cues)
    )
)
output = OUT / "aimo-order-desk-draft.mp4"
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vf",
        f"subtitles={srt}:force_style='FontName=DejaVu Sans,FontSize=9,PrimaryColour=&H00F4F3ED,BackColour=&H00323F15,OutlineColour=&H00323F15,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=18'",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "24",
        "-pix_fmt",
        "yuv420p",
        "-an",
        "-movflags",
        "+faststart",
        str(output),
    ],
    check=True,
)
seconds = float(
    subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(output),
        ]
    )
)
assert seconds <= 120, f"Demo exceeds2min: {seconds}"
(OUT / "recording-report.json").write_text(
    json.dumps(
        {
            "duration_seconds": seconds,
            "mode": "authored_fixture",
            "orders": "simulated_only",
            "audio": False,
            "public_upload": False,
            "caption_count": len(cues),
            "output": str(output),
        },
        indent=2,
    )
)
print(
    json.dumps(
        {
            "duration_seconds": seconds,
            "output": str(output),
            "captions": len(cues),
            "mode": "fixture",
            "uploaded": False,
        },
        indent=2,
    )
)
