# Changelog

All notable changes to this project are listed here. Versions follow
[Semantic Versioning](https://semver.org/).

## Unreleased

### Moved
- Repository moved to https://github.com/Guett-HM/4d-vods after the former account (GuettHM) was
  closed; project page now at https://guett-hm.github.io/4d-vods/. Links updated everywhere except
  inside the two PDF documents, which keep the former address. The Zenodo DOIs are unchanged.
- The history before the v1.0.0 commit could not be carried over, and release tags were not
  carried over; versions 1.0.0 and 1.1.0 are archived on Zenodo (doi:10.5281/zenodo.24268722 and
  doi:10.5281/zenodo.24275029). Version 1.0.0 is commit ba90ccc; version 1.1.0 was released after
  commit 4e2f128, the last commit before its DOI was added.

### Documented (details in ERRATA.md)
- E6: data-layer results at 250 nm and below are 3–7% optimistic because of the 7 × 7 grid;
  the 300 nm headline (42.6 bits/µm²) holds on 15 × 15 and 19 × 19 grids.
- E7: SAMM with defocus: half a depth of focus at pitch 1.1 × λ/NA, one depth of focus at
  1.4 × λ/NA; a reader without a focus stage needs a focus sweep.
- README and project page point to the successor project CUNEUS.

## [1.1.0] – consolidation

No new physics: every result of 1.0.0 is unchanged. This release corrects the text, makes
every number traceable, and checks the simulator against independent references.

### Fixed (details in ERRATA.md)
- E1: the APSK-16 dot is a 0.6 p square, not a round dot (wording only).
- E2: densities are now labelled "before error correction"; the comparison uses the net
  user data of Blu-ray (22.8 bits/µm²) and BDXL (30.5 bits/µm²), with an indicative net
  figure for APSK-16 of about 35 bits/µm² (≈ 1.15× BDXL) instead of "1.9× Blu-ray".
- E3: TN-001 error-correction target changed to LDPC ≈ 0.94 + RS(255, 239), about 12%
  parity, consistent with the 15% limit of test T2 (was 21%).
- E4: the physical medium of each layer is declared (SAMM: ablated absorbing film;
  data layer: metallised relief under a cover layer); the bulk-glass variant of the data
  layer is withdrawn as a claim.
- E5: SAMM reader at NA 0.25 renamed "entry-level 10× objective"; pitches and densities
  are stated at 405 nm, with the scaling to other wavelengths.

### Added
- `python -m vods`: one command line for all studies, with TOML configurations in `configs/`.
- `results/MANIFEST.json`: provenance of every result (hash, command, parameters, commit,
  software versions), checked by the tests.
- `results/claims.json` and `python -m vods check`: every published number is traced to a
  result field and checked against the README, the project page and the documents.
- `vods/validation.py` and `docs/VALIDATION.md`: nine checks against closed-form diffraction
  theory and independent libraries (Airy pattern, MTF, Parseval, band limits, SAMM scale
  invariance, mutual information, Wilson intervals).
- Tests grow from 10 to about 50: validation, fixed-seed regression, properties (SAMM at
  0/90/180/270° and mirrored, monotonic error growth), provenance and published numbers.
- Figures in one shared style (`sim/plotstyle.py`), as PNG and vector PDF, with the plotted
  values as CSV in `figures/data/`; 95% confidence bands on the SAMM alignment figure;
  BDXL reference line in figure 1.
- Markdown sources of both documents in `docs/src/`.
- `pyproject.toml`, `requirements-lock.txt` (exact reference versions), continuous
  integration on Python 3.11–3.13 with style checks (ruff) and coverage.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue forms (physics correction, bug) and a
  pull-request checklist.

### Changed
- White Paper v1.1 and Technical Note TN-001 rev. 1.1 carry the corrections above.
- `TRIALS` now sets the number of trials of every data-layer experiment (default unchanged).

## [1.0.0] – first public release

### Added
- `sim/vods_sim.py`: data-layer simulator (Voxel-Wedge and APSK-16 alphabets,
  pitch sweep, ideal and practical decoders, rotation test, Gray coding,
  on-media compression test, writing-variability sensitivity, seed spread).
- `sim/samm_sim.py`: Self-Aligning Micro-Matrix (SAMM) simulator for low-cost
  bright-field readers, with sensitivity analysis and 95% confidence intervals.
- `sim/make_figures.py`, `sim/make_illustrations.py`: all figures.
- `tests/`: fast sanity tests, run by GitHub Actions on every push.
- `docs/`: White Paper v1.0 and Technical Note TN-001 (PDF).
- `results/`: raw JSON results behind every number in the documents.
- `index.html`: project page with an interactive SAMM frame, ready for GitHub Pages.
