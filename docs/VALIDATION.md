# Validation report

4D-VODS 1.1.0 · generated 2026-11-16 by `python -m vods validate --report` · commit ffba8b3 · Python 3.13.18, NumPy 2.5.3, SciPy 1.18.1

**9 of 9 checks pass.** Each check compares the simulator with a reference that does not come from the simulator: a closed-form result of diffraction theory, an independent library, or a scaling law the physics must obey. The same checks run as tests on every push (`tests/test_validation.py`).

| Check | Reference | Measured | Limit | Result |
| --- | --- | --- | --- | --- |
| Coherent point image matches the Airy amplitude 2J1(v)/v | closed-form diffraction of a circular pupil | max deviation 0.0095 (field normalised to 1) over 3 λ/NA | ≤ 0.02 | pass |
| First dark ring of the point image at 0.610 λ/NA | first zero of J1 (3.8317) | 273.8 nm vs 274.4 nm (relative error 0.24%) | ≤ 1% | pass |
| No energy above the cut-off frequency NA/λ | Abbe band limit of a circular pupil | fraction of energy beyond NA/λ: 1.6e-31 | ≤ 1e-20 | pass |
| Energy is conserved for band-limited fields and never created | Parseval's theorem | relative change 6.7e-16; filtered/unfiltered energy 0.007 ≤ 1 | ≤ 1e-10 | pass |
| Incoherent transfer function matches the circular-pupil MTF | (2/π)[acos ν − ν√(1−ν²)] | max deviation 0.0008 at ν = 0.1–0.9 of the cut-off 2NA/λ | ≤ 0.005 | pass |
| No contrast above the incoherent cut-off 2NA/λ | band limit of incoherent imaging | largest |OTF| beyond 2NA/λ: 2.2e-16 | ≤ 1e-12 | pass |
| SAMM image depends only on pitch in units of λ/NA | scaling law of diffraction-limited imaging | largest pixel difference NA 0.25 vs 0.65: 0.00065 of full scale | ≤ 0.002 | pass |
| Mutual-information estimator is exact on a known channel | M-ary symmetric channel formula | 3.140315 vs 3.140315 bits | ≤ 1e-09 | pass |
| 95% Wilson intervals agree with SciPy | scipy.stats.binomtest(...).proportion_ci(method='wilson') | largest difference 7.4e-06 | ≤ 1e-05 | pass |

## What these checks do not cover

They confirm that the code implements its stated model correctly. They do not test the model against reality: scalar optics, ideal symbol shapes, shot-noise-limited readout and the other assumptions listed in the white paper (section 16) remain assumptions until written glass is measured (tests T4–T8 of the technical note).
