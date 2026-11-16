# 4D-VODS

**Optical data storage in glass with a self-aligning code for low-cost readers – an open simulation study**

Hakim Guettal · v1.0.0 · Code: MIT · Documents and figures: CC BY 4.0

*I am not a professional physicist. 4D-VODS started as a geometric intuition (storing data in the shape of engraved symbols) and grew into this conceptual study and simulator, built with the help of AI tools on standard diffraction optics. Corrections from specialists are very welcome.*

4D-VODS is a concept for archival data storage in glass with two layers written by the
same femtosecond laser:

- a **high-density data layer** of multi-level dots, read by a laboratory interferometric microscope;
- a **Self-Aligning Micro-Matrix (SAMM)** code that an ordinary microscope camera can find,
  orient and decode at any rotation, with no positioning stage.

A project page is in `index.html`: open it in a browser, or publish it with GitHub Pages
(Settings, Pages, deploy from the main branch).

This repository contains the simulator, the raw results behind every number, and the two
documents ([White Paper v1.0](docs/4D-VODS_White_Paper_v1.0.pdf) and
[Technical Note TN-001](docs/4D-VODS_Technical_Note_TN-001.pdf)).

> **Status: concept, simulation only (TRL 2).** No physical sample has been written or read.
> The results compare design options under the same modelled physics; they are not
> performance claims for a device.

![What the symbols look like before and after the optics](figures/fig0_symbols.png)

## Key results

**Data layer** (405 nm, NA 0.90, interferometric readout, 10% writing variability, practical decoder):

| Alphabet | Best pitch | Information density | ≈ Capacity per 12 cm disc layer |
| --- | --- | --- | --- |
| Naive estimate: 8-bit Voxel-Wedge at 150 nm | 150 nm | 356 bits/µm² (not achievable) | 390 GB |
| **APSK-16 isotropic dots (4 bits)** | 300 nm | **42.6 bits/µm²** (± 0.07) | 47 GB |
| Voxel-Wedge (8 bits) | 500 nm | 26.8 bits/µm² (± 0.15) | 29 GB |
| Blu-ray, reference | – | 22.8 bits/µm² | 25 GB |

± = standard deviation over 5 further independent random seeds (`results/spread.json`). The ranking holds at 5%, 10% and 20%
writing variability (`figures/fig7_sensitivity.png`).

**SAMM layer** (bright-field intensity camera, 405 nm, random rotation 0–360°, scale ±3%,
illumination tilt ±20%, pitch 1.1 × λ/NA, 200 frames per reader class):

| Reader class | NA | Pitch | Frames aligned (95% CI) | Symbol error | Net density |
| --- | --- | --- | --- | --- | --- |
| USB / phone-clip microscope | 0.25 | 1.78 µm | 200/200 (98.1–100%) | 0.02% | 0.55 bits/µm² (≈ 7 MB/cm²) |
| Budget 20× objective | 0.45 | 0.99 µm | 199/200 (97.2–99.9%) | 0.25% | 1.77 bits/µm² (≈ 22 MB/cm²) |
| Budget 40× objective | 0.65 | 0.69 µm | 200/200 (98.1–100%) | 0.02% | 3.75 bits/µm² (≈ 47 MB/cm²) |

![One SAMM frame: written, photographed, decoded](figures/fig6_samm_pipeline.png)

Other findings:

- Shape-encoded bits (azimuth, curvature) disappear first as the pitch shrinks; phase and
  reflectance survive down to 300 nm (`fig2`).
- Pilot symbols handle rotation with about 3× fewer errors than differential angle coding (`fig3`).
- Software compression before writing beats on-media run-length glyphs 4–6× on real data (`fig4`).

## Quick start

```bash
pip install -r requirements.txt
pytest -q tests                        # 10 sanity tests, ~10 s

QUICK=1 python3 sim/vods_sim.py        # smoke run -> results_quick/
QUICK=1 python3 sim/samm_sim.py

python3 sim/vods_sim.py                # full data-layer study  (~30 min, 2 cores)
python3 sim/samm_sim.py                # full SAMM study        (~30 min)
SENS=1 python3 sim/samm_sim.py         # SAMM sensitivity
python3 sim/make_figures.py            # figures/fig1-fig7 + results/summary.json
python3 sim/make_illustrations.py      # figures/fig0, fig6
```

Random seeds are fixed, so a full run reproduces the published results.

## Repository layout

| Path | Contents |
| --- | --- |
| `sim/vods_sim.py` | Data-layer simulator: Voxel-Wedge vs APSK-16, ideal and practical decoders, rotation, Gray coding, compression, sensitivity |
| `sim/samm_sim.py` | SAMM simulator: finder detection, alignment, decoding, confidence intervals, sensitivity |
| `sim/make_figures.py`, `sim/make_illustrations.py` | All figures |
| `results/` | Raw JSON results behind every number in the documents |
| `figures/` | Figures used in the README and documents |
| `docs/` | White Paper v1.0 and Technical Note TN-001 (PDF) |
| `tests/` | Sanity tests (run by GitHub Actions on every push) |
| `HISTORY.md` | How the design evolved from the first hand-drawn glyphs |

## What is modelled, and what is not

Modelled: scalar Fourier optics at the diffraction limit (coherent for the data layer,
incoherent for SAMM), shot and sensor noise, writing variability, inter-symbol interference,
random rotation, scale and illumination errors, practical decoders.

Not modelled: real laser–glass interaction and shape fidelity, vectorial optics at high NA,
defocus and tilt, multilayer cross-talk, error-correction codes, speed and cost.
See section 16 of the white paper.

## Related work

Microsoft Project Silica (Nature, 2026), 5D optical storage (University of Southampton),
Cerabyte ceramic storage, holographic storage, and 2D codes such as QR, Data Matrix and
Aztec. 4D-VODS builds on these ideas; its contribution is an open, reproducible comparison
and a low-cost, self-aligning reading layer. See section 5 of the white paper.

## How to cite

Use the "Cite this repository" button on GitHub (from `CITATION.cff`) or the Zenodo DOI
shown on the release page.

> Guettal, H. (2026). *4D-VODS: optical data storage in glass with a self-aligning code for low-cost readers* (v1.0.0). Zenodo.

## Use of AI tools

AI assistants helped write the simulator and documents (see the note at the top). Every
result comes from the code in this repository and can be checked by re-running it.

## Feedback

Issues and pull requests are welcome, especially from people with experience in
femtosecond laser writing, optical metrology or 2D-code reading.
