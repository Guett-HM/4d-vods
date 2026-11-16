"""Validation of the physics model against independent references.

Each check compares the simulator with a result that does not come from the simulator:
a closed-form formula from diffraction theory, an independent library, or a symmetry the
physics must have. ``python -m vods validate --report`` writes docs/VALIDATION.md, and
tests/test_validation.py runs the same checks on every push.
"""
import datetime as _dt
import math

import numpy as np
from scipy.special import j1
from scipy.stats import binomtest

import samm_sim as S  # noqa: E402  (sim/ is put on sys.path by the package)
import vods_sim as V  # noqa: E402

from . import __version__, provenance


def _result(name, title, reference, measured, limit, passed, measured_text, limit_text):
    return {"name": name, "title": title, "reference": reference, "measured": float(measured),
            "limit": float(limit), "passed": bool(passed), "measured_text": measured_text,
            "limit_text": limit_text}


def coherent_psf_is_airy():
    """Data layer: amplitude image of a point = 2 J1(v)/v, v = 2 pi NA r / lambda."""
    opt = V.Optics(0.3, 6)
    c = opt.N // 2
    d = np.zeros((opt.N, opt.N), complex)
    d[c, c] = 1.0
    E = np.fft.ifft2(np.fft.fft2(d) * opt.pupil)
    prof = np.real(E[c, c:]) / np.real(E[c, c])
    r = np.arange(prof.size) * opt.dx
    v = 2 * np.pi * V.NA * r / V.LAM
    airy = np.ones_like(v)
    airy[1:] = 2 * j1(v[1:]) / v[1:]
    m = r < 3 * V.LAM / V.NA
    err = float(np.max(np.abs(prof[m] - airy[m])))
    lim = 0.02
    return _result("coherent_psf_is_airy", "Coherent point image matches the Airy amplitude 2J1(v)/v",
                   "closed-form diffraction of a circular pupil", err, lim, err <= lim,
                   f"max deviation {err:.4f} (field normalised to 1) over 3 λ/NA", f"≤ {lim}")


def coherent_first_zero():
    """First zero of the coherent point image at 0.610 lambda/NA."""
    opt = V.Optics(0.3, 6)
    c = opt.N // 2
    d = np.zeros((opt.N, opt.N), complex)
    d[c, c] = 1.0
    prof = np.real(np.fft.ifft2(np.fft.fft2(d) * opt.pupil)[c, c:])
    r = np.arange(prof.size) * opt.dx
    i = int(np.where(np.diff(np.sign(prof)) != 0)[0][0])
    z = r[i] + (r[i + 1] - r[i]) * prof[i] / (prof[i] - prof[i + 1])
    ref = 3.8317 / (2 * np.pi) * V.LAM / V.NA
    rel = abs(z - ref) / ref
    lim = 0.01
    return _result("coherent_first_zero", "First dark ring of the point image at 0.610 λ/NA",
                   "first zero of J1 (3.8317)", rel, lim, rel <= lim,
                   f"{z * 1000:.1f} nm vs {ref * 1000:.1f} nm (relative error {rel:.2%})", f"≤ {lim:.0%}")


def coherent_band_limit():
    """No spatial frequency above NA/lambda survives the data-layer optics."""
    opt = V.Optics(0.5, 3)
    rng = np.random.default_rng(0)
    obj = rng.standard_normal((opt.N, opt.N)) + 1j * rng.standard_normal((opt.N, opt.N))
    spec = np.abs(np.fft.fft2(np.fft.ifft2(np.fft.fft2(obj) * opt.pupil))) ** 2
    frac = float(spec[~opt.pupil].sum() / spec.sum())
    lim = 1e-20
    return _result("coherent_band_limit", "No energy above the cut-off frequency NA/λ",
                   "Abbe band limit of a circular pupil", frac, lim, frac <= lim,
                   f"fraction of energy beyond NA/λ: {frac:.1e}", f"≤ {lim:.0e}")


def energy_conservation():
    """Imaging a band-limited field keeps its energy; no field gains energy (Parseval)."""
    opt = V.Optics(0.5, 3)
    rng = np.random.default_rng(1)
    obj = rng.standard_normal((opt.N, opt.N)) + 1j * rng.standard_normal((opt.N, opt.N))
    img = np.fft.ifft2(np.fft.fft2(obj) * opt.pupil)
    again = np.fft.ifft2(np.fft.fft2(img) * opt.pupil)
    e_obj, e_img, e_again = (float(np.sum(np.abs(a) ** 2)) for a in (obj, img, again))
    dev = abs(e_again / e_img - 1)
    lim = 1e-10
    ok = dev <= lim and e_img <= e_obj
    return _result("energy_conservation", "Energy is conserved for band-limited fields and never created",
                   "Parseval's theorem", dev, lim, ok,
                   f"relative change {dev:.1e}; filtered/unfiltered energy {e_img / e_obj:.3f} ≤ 1", f"≤ {lim:.0e}")


def incoherent_mtf():
    """SAMM: the simulator's OTF equals the analytic MTF of a circular pupil."""
    na = 0.45
    rd = S.Reader(na, round(1.1 * S.LAM / na, 3))
    otf = np.real(rd.otf)
    f = np.fft.fftfreq(rd.nf, d=rd.dx)
    fc = 2 * na / S.LAM
    worst = 0.0
    for nu in (0.1, 0.25, 0.5, 0.75, 0.9):
        k = int(round(nu * fc / (f[1] - f[0])))
        x = f[k] / fc
        mtf = 2 / np.pi * (math.acos(x) - x * math.sqrt(1 - x * x))
        worst = max(worst, abs(otf[0, k] - mtf))
    lim = 0.005
    return _result("incoherent_mtf", "Incoherent transfer function matches the circular-pupil MTF",
                   "(2/π)[acos ν − ν√(1−ν²)]", worst, lim, worst <= lim,
                   f"max deviation {worst:.4f} at ν = 0.1–0.9 of the cut-off 2NA/λ", f"≤ {lim}")


