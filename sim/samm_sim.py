"""
SAMM -- Self-Aligning Micro-Matrix: a 2D optical code for low-cost readers
==========================================================================

Simulates the low-cost reading layer of 4D-VODS: a square frame of N x N cells
read by an ordinary bright-field microscope camera (intensity only, no
interferometer, no precision stage). The reader does NOT know the frame's
rotation, position or exact scale: it must find and align the frame by itself.

Frame layout (N = 24 by default)
  * 4 corner finders: 3x3-cell "bullseye" (dark centre dot + dark ring on the
    bright substrate). A bullseye looks the same at every rotation, so it can
    be found with one correlation, without searching over angles.
  * Pilot cells: every cell with row % 4 == 2 and col % 4 == 2 (1 in 16)
    carries a known, pseudo-random level. Pilots resolve the 4-fold
    (and mirror) ambiguity left by four identical corners, calibrate the
    grey levels and the illumination gradient.
  * Data cells: everything else; M = 4 reflectance levels (2 bits, Gray coded).

Optics / sensor (low-cost reader)
  * LED or laser-diode illumination, incoherent imaging, wavelength 405 nm.
  * NA in {0.25 (USB / phone-clip microscope), 0.45 (20x budget objective),
    0.65 (40x budget objective)}.
  * Camera pixel = lambda / (4 NA) in object space (Nyquist for the incoherent
    cut-off), additive noise 2% of full scale.
  * Unknown rotation U[0, 360), scale 1 +- 3%, random position,
    linear illumination gradient up to +-20%, writing jitter 0.03 in reflectance.

Decoder
  1. normalised correlation with the (rotation-invariant) bullseye template
  2. keep up to 5 groups of 4 peaks that form a square
  3. for each group, 8 hypotheses (4 rotations x mirror) -> affine fit from the
     4 corners; keep the one whose pilot cells best match the known pattern
  4. fit illumination plane + grey-level means on pilots
  5. classify data cells, with 2 rounds of neighbour-interference cancellation

Usage:
  python3 samm_sim.py              -> results/samm.json (~10 min, 2 cores with NAS split)
  SENS=1 python3 samm_sim.py       -> results/samm_sensitivity.json
  QUICK=1 python3 samm_sim.py      -> smoke run, results_quick/ (8 frames per point)
"""
import json
import math
import os
import time
from itertools import combinations

import numpy as np
from scipy import ndimage

LAM = 0.405
N = 24
LEVELS = np.array([1.0, 0.7, 0.4, 0.1])     # intensity reflectance, level 0 = unwritten
NOISE = 0.02
JITTER = 0.03
F = 4                                        # fine pixels per camera pixel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results_quick" if os.environ.get("QUICK") == "1" else "results")


def layout(n=N, seed=123):
    """Cell roles: 0 data, 1 pilot, 2 finder. Pilot levels are fixed (known)."""
    role = np.zeros((n, n), int)
    for (r0, c0) in [(0, 0), (0, n - 3), (n - 3, 0), (n - 3, n - 3)]:
        role[r0:r0 + 3, c0:c0 + 3] = 2
    rr, cc = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    role[(rr % 4 == 2) & (cc % 4 == 2) & (role == 0)] = 1
    rng = np.random.default_rng(seed)
    pilot_lvl = rng.integers(0, 4, (n, n))
    return role, pilot_lvl


ROLE, PILOT = layout()
FINDER_CENTRES = np.array([[1.5, 1.5], [1.5, N - 1.5], [N - 1.5, N - 1.5], [N - 1.5, 1.5]])  # (row, col) in cells


