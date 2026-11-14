"""Scan staged source and artifact text without ever printing a credential."""

import hashlib, json, subprocess, sys, zipfile
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
values = dotenv_values(ROOT / ".env")
secrets = {
    k: v.encode()
    for k, v in values.items()
    if v and any(s in k for s in ["KEY", "SECRET", "PASSWORD", "DATABASE_URL"])
}
if values.get("DATABASE_URL"):
    password = urlparse(values["DATABASE_URL"]).password
    if password:
        secrets["DATABASE_PASSWORD"] = unquote(password).encode()
access = ROOT / ".local/access.json"
if access.exists():
    secrets.update(
        {
            f"DEMO_{k.upper()}_CODE": v.encode()
            for k, v in json.loads(access.read_text()).items()
        }
    )
files = (
    subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT)
    .decode()
    .split("\0")
)
problems = []
count = 0
for name in filter(None, files):
    if (
        name == ".env"
        or name.startswith(
            (
                ".local/",
                "data/raw/",
                "node_modules/",
                "frontend/node_modules/",
                ".venv/",
            )
        )
        or (Path(name).name.startswith(".env.") and name != ".env.example")
    ):
        problems.append((name, "forbidden path"))
        continue
    path = ROOT / name
    if not path.is_file():
        continue
    count += 1
    data = subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
    blocks = [data]
    if name.endswith(".pptx"):
        import io

        with zipfile.ZipFile(io.BytesIO(data)) as z:
            blocks.extend(
                z.read(x) for x in z.namelist() if x.endswith((".xml", ".rels", ".txt"))
            )
    if name.endswith(".pdf"):
        result = subprocess.run(["pdftotext", str(path), "-"], capture_output=True)
        if result.returncode:
            problems.append((name, "PDF text extraction failed"))
        else:
            blocks.append(result.stdout)
    for key, value in secrets.items():
        if len(value) >= 8 and any(value in b for b in blocks):
            problems.append((name, "matches " + key))
    if len(data) > 10_000_000:
        problems.append((name, "unexpected large artifact"))
for name, reason in problems:
    print(name + ": " + reason)
if problems:
    raise SystemExit("Private-source scan FAILED. No push allowed.")
print(
    f"Private-source scan passed: {count} staged files; known credentials, compressed deck/PDF text, forbidden paths and large artifacts checked. No credential values printed."
)
# Also verify the prepared raw files remain byte-for-byte intact, without staging them.
for resource in json.loads((ROOT / "research/SOURCES.json").read_text())["files"]:
    p = ROOT / resource["path"]
    assert (
        p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == resource["sha256"]
    ), "Prepared dataset changed: " + resource["path"]
print("All four prepared challenge datasets retain their recorded SHA-256 checksums.")
