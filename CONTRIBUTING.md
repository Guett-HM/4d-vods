# Contributing to 4D-VODS

4D-VODS is a concept study by a non-specialist. The most valuable contributions are
**corrections**: an assumption that is wrong, a formula that is too optimistic, a reference
that was missed. You do not need to send code for that; a short issue is enough.

## Ways to help

| You are… | Most useful contribution |
| --- | --- |
| An optics or laser-writing specialist | A [physics correction](https://github.com/GuettHM/4d-vods/issues/new?template=physics_correction.yml): what the model gets wrong and how much it matters |
| A coding-theory or 2D-code specialist | Review of the error-correction plan (TN-001 section 4.4) and of the SAMM layout |
| A developer | Bug reports, tests, faster code, the open items in `CHANGELOG.md` |
| Anyone | Questions about anything that is unclear: unclear text is a bug too |

## Ground rules for code changes

1. **Every number must stay reproducible.** Results are produced only by the scripts in
   `sim/`, run through `python -m vods run …`, which records the command, commit and
   software versions in `results/MANIFEST.json`. Never edit a file in `results/` by hand.
2. **Published numbers are registered.** If a change moves a number quoted in the README,
   the project page or the documents, update `results/claims.json` and the text, then run
   `python -m vods check`.
3. **Physics changes need a validation check or a test.** If you change the optics, add a
   comparison with an independent reference in `vods/validation.py` when one exists.
4. **Fixed seeds stay fixed.** If a change alters the fixed-seed reference values on
   purpose, regenerate them with `python tests/regression_cases.py` and explain why in
   `CHANGELOG.md`.
5. Before opening a pull request: `pytest -q` and `ruff check .` must pass.

## Set-up

```bash
git clone https://github.com/GuettHM/4d-vods && cd 4d-vods
pip install -e ".[dev]"          # or: pip install -r requirements-lock.txt
pytest -q                        # about 1 minute
python -m vods validate          # physics validation checks
python -m vods check             # published numbers vs results
```

## Licences

By contributing you agree that code is released under the MIT License and text and figures
under CC BY 4.0, like the rest of the project. Contributors are credited in `CHANGELOG.md`
and, for substantial contributions, in `CITATION.cff`.

Please follow the [code of conduct](CODE_OF_CONDUCT.md).
