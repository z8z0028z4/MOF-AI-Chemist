"""Validate canonical PubChem Demo PNGs and sync the frontend runtime mirror."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIR = ROOT / "backend" / "demo_fixtures" / "pubchem_images"
MIRROR_DIR = ROOT / "frontend" / "public" / "demo_fixtures" / "pubchem_images"
EXPECTED_CIDS = (18616, 11138, 3776, 280, 947)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def load_manifest(manifest_path: Path = CANONICAL_DIR / "manifest.json") -> dict[str, Any]:
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("manifest assets must be a list")
    return manifest


def validate_png_response(content: bytes, content_type: str | None) -> None:
    """Reject empty, non-PNG, HTML, or non-image responses before writing."""
    if not content or not content.startswith(PNG_SIGNATURE):
        raise ValueError("PubChem fixture response is not a PNG")
    if not content_type or content_type.split(";", 1)[0].strip().lower() != "image/png":
        raise ValueError("PubChem fixture response content type is not image/png")


def validate_manifest(manifest: dict[str, Any], source_dir: Path = CANONICAL_DIR) -> list[dict[str, Any]]:
    assets = manifest["assets"]
    cids = [asset.get("cid") for asset in assets]
    if tuple(cids) != EXPECTED_CIDS:
        raise ValueError(f"manifest CID allowlist must be exactly {EXPECTED_CIDS}")
    filenames = [asset.get("filename") for asset in assets]
    if len(set(filenames)) != len(filenames) or any(not name or Path(name).name != name for name in filenames):
        raise ValueError("manifest filenames must be unique local names")

    for asset in assets:
        path = source_dir / asset["filename"]
        if not path.is_file():
            raise ValueError(f"missing canonical asset: {path}")
        content = path.read_bytes()
        validate_png_response(content, asset.get("content_type"))
        digest = hashlib.sha256(content).hexdigest()
        if digest != asset.get("sha256"):
            raise ValueError(f"SHA-256 mismatch for {path.name}")
        if len(content) != asset.get("bytes"):
            raise ValueError(f"byte count mismatch for {path.name}")
    return assets


def sync_assets(
    canonical_dir: Path = CANONICAL_DIR,
    mirror_dir: Path = MIRROR_DIR,
) -> list[Path]:
    """Copy validated canonical assets into the disposable frontend public mirror."""
    manifest = load_manifest(canonical_dir / "manifest.json")
    assets = validate_manifest(manifest, canonical_dir)
    mirror_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for asset in assets:
        source = canonical_dir / asset["filename"]
        target = mirror_dir / asset["filename"]
        shutil.copyfile(source, target)
        copied.append(target)
    shutil.copyfile(canonical_dir / "manifest.json", mirror_dir / "manifest.json")
    return copied


if __name__ == "__main__":
    synced = sync_assets()
    print(f"synced {len(synced)} PubChem Demo PNGs to {MIRROR_DIR}")
