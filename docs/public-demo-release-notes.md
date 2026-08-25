# Public Demo Release Notes

This repository is a fresh-history public release of the MOF-AI-Chemist offline Demo tree. The previous public repository history was not rewritten or copied into this repository.

## What was verified

- The repository security preflight passed on the staged release snapshot.
- Targeted Demo, PubChem fixture, safety-image TLS, XRD fixture, and PORMAKE skip tests passed: 19 passed, 3 skipped because the optional local PORMAKE engine environment is not installed.
- Frontend lint passed.
- Frontend production build passed with existing bundle-size and dependency `eval` warnings.
- No real provider key, private key, personal absolute path, ignored runtime data, or local Agent handoff file is included in the release snapshot.
- PubChem and PORMAKE provenance notices are included in `THIRD_PARTY_NOTICES.md` and the asset-local notices.

## Known limitations

- The full safe-loop currently reports 297 passed, 26 failed, 15 skipped, and 25 deselected in the repository virtual environment. The failures are existing dirty-branch/demo-default/path-drift/XRD-route issues outside this sanitization release gate; they are not represented as a green full-suite claim here.
- The optional PORMAKE engine-real tests are collected as `external`/`slow` and skip when the local PORMAKE tool environment is absent.
- The repository's existing pre-commit quality hooks are not green across the legacy tree: Black and isort would reformat many Python files, flake8 reports existing lint findings, mypy reports a duplicate `services` module mapping, and the large-file hook rejects several intentionally bundled XRD Demo fixtures. These hooks were explicitly skipped for this sanitization-only release; the security-preflight hook still ran and passed.
- No GitHub Actions workflow is configured in this initial public snapshot. Code-quality CI should be added as a separate, bounded follow-up after the legacy tree and large-fixture policy are addressed.
- PubChem record and asset reuse remains subject to downstream provenance, terms, and legal review. The repository makes no unconditional third-party licensing claim.

## Scope disclaimer

Demo scientific text, prediction values, CIFs, and XRD patterns are illustrative, synthetic, and non-experimental. They are not validated synthesis procedures, calibrated model results, measured data, safety instructions, or a basis for laboratory, engineering, regulatory, or health decisions.
