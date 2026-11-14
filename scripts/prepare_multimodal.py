"""Prepare public pretrained speech weights and optional rootless local OCR.

No provider credential, customer content or challenge catalog is uploaded.
Prepared weights/binaries stay under ignored .local, outside source control.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from backend.config import LOCAL

MODEL_REPOSITORY = "Systran/faster-whisper-base"
MODEL_REVISION = "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"
MODEL_FILES = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
LICENSE_URL = "https://raw.githubusercontent.com/openai/whisper/86098128c0b4f24f0e2aa2994de830614b474227/LICENSE"
LICENSE_SHA256 = "b5d65a59060e68c4ff940e1eddfa6f94b2d68fdf58ed7f4dd57721c997e35e9d"


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_model(offline=False):
    from huggingface_hub import snapshot_download
    source = Path(snapshot_download(
        MODEL_REPOSITORY, revision=MODEL_REVISION, allow_patterns=MODEL_FILES,
        cache_dir=str(LOCAL / "models"), token=False, local_files_only=offline,
    ))
    target = LOCAL / "model-bundle/whisper-base"
    target.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        original = (source / name).resolve()
        if not original.is_file():
            raise RuntimeError("The pinned speech model snapshot is incomplete: " + name)
        shutil.copyfile(original, target / name)
    license_file = target / "LICENSE"
    if not license_file.exists() or checksum(license_file) != LICENSE_SHA256:
        if offline:
            raise RuntimeError("The model LICENSE must be prepared once online before --offline.")
        response = httpx.get(LICENSE_URL, timeout=30)
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != LICENSE_SHA256:
            raise RuntimeError("The pinned model LICENSE checksum did not match.")
        license_file.write_bytes(response.content)
    manifest = {
        "repository": MODEL_REPOSITORY, "revision": MODEL_REVISION,
        "source_url": "https://huggingface.co/" + MODEL_REPOSITORY + "/tree/" + MODEL_REVISION,
        "license": "MIT", "license_source": LICENSE_URL,
        "files": {name: {"bytes": (target / name).stat().st_size, "sha256": checksum(target / name)}
                  for name in MODEL_FILES + ["LICENSE"]},
        "runtime": {"device": "cpu", "compute_type": "int8", "cpu_threads": 2},
    }
    (target / "MODEL_PROVENANCE.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Prepared public pretrained Whisper base with LICENSE and checksums:", target)
    print("Set AIMO_WHISPER_MODEL_PATH to that absolute directory for offline runtime loading.")


def prepare_ocr():
    if not shutil.which("apt-get") or not shutil.which("dpkg-deb"):
        raise RuntimeError("Rootless OCR setup needs Debian/Ubuntu apt-get and dpkg-deb, or install Tesseract + eng/fin through your OS package manager.")
    packages = ["tesseract-ocr", "libtesseract5", "liblept5", "tesseract-ocr-eng", "tesseract-ocr-fin", "tesseract-ocr-osd"]
    cache = LOCAL / "tesseract-debs"
    target = LOCAL / "tesseract"
    cache.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    # Uses the OS's configured trusted package repository; no sudo/global install.
    subprocess.run(["apt-get", "download", *packages], cwd=cache, check=True)
    manifest = []
    for archive in sorted(cache.glob("*.deb")):
        subprocess.run(["dpkg-deb", "-x", str(archive), str(target)], check=True)
        manifest.append({"archive": archive.name, "bytes": archive.stat().st_size, "sha256": checksum(archive)})
    (target / "PACKAGE_PROVENANCE.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Prepared local OCR under", target, "(automatically discovered by backend.multimodal).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Use only an already cached speech snapshot and LICENSE.")
    parser.add_argument("--local-ocr", action="store_true", help="Extract official OS OCR packages into .local without sudo.")
    parser.add_argument("--skip-model", action="store_true")
    args = parser.parse_args()
    if not args.skip_model:
        prepare_model(args.offline)
    if args.local_ocr:
        if args.offline:
            parser.error("--local-ocr downloads OS packages; omit --offline or prepare OCR separately.")
        prepare_ocr()


if __name__ == "__main__":
    main()
