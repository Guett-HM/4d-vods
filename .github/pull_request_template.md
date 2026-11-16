## What this changes

## Checklist

- [ ] `pytest -q` passes and `ruff check .` is clean
- [ ] If results changed: rerun with `python -m vods run ...` (provenance is recorded automatically) and explain why in `CHANGELOG.md`
- [ ] If a published number changed: update `results/claims.json` and the documents, then `python -m vods check`
- [ ] If the fixed-seed reference changed on purpose: `python tests/regression_cases.py` and say why