def incoherent_band_limit():
    na = 0.45
    rd = S.Reader(na, round(1.1 * S.LAM / na, 3))
    f = np.fft.fftfreq(rd.nf, d=rd.dx)
    FX, FY = np.meshgrid(f, f)
    beyond = float(np.abs(rd.otf[np.hypot(FX, FY) > 1.02 * 2 * na / S.LAM]).max())
    lim = 1e-12
    return _result("incoherent_band_limit", "No contrast above the incoherent cut-off 2NA/λ",
                   "band limit of incoherent imaging", beyond, lim, beyond <= lim,
                   f"largest |OTF| beyond 2NA/λ: {beyond:.1e}", f"≤ {lim:.0e}")


def samm_scale_invariance():
    """A SAMM frame written at pitch k*lambda/NA gives the same camera image for any NA.
    This is what makes one code work for every reader class, and what allows a
    large printed frame photographed through a pinhole to stand in for a microscope."""
    rng = np.random.default_rng(3)
    levels = rng.integers(0, 4, (S.N, S.N))
    levels[S.ROLE == 1] = S.PILOT[S.ROLE == 1]
    imgs = []
    for na in (0.25, 0.65):
        rd = S.Reader(na, 1.1 * S.LAM / na)
        R = rd.render(levels, (0.4, 1.0, 0.0, 0.0), np.zeros((S.N, S.N)))
        imgs.append(rd.image(R, 1.0))
    m = min(i.shape[0] for i in imgs)
    crop = [i[(i.shape[0] - m) // 2:(i.shape[0] + m) // 2, (i.shape[1] - m) // 2:(i.shape[1] + m) // 2]
            for i in imgs]
    diff = float(np.abs(crop[0] - crop[1]).max())
    lim = 0.002
    return _result("samm_scale_invariance", "SAMM image depends only on pitch in units of λ/NA",
                   "scaling law of diffraction-limited imaging", diff, lim, diff <= lim,
                   f"largest pixel difference NA 0.25 vs 0.65: {diff:.5f} of full scale", f"≤ {lim}")


def mutual_information_estimator():
    """MI of a 16-ary symmetric channel with 10% errors: log2 M - h(e) - e log2(M-1)."""
    M, n, e = 16, 1500, 0.1
    xs, ys = [], []
    for s in range(M):
        xs += [s] * int(n * (1 - e))
        ys += [s] * int(n * (1 - e))
        for t in range(M):
            if t != s:
                xs += [s] * int(n * e / (M - 1))
                ys += [t] * int(n * e / (M - 1))
    mi = V.mutual_info(np.array(xs), np.array(ys), M)
    h = -e * math.log2(e) - (1 - e) * math.log2(1 - e)
    ref = math.log2(M) - h - e * math.log2(M - 1)
    dev = abs(mi - ref)
    lim = 1e-9
    return _result("mutual_information_estimator", "Mutual-information estimator is exact on a known channel",
                   "M-ary symmetric channel formula", dev, lim, dev <= lim,
                   f"{mi:.6f} vs {ref:.6f} bits", f"≤ {lim:.0e}")


def wilson_interval():
    """The confidence intervals agree with SciPy's independent implementation."""
    worst = 0.0
    for k, n in ((0, 10), (120, 120), (199, 200), (113, 200), (596, 600)):
        lo, hi = S.wilson(k, n)
        ci = binomtest(k, n).proportion_ci(method="wilson")
        worst = max(worst, abs(lo - ci.low), abs(hi - ci.high))
    lim = 1e-5
    return _result("wilson_interval", "95% Wilson intervals agree with SciPy",
                   "scipy.stats.binomtest(...).proportion_ci(method='wilson')", worst, lim, worst <= lim,
                   f"largest difference {worst:.1e}", f"≤ {lim:.0e}")


CHECKS = (coherent_psf_is_airy, coherent_first_zero, coherent_band_limit, energy_conservation,
          incoherent_mtf, incoherent_band_limit, samm_scale_invariance, mutual_information_estimator,
          wilson_interval)


def run_all():
    return [check() for check in CHECKS]


def write_report(results, path):
    env = provenance.environment()
    git = provenance.git_state()
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    n_ok = sum(r["passed"] for r in results)
    lines = [
        "# Validation report",
        "",
        f"4D-VODS {__version__} · generated {now} by `python -m vods validate --report` · "
        f"commit {git['commit']} · Python {env['python']}, NumPy {env['numpy']}, SciPy {env['scipy']}",
        "",
        f"**{n_ok} of {len(results)} checks pass.** Each check compares the simulator with a reference "
        "that does not come from the simulator: a closed-form result of diffraction theory, an "
        "independent library, or a scaling law the physics must obey. The same checks run as tests "
        "on every push (`tests/test_validation.py`).",
        "",
        "| Check | Reference | Measured | Limit | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in results:
        lines.append(f"| {r['title']} | {r['reference']} | {r['measured_text']} | {r['limit_text']} | "
                     f"{'pass' if r['passed'] else '**fail**'} |")
    lines += [
        "",
        "## What these checks do not cover",
        "",
        "They confirm that the code implements its stated model correctly. They do not test the "
        "model against reality: scalar optics, ideal symbol shapes, shot-noise-limited readout and "
        "the other assumptions listed in the white paper (section 16) remain assumptions until "
        "written glass is measured (tests T4–T8 of the technical note).",
        "",
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines))
