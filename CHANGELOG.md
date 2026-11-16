# Changelog

All notable changes to this project are listed here. Versions follow
[Semantic Versioning](https://semver.org/).

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
