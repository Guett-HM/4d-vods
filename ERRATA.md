# Errata

Corrections to published versions. Each entry says what was wrong, what is correct, and
whether any result changes. The archived versions on Zenodo are left as they were; the
corrections apply from the version named in the heading.

## Corrections to v1.0.0, made in v1.1.0

### E1. The APSK-16 dot is square, not round

**Was:** the README, the project page and the White Paper described the APSK-16 symbol
as a "round" or "isotropic" dot.
**Correct:** the simulator writes a **square dot of side 0.6 p** (180 nm at 300 nm pitch;
`sim/vods_sim.py`, `build_templates`). The illustration `fig0` already showed squares.
At this size the square is below the optical resolution (about 225 nm), so the readout
cannot tell it from a round dot of the same area.
**Results:** unchanged; only the wording was wrong.

### E2. "1.9× a Blu-ray layer" compared two different quantities

**Was:** APSK-16 at 300 nm (42.6 bits/µm²) was called "1.9 times a Blu-ray layer"
(22.8 bits/µm²).
**Correct:** 42.6 bits/µm² is the information recoverable **before error correction**, with
pilots counted as data and a laboratory interferometric reader. 22.8 bits/µm² is the
**net user data** of a 25 GB Blu-ray layer after modulation, error correction and
formatting. The fair optical reference is also BDXL, which reaches 33.4 GB per layer with
the same 405 nm / NA 0.85 optics, i.e. about **30.5 bits/µm² of net user data**.
An indicative net figure for APSK-16 is 42.6 × 15/16 (pilots) × 0.88 (error-correction rate
of E3) ≈ **35 bits/µm², about 1.15× BDXL**. This is an estimate until test T2 (error-correction
budget) is run.
**Results:** the raw figure (42.6) is unchanged; all comparisons now state "before error
correction" and quote BDXL as well as Blu-ray. Figure 1 shows both reference lines.

### E3. The error-correction target in TN-001 did not meet its own overhead limit

**Was:** TN-001 section 4.4 proposed an inner LDPC code of rate 0.9 with an outer
Reed-Solomon RS(255, 223) code, while test T2 requires at most 15% overhead.
**Correct:** 0.9 × 223/255 = 0.787, i.e. **21% parity**, which fails T2. The target becomes
an inner LDPC code of rate ≈ 0.94 with an outer RS(255, 239) code interleaved across frames:
0.94 × 239/255 ≈ 0.881, i.e. **about 12% parity**. Whether this meets the residual-error
target is exactly what T2 must show. T2 also states how it will be shown: post-correction
error rates of 10⁻¹⁵ cannot be reached by simulation, so the LDPC stage is simulated down to
about 10⁻⁶ and the Reed-Solomon stage is computed analytically.
**Results:** none (error correction is not simulated yet).

### E4. The physical medium of each layer was not stated

**Was:** both layers were described as "engraved into glass" without saying how they
produce contrast.
**Correct, as declared from v1.1.0:**
- **SAMM layer:** a thin absorbing film (metal, nitride or ceramic) on the glass surface,
  removed by laser ablation. Grey levels are set by the fraction of each cell that is
  ablated, in features smaller than the reader resolves. This gives the amplitude contrast
  that a bright-field camera needs; a modification inside bulk glass mostly changes phase
  and would be nearly invisible to such a camera. The film must be protected (durable
  material or bonded cover glass): an open design choice.
- **High-density layer:** the simulator models a **reflective surface relief** (phase
  4πh/λ, floor reflectance 1.0 or 0.5), i.e. a metallised relief sealed under a cover layer,
  as in a pressed optical disc. Under a cover of refractive index n the same phases need
  depths divided by n (40 and 90 nm become 27 and 62 nm for n = 1.46); the results are
  unchanged. A version written inside bulk glass is **not** covered by these results: eight
  phase levels need a voxel 10–38 µm long for a refractive-index change of 0.02–0.005
  (read in reflection; twice that in transmission), against a depth of focus of 0.5 µm, which is not feasible at 300 nm pitch.
**Results:** unchanged for the declared media; the bulk-glass variant is withdrawn as a
claim and listed as an open question.

### E5. SAMM reader classes: wavelength and "USB microscope"

**Was:** NA 0.25 was labelled "USB / phone-clip microscope", and the SAMM pitches in µm
assumed 405 nm illumination.
**Correct:** NA 0.25 corresponds to an entry-level 10× objective; many low-cost USB
microscopes have a lower NA. SAMM results are exact in units of λ/NA (validated in
`docs/VALIDATION.md`), so they hold for any reader; only the conversion to µm and
bits/µm² depends on the wavelength. With white-LED light (about 550 nm) the pitch at NA 0.25
is 2.42 µm instead of 1.78 µm, and densities scale by (405/550)² ≈ 0.54.
**Results:** alignment and error rates unchanged; tables now name the reader by NA and
state the wavelength.

## Limits found after v1.1.0 (not yet in a release)

These were found on 17 November 2026 while preparing the successor project
[CUNEUS](https://github.com/Guett-HM/cuneus) (doi:10.5281/zenodo.24325753). The files in
`results/` are not regenerated; the entries say which published numbers they affect.

### E6. Results at 250 nm and below are slightly flattered by the small simulated grid

**Was:** data-layer results come from 7 × 7 grids of symbols with only the central 3 × 3
scored (White Paper section 8). At 250 nm the practical decoder gives 35.3 bits/µm².
**Correct:** outside the 7 × 7 grid there are no symbols, so the scored symbols see less
interference than they would inside a full lattice. Running the same decoder on larger grids
gives 33.0 bits/µm² on 15 × 15 grids and 34.1 bits/µm² on 19 × 19 grids at 250 nm, about
3–7% lower. At 300 nm the published value holds: 42.2 and 42.8 bits/µm² against 42.6.
**Results:** the headline (APSK-16 at 300 nm, 42.6 bits/µm²) and the ranking of the
alphabets are unchanged; the APSK-16 values below 300 nm in Figure 1 and the results tables
are slightly optimistic. CUNEUS simulates a periodic lattice with no edges and replaces them.

### E7. Defocus was not modelled; the SAMM reader needs a focus sweep

**Was:** the SAMM results (199–200 of 200 frames aligned) assume a reader exactly in focus;
defocus was listed as not modelled.
**Correct:** with the same SAMM-24 frames at NA 0.45 (depth of focus λ/NA² = 2.0 µm at
405 nm), exact non-paraxial defocus and a decoder unaware of it, 40 randomly rotated frames
per point: at pitch 1.1 × λ/NA, 40/40 frames align at half a depth of focus (symbol error
0.14%), 34/40 at one depth of focus (14.8%) and 3/40 at 1.5. At pitch 1.4 × λ/NA, 39/40
align at one depth of focus (1.3%).
**Results:** the in-focus results are unchanged. A reader without a focus stage must take a
short focus sweep (images about half a depth of focus apart) and decode the sharpest, or use
a pitch about 27% larger; the low-cost tier of CUNEUS includes both.