class Reader:
    def __init__(self, na, p):
        self.na, self.p = na, p
        self.pix = LAM / (4 * na)
        self.dx = self.pix / F
        side = 1.42 * N * p * 1.03 + 2 * 1.5 * LAM / na + 2.0
        nc = int(math.ceil(side / self.pix))
        nc += nc % 2
        self.nc, self.nf = nc, nc * F
        x = (np.arange(self.nf) - (self.nf - 1) / 2) * self.dx
        self.X, self.Y = np.meshgrid(x, x)
        f = np.fft.fftfreq(self.nf, d=self.dx)
        FX, FY = np.meshgrid(f, f)
        pupil = ((FX ** 2 + FY ** 2) <= (na / LAM) ** 2).astype(float)
        psf = np.abs(np.fft.ifft2(pupil)) ** 2
        self.otf = np.fft.fft2(psf / psf.sum())
        self.template = self._finder_template()

    # ---------- geometry --------------------------------------------------
    def to_world(self, rc, T):
        """frame coords (row, col in cells) -> world (x, y) in um"""
        th, s, tx, ty = T
        u = (rc[..., 1] - N / 2) * self.p * s
        v = (rc[..., 0] - N / 2) * self.p * s
        c, sn = math.cos(th), math.sin(th)
        return np.stack([tx + c * u - sn * v, ty + sn * u + c * v], -1)

    def world_to_pix(self, xy):
        """world (x, y) -> camera (row, col) index coordinates"""
        k = lambda X: (X / self.dx + (self.nf - 1) / 2 - (F - 1) / 2) / F
        return np.stack([k(xy[..., 1]), k(xy[..., 0])], -1)

    # ---------- rendering -------------------------------------------------
    def render(self, levels, T, jitter):
        th, s, tx, ty = T
        c, sn = math.cos(th), math.sin(th)
        Xr, Yr = self.X - tx, self.Y - ty
        u = (c * Xr + sn * Yr) / (s * self.p) + N / 2       # col in cells
        v = (-sn * Xr + c * Yr) / (s * self.p) + N / 2      # row in cells
        j, i = np.floor(u).astype(int), np.floor(v).astype(int)
        inside = (i >= 0) & (i < N) & (j >= 0) & (j < N)
        ic, jc = np.clip(i, 0, N - 1), np.clip(j, 0, N - 1)
        lu, lv = u - j - 0.5, v - i - 0.5
        R = np.ones_like(self.X)
        refl = LEVELS[levels] + jitter
        dot = inside & (np.abs(lu) < 0.4) & (np.abs(lv) < 0.4) & (ROLE[ic, jc] != 2)
        R = np.where(dot, refl[ic, jc], R)
        # finders: bullseye centred in each 3x3 corner block
        for (fr, fc) in FINDER_CENTRES:
            r = np.hypot(u - fc, v - fr)
            ring = ((r < 0.45) | ((r > 0.95) & (r < 1.4)))
            R = np.where(ring & (np.abs(u - fc) < 1.5) & (np.abs(v - fr) < 1.5), LEVELS[3], R)
        return R

    def image(self, R, gain):
        I = np.real(np.fft.ifft2(np.fft.fft2(R) * self.otf))
        cam = I.reshape(self.nc, F, self.nc, F).mean(axis=(1, 3))
        return cam * gain

    def _finder_template(self):
        T = (0.0, 1.0, 0.0, 0.0)
        # isolated bullseye on bright background, centred at the origin
        u = self.X / self.p + 1.5
        v = self.Y / self.p + 1.5
        r = np.hypot(u - 1.5, v - 1.5)
        R = np.where(((r < 0.45) | ((r > 0.95) & (r < 1.4))) & (np.abs(u - 1.5) < 1.5)
                     & (np.abs(v - 1.5) < 1.5), LEVELS[3], 1.0)
        img = self.image(R, 1.0)
        c = self.nc // 2
        h = int(math.ceil(2.2 * self.p / self.pix)) + 2
        t = 1.0 - img[c - h:c + h, c - h:c + h]
        t -= t.mean()
        return t / np.linalg.norm(t)

    # ---------- decoding --------------------------------------------------
    def find_corners(self, img):
        # flatten the illumination tilt before looking for finders
        bg = ndimage.gaussian_filter(img, sigma=4 * self.p / self.pix)
        flat = img / np.maximum(bg, 1e-3)
        a = 1.0 - flat / np.percentile(flat, 99)
        t = self.template
        k = np.ones_like(t)
        num = ndimage.correlate(a, t, mode="constant")
        mean = ndimage.correlate(a, k, mode="constant") / k.size
        var = ndimage.correlate(a * a, k, mode="constant") - k.size * mean ** 2
        ncc = num / np.sqrt(np.maximum(var, 1e-9))
        sep = max(3, int(0.3 * N * self.p / self.pix))
        peaks = (ncc == ndimage.maximum_filter(ncc, size=sep)) & (ncc > 0.3)
        rr, cc = np.nonzero(peaks)
        order = np.argsort(-ncc[rr, cc])[:20]
        pts = []
        for r0, c0 in zip(rr[order], cc[order]):
            if 0 < r0 < ncc.shape[0] - 1 and 0 < c0 < ncc.shape[1] - 1:
                dr = 0.5 * (ncc[r0 - 1, c0] - ncc[r0 + 1, c0]) / (ncc[r0 - 1, c0] - 2 * ncc[r0, c0] + ncc[r0 + 1, c0] + 1e-12)
                dc = 0.5 * (ncc[r0, c0 - 1] - ncc[r0, c0 + 1]) / (ncc[r0, c0 - 1] - 2 * ncc[r0, c0] + ncc[r0, c0 + 1] + 1e-12)
                pts.append((r0 + np.clip(dr, -1, 1), c0 + np.clip(dc, -1, 1), ncc[r0, c0]))
        side = (N - 3) * self.p / self.pix
        cands = []
        for q in combinations(pts, 4):
            P = np.array([[a_[0], a_[1]] for a_ in q])
            cen = P.mean(0)
            ang = np.arctan2(P[:, 0] - cen[0], P[:, 1] - cen[1])
            P = P[np.argsort(ang)]
            d = np.linalg.norm(P - np.roll(P, -1, 0), axis=1)
            diag = np.linalg.norm(P[:2] - P[2:], axis=1)
            err = np.std(d) / side + abs(d.mean() / side - 1) + abs(diag.mean() / (side * math.sqrt(2)) - 1)
            cands.append((err, P))
        cands = sorted([c for c in cands if c[0] < 0.25], key=lambda c: c[0])[:5]
        return [P for _, P in cands]

    def decode(self, img):
        cands = self.find_corners(img)
        if not cands:
            return None, None
        pil = np.argwhere(ROLE == 1)
        best = None
        for P in cands:
            for mirror in (False, True):
                Q = P[::-1] if mirror else P
                for k in range(4):
                    Qk = np.roll(Q, k, 0)
                    A = np.c_[FINDER_CENTRES, np.ones(4)]
                    M, *_ = np.linalg.lstsq(A, Qk, rcond=None)      # affine frame -> pixel
                    pos = np.c_[pil + 0.5, np.ones(len(pil))] @ M
                    v = ndimage.map_coordinates(img, pos.T, order=1, mode="nearest")
                    lv = LEVELS[PILOT[pil[:, 0], pil[:, 1]]]
                    score = np.corrcoef(v, lv)[0, 1]
                    if best is None or score > best[0]:
                        best = (score, M)
        M = best[1]
        allc = np.argwhere(np.ones((N, N), bool))
        pos = np.c_[allc + 0.5, np.ones(len(allc))] @ M
        vals = ndimage.map_coordinates(img, pos.T, order=1, mode="nearest").reshape(N, N)
        # illumination plane + level means from pilots
        pr, pc = pil[:, 0], pil[:, 1]
        pl = PILOT[pr, pc]
        g = np.ones(len(pil))
        Ap = np.c_[np.ones(len(pil)), pr - N / 2, pc - N / 2]
        for _ in range(6):
            m = np.array([np.mean(vals[pr, pc][pl == l] / g[pl == l]) for l in range(4)])
            coef, *_ = np.linalg.lstsq(Ap * m[pl][:, None], vals[pr, pc], rcond=None)
            g = Ap @ coef
            m *= g.mean(); g /= g.mean()
        rr, cc = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
        G = coef[0] + coef[1] * (rr - N / 2) + coef[2] * (cc - N / 2)
        G = G / np.mean(Ap @ coef)
        x = vals / G
        est = np.argmin(np.abs(x[..., None] - m[None, None, :]), -1)
        est[ROLE == 1] = PILOT[ROLE == 1]
        # neighbour-interference cancellation (decision directed, 2 rounds)
        for _ in range(2):
            mv = m[est]
            mv[ROLE == 2] = m[3]
            mbar = m.mean()
            pad = np.pad(mv - mbar, 1, constant_values=m[0] - mbar)
            n4 = pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:]
            nd = pad[:-2, :-2] + pad[:-2, 2:] + pad[2:, :-2] + pad[2:, 2:]
            sel = ROLE != 2
            A = np.c_[mv[sel], n4[sel], nd[sel], np.ones(sel.sum())]
            beta, *_ = np.linalg.lstsq(A, x[sel], rcond=None)
            y = (x - beta[1] * n4 - beta[2] * nd - beta[3]) / max(beta[0], 1e-3)
            est = np.argmin(np.abs(y[..., None] - m[None, None, :]), -1)
            est[ROLE == 1] = PILOT[ROLE == 1]
        return est, M


