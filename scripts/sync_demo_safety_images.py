"""Fetch the approved PubChem safety-image fixture set and mirror it."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os

from backend.services.pubchem_service import get_safety_info

# This is a one-time fixture-prep script. TLS verification is always enabled.
# An operator may provide a trusted CA bundle explicitly for a managed network;
# an absent or invalid path falls back to Requests' system trust store.
_CA_BUNDLE_ENV_VARS = ("DEMO_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE")


def tls_verify_setting() -> str | bool:
    """Return a strict Requests TLS setting, optionally using a CA bundle."""
    for variable in _CA_BUNDLE_ENV_VARS:
        candidate = os.environ.get(variable)
        if candidate:
            if not os.path.isfile(candidate):
                raise ValueError(f"configured CA bundle does not exist: {candidate}")
            return candidate
    return True

CANONICAL_DIR = ROOT / "backend" / "demo_fixtures" / "safety_images"
MIRROR_DIR = ROOT / "frontend" / "public" / "demo_fixtures" / "safety_images"
EXPECTED_CIDS = (18616, 11138, 3776, 280, 947, 702)
NFPA_CIDS = (3776, 947, 702)


def collect_safety_info() -> dict[int, dict]:
    return {cid: get_safety_info(cid) for cid in EXPECTED_CIDS}


def _filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    if not name:
        raise ValueError(f"source URL has no filename: {url}")
    return name.lower()


def _download(url: str) -> tuple[bytes, str]:
    response = requests.get(url, timeout=30, verify=tls_verify_setting())
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if not content_type.startswith("image/"):
        raise ValueError(f"unexpected content type for {url}: {content_type}")
    if not response.content:
        raise ValueError(f"empty response for {url}")
    return response.content, content_type


def build_fixture(dry_run: bool = False) -> dict:
    safety = collect_safety_info()
    print(json.dumps(safety, indent=2, sort_keys=True))
    if dry_run:
        return {"safety": safety}

    (CANONICAL_DIR / "ghs").mkdir(parents=True, exist_ok=True)
    (CANONICAL_DIR / "nfpa").mkdir(parents=True, exist_ok=True)
    entries = []
    ghs_seen: dict[str, str] = {}

    for cid in EXPECTED_CIDS:
        info = safety[cid]
        ghs_entries = []
        for source_url in info.get("ghs_icons", []):
            filename = _filename(source_url)
            local_url = f"/demo_fixtures/safety_images/ghs/{filename}"
            if filename not in ghs_seen:
                content, content_type = _download(source_url)
                (CANONICAL_DIR / "ghs" / filename).write_bytes(content)
                ghs_seen[filename] = source_url
            path = CANONICAL_DIR / "ghs" / filename
            content = path.read_bytes()
            ghs_entries.append({
                "local_url": local_url,
                "source_url": source_url,
                "content_type": "image/svg+xml",
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            })

        nfpa = None
        if cid in NFPA_CIDS:
            source_url = info.get("nfpa_image")
            if not source_url:
                raise ValueError(f"CID {cid} is required to have an NFPA source URL")
            filename = f"nfpa-cid-{cid}.svg"
            content, content_type = _download(source_url)
            path = CANONICAL_DIR / "nfpa" / filename
            path.write_bytes(content)
            nfpa = {
                "local_url": f"/demo_fixtures/safety_images/nfpa/{filename}",
                "source_url": source_url,
                "content_type": content_type,
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        elif info.get("nfpa_image") is not None:
            raise ValueError(f"CID {cid} unexpectedly has an NFPA source URL")

        entries.append({"cid": cid, "ghs_icons": ghs_entries, "nfpa_image": nfpa})

    manifest = {"assets": entries, "retrieval_date": date.today().isoformat()}
    (CANONICAL_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (CANONICAL_DIR / "README.md").write_text(
        "# Real PubChem safety images\n\n"
        "These are real PubChem hazard pictograms and NFPA 704 images captured "
        "for the offline demo fixture. The CID mapping follows PubChem's current "
        "GHS classification response. Keep PubChem attribution and legal review "
        "as a P1 release gate before public distribution. The fixture is not a "
        "substitute for a current safety data sheet.\n",
        encoding="utf-8",
    )
    if MIRROR_DIR.exists():
        shutil.rmtree(MIRROR_DIR)
    shutil.copytree(CANONICAL_DIR, MIRROR_DIR)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = build_fixture(dry_run=args.dry_run)
    if not args.dry_run:
        print(json.dumps({"assets": len(result["assets"]), "retrieval_date": result["retrieval_date"]}))
