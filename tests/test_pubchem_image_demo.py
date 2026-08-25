import hashlib
import json
from pathlib import Path

import pytest

from scripts.sync_demo_pubchem_images import EXPECTED_CIDS, sync_assets, validate_manifest, validate_png_response

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "backend" / "demo_fixtures" / "pubchem_images"


@pytest.mark.unit
def test_manifest_contains_exact_allowlist_and_valid_png_hashes():
    manifest = json.loads((CANONICAL / "manifest.json").read_text(encoding="utf-8"))
    assets = validate_manifest(manifest, CANONICAL)
    assert tuple(asset["cid"] for asset in assets) == EXPECTED_CIDS
    assert all(asset["content_type"] == "image/png" for asset in assets)
    assert all(hashlib.sha256((CANONICAL / asset["filename"]).read_bytes()).hexdigest() == asset["sha256"] for asset in assets)


@pytest.mark.unit
def test_validation_rejects_html_and_wrong_content_type():
    with pytest.raises(ValueError, match="not a PNG"):
        validate_png_response(b"<html>error</html>", "text/html")
    with pytest.raises(ValueError, match="content type"):
        validate_png_response(b"\x89PNG\r\n\x1a\nbody", "application/octet-stream")


@pytest.mark.unit
def test_sync_copies_only_manifest_allowlist(tmp_path):
    mirror = tmp_path / "mirror"
    copied = sync_assets(CANONICAL, mirror)
    assert [path.name for path in copied] == [f"cid-{cid}.png" for cid in EXPECTED_CIDS]
    assert (mirror / "manifest.json").read_bytes() == (CANONICAL / "manifest.json").read_bytes()
    for cid in EXPECTED_CIDS:
        assert (mirror / f"cid-{cid}.png").read_bytes() == (CANONICAL / f"cid-{cid}.png").read_bytes()