def trial(rd, rng, noise=None, jitter=None):
    noise = NOISE if noise is None else noise
    jitter = JITTER if jitter is None else jitter
    levels = rng.integers(0, 4, (N, N))
    levels[ROLE == 1] = PILOT[ROLE == 1]
    T = (rng.uniform(0, 2 * math.pi), rng.uniform(0.97, 1.03),
         rng.uniform(-0.5, 0.5) * LAM / rd.na, rng.uniform(-0.5, 0.5) * LAM / rd.na)
    jit = rng.normal(0, jitter, (N, N))
    R = rd.render(levels, T, jit)
    a, b = rng.uniform(-1, 1, 2)
    span = rd.nc / 2
    rr, cc = np.meshgrid(np.arange(rd.nc), np.arange(rd.nc), indexing="ij")
    gain = 1 + 0.2 * (a * (rr - span) + b * (cc - span)) / (span * math.sqrt(2))
    img = rd.image(R, gain) + rng.normal(0, noise, (rd.nc, rd.nc))
    est, M = rd.decode(img)
    data = ROLE == 0
    # true cell-centre positions vs estimated
    allc = np.argwhere(np.ones((N, N), bool)) + 0.5
    true_pix = rd.world_to_pix(rd.to_world(allc, T))
    if est is None:
        return levels[data], rng.integers(0, 4, data.sum()), False, float("nan")
    est_pix = np.c_[allc, np.ones(len(allc))] @ M
    err = np.max(np.linalg.norm(est_pix - true_pix, axis=1)) * rd.pix / rd.p
    ok = err < 0.5
    return levels[data], est[data], ok, err


