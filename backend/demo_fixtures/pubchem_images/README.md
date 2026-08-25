# PubChem Demo Structure Images

This directory is the canonical, bundled source for the five Proposal Demo structure images.

Source and reuse notice: images are retrieved from PubChem (National Center for Biotechnology Information, U.S. National Library of Medicine) using the PUG image endpoint. PubChem is the source and should be credited in downstream distributions. This repository does not assert that every PubChem record or image is uniformly licensed for every reuse; downstream users must review the applicable PubChem terms, record-specific provenance, and any third-party rights before redistribution.

The images are illustrative Demo assets only and do not constitute experimental evidence, safety instructions, or an endorsement by PubChem.

Assets:

- CID 18616 — copper dinitrate
- CID 11138 — benzene-1,3,5-tricarboxylic acid
- CID 3776 — methanol
- CID 280 — carbon dioxide
- CID 947 — nitrogen

`manifest.json` records the official PubChem PUG image URL, retrieval date, content type, byte count, and SHA-256 for every PNG. The frontend mirror under `frontend/public/demo_fixtures/pubchem_images/` is disposable and must be regenerated with the local sync script; it is not a second source of truth.

The Proposal Demo uses these local files and must not request PubChem or the backend chemical/PubChem routes. Real mode retains its existing backend path.

## Refreshing the local fixture (explicit, read-only source)

The one-time source retrieval used the fixed allowlist and URL template below. A refresh must be deliberate, validate PNG content and MIME type, and update the manifest hashes only after inspection:

```text
https://pubchem.ncbi.nlm.nih.gov/image/imgsrv.fcgi?cid={cid}&t=l
```

Public-release packaging still requires a separate attribution/legal review; this local demo fixture does not claim that review is complete.

## Local mirror

```bash
python scripts/sync_demo_pubchem_images.py
```