def mi4(x, y):
    C = np.zeros((4, 4))
    np.add.at(C, (x, y), 1)
    P = C / C.sum()
    px, py = P.sum(1, keepdims=True), P.sum(0, keepdims=True)
    nz = P > 0
    return float(np.sum(P[nz] * np.log2(P[nz] / (px @ py)[nz])))


def run(trials=200, nas=(0.25, 0.45, 0.65), pitches=(0.6, 0.75, 0.9, 1.1, 1.4, 1.8)):
    """Pitch sweep. Each reader class has its own fixed seed, so running the
    classes one by one or in parallel (NAS=...) gives identical results."""
    out = []
    data_frac = float(np.mean(ROLE == 0))
    for na in nas:
        rng = np.random.default_rng(5 + int(round(na * 100)))
        for k in pitches:
            p = round(k * LAM / na, 3)
            rd = Reader(na, p)
            t0 = time.time()
            xs, ys, oks, errs = [], [], [], []
            for _ in range(trials):
                x, y, ok, e = trial(rd, rng)
                xs.append(x); ys.append(y); oks.append(ok); errs.append(e)
            x, y = np.concatenate(xs), np.concatenate(ys)
            mi = mi4(x, y)
            gray = lambda n: n ^ (n >> 1)
            ber = np.mean([bin(gray(a) ^ gray(b)).count("1") for a, b in zip(x, y)]) / 2
            res = {"na": na, "pitch_um": p, "pitch_over_lambda_na": k, "trials": trials,
                   "align_success": float(np.mean(oks)),
                   "align_ci95": list(wilson(int(np.sum(oks)), trials)),
                   "max_cell_error_cells_median": float(np.nanmedian(errs)),
                   "ser": float(np.mean(x != y)), "ber_gray": float(ber),
                   "bits_per_cell": mi, "data_fraction": data_frac,
                   "net_density_bits_per_um2": mi * data_frac / p ** 2,
                   "camera_pixel_um": rd.pix, "pixels_per_cell": p / rd.pix}
            out.append(res)
            print(f"NA={na} p={p:.3f} align={res['align_success']:.2f} SER={res['ser']:.3f} "
                  f"bits={mi:.2f} net={res['net_density_bits_per_um2']:.2f} b/um2 ({time.time()-t0:.0f}s)", flush=True)
    return out


def wilson(k, n, z=1.96):
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def run_sensitivity(trials=120, seed=77, na=0.45):
    """Camera noise and writing variability doubled, one reader class."""
    rng = np.random.default_rng(seed)
    out = []
    for label, noise, jitter in (("baseline", NOISE, JITTER), ("noise x2", 2 * NOISE, JITTER),
                                 ("writing variability x2", NOISE, 2 * JITTER),
                                 ("both x2", 2 * NOISE, 2 * JITTER)):
        for k in (0.9, 1.1, 1.4):
            p = round(k * LAM / na, 3)
            rd = Reader(na, p)
            xs, ys, oks = [], [], []
            for _ in range(trials):
                x, y, ok, _e = trial(rd, rng, noise, jitter)
                xs.append(x); ys.append(y); oks.append(ok)
            x, y = np.concatenate(xs), np.concatenate(ys)
            lo, hi = wilson(int(np.sum(oks)), trials)
            out.append({"case": label, "na": na, "pitch_over_lambda_na": k, "pitch_um": p,
                        "noise": noise, "jitter": jitter, "align_success": float(np.mean(oks)),
                        "align_ci95": [lo, hi], "ser": float(np.mean(x != y)), "bits_per_cell": mi4(x, y)})
            print(f"{label:24s} k={k} align={np.mean(oks):.3f} [{lo:.3f},{hi:.3f}] SER={np.mean(x != y):.4f}", flush=True)
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    QUICK = os.environ.get("QUICK") == "1"
    nas = tuple(float(v) for v in os.environ.get("NAS", "0.25,0.45,0.65").split(","))
    tag = os.environ.get("TAG", "")
    if os.environ.get("SENS") == "1" or QUICK:
        json.dump(run_sensitivity(8 if QUICK else 120), open(os.path.join(OUT, "samm_sensitivity.json"), "w"), indent=1)
        if os.environ.get("SENS") == "1":
            raise SystemExit
    tr = int(os.environ.get("TRIALS", "8" if QUICK else "200"))
    kw = {"pitches": (0.9, 1.4)} if QUICK else {}
    json.dump(run(tr, nas=nas, **kw), open(os.path.join(OUT, f"samm{tag}.json"), "w"), indent=1)
