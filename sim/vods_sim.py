"""
4D-VODS physical-layer simulator (v0.1)
=======================================

Simulates writing, optical readout and decoding of "Voxel-Wedge" symbols
(1 byte per symbol, 4 degrees of freedom) on a 2D lattice, to measure how many
bits per symbol and per square micron are actually recoverable as a function
of the lattice pitch.

Physical model (deliberately simple and stated explicitly):
  * Reflective sample, coherent illumination, lambda = 405 nm, NA = 0.90.
  * Readout is interferometric: the camera measures the complex reflected
    field (amplitude + phase), as proposed in the 4D-VODS note (OCT / PSI).
  * Coherent imaging = object field low-pass filtered by a circular pupil of
    cutoff NA/lambda (scalar Fourier optics, no polarisation, no 3D effects).
  * Object field: 1 outside features; a * exp(i*4*pi*h/lambda) inside a wedge,
    where h(x,y) is the engraving depth and a the floor reflectance.
  * Camera: 8 x 8 pixels per symbol cell (as in the v2 spec), complex Gaussian
    noise with std sigma = 1/sqrt(photons per pixel) (shot-noise limited).
  * Symbol geometry scales with the pitch p (length 0.75p, head 0.6p,
    tail 0.17p, max tail deflection 0.12p) -> at p = 150 nm this reproduces
    the 90 nm head / 25 nm tail of the v2 spec.

NOT modelled (so results are an upper bound on the physics side):
  fabrication jitter, heat-affected zones, focus/tilt errors, polarisation,
  multilayer cross-talk, sensor bandwidth.
The decoder is a template matcher with successive interference cancellation;
a trained CNN (as in Microsoft Project Silica) could do somewhat better, so on
the decoder side results are conservative.

Usage:
  python3 vods_sim.py              # every experiment -> results/*.json (~20 min, 2 cores)
  QUICK=1 python3 vods_sim.py      # smoke run -> results_quick/ (numbers not meaningful)
  python3 vods_sim.py rle|skew|sensitivity|spread|lattice:0.3,0.5|extra:0.3
"""
import json
import math
import os
import sys
import time
import zlib
import lzma

import numpy as np

LAM = 0.405          # um
NA = 0.90
OS = 24              # fine-grid pixels per pitch
CAM = 8              # camera pixels per pitch (v2 spec: 8x8 oversampling)
F = OS // CAM        # fine pixels per camera pixel
H_STRATA = (0.040, 0.090)   # um, L0 / L1 depth (v2 spec)
A_FLOOR = (1.0, 0.5)        # floor amplitude: specular / diffusive
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results_quick" if os.environ.get("QUICK") == "1" else "results")


# --------------------------------------------------------------------------
# Symbol mapping  [b7 b6 b5 | b4 b3 | b2 b1 | b0]
# --------------------------------------------------------------------------
def split_byte(b):
    return (b >> 5) & 7, (b >> 3) & 3, (b >> 1) & 3, b & 1


def render_delta(X, Y, p, theta_deg, z, k, r):
    """Return (object_field - 1) for one wedge centred at the origin."""
    th = math.radians(theta_deg)
    L, Wh, Wt, D = 0.75 * p, 0.60 * p, 0.17 * p, 0.12 * p
    u = X * math.cos(th) + Y * math.sin(th)       # along head -> tail
    v = -X * math.sin(th) + Y * math.cos(th)      # transverse
    t = (u + L / 2) / L
    inside_u = (t >= 0) & (t <= 1)
    tc = np.clip(t, 0, 1)
    w = Wh + (Wt - Wh) * tc
    k1, k2 = {0: (0, 0), 1: (1, 0), 2: (-1, 0), 3: (0, 1)}[k]
    vc = k1 * 4 * D * tc * (1 - tc) + k2 * D * np.sin(2 * np.pi * tc)
    mask = inside_u & (np.abs(v - vc) < w / 2)
    stratum, slope = z >> 1, z & 1
    h0 = H_STRATA[stratum]
    h = h0 * (1.25 - 0.5 * tc) if slope == 0 else h0 * (0.75 + 0.5 * tc)
    field = A_FLOOR[r] * np.exp(1j * 4 * np.pi * h / LAM)
    return np.where(mask, field - 1.0, 0.0)


class Optics:
    """Fine grid + coherent pupil for a given pitch."""

    def __init__(self, p, half_cells):
        self.p = p
        margin = math.ceil(1.5 / p)                   # >= 1.5 um PSF margin
        ncell = 2 * (half_cells + margin) + 1         # odd -> cell-centred
        self.N = ncell * OS
        self.dx = p / OS
        x = (np.arange(self.N) - (self.N - 1) / 2) * self.dx
        self.X, self.Y = np.meshgrid(x, x)
        f = np.fft.fftfreq(self.N, d=self.dx)
        FX, FY = np.meshgrid(f, f)
        self.pupil = (FX ** 2 + FY ** 2) <= (NA / LAM) ** 2
        self.half_cells = half_cells

    def image(self, delta):
        """Coherent image of delta, binned to camera pixels, cropped to
        +-half_cells around the centre. Returns complex64 array."""
        E = np.fft.ifft2(np.fft.fft2(delta) * self.pupil)
        n = self.N // F
        cam = E.reshape(n, F, n, F).mean(axis=(1, 3))
        c = n // 2
        h = self.half_cells * CAM
        return cam[c - h:c + h, c - h:c + h].astype(np.complex64)


# --------------------------------------------------------------------------
# Experiment 1: full 256-state alphabet on a 2D lattice, sweep pitch
# --------------------------------------------------------------------------
ARR = 7          # 7x7 symbols per trial, central 3x3 scored
CROP = 7         # stored symbol images span +-7 cells


def build_templates(p, alphabet="wedge256"):
    opt = Optics(p, CROP)
    if alphabet == "wedge256":
        n = 256
        render = lambda b: render_delta(opt.X, opt.Y, p, split_byte(b)[0] * 45.0, *split_byte(b)[1:])
    elif alphabet.startswith("apsk"):
        # isotropic square dot (0.6p); n_phase phase levels x 2 floor amplitudes
        n_phase = int(alphabet[4:]) // 2
        n = 2 * n_phase
        dot = (np.abs(opt.X) < 0.3 * p) & (np.abs(opt.Y) < 0.3 * p)

        def render(b):
            ph = 2 * np.pi * (b % n_phase) / n_phase + np.pi / n_phase
            a = A_FLOOR[b // n_phase]
            return np.where(dot, a * np.exp(1j * ph) - 1.0, 0.0)
    else:
        raise ValueError(alphabet)
    G = np.empty((n, 2 * CROP * CAM, 2 * CROP * CAM), np.complex64)
    for b in range(n):
        G[b] = opt.image(render(b))
    return G


def run_lattice(p, photons_per_cell, trials, seed=0, sic_iters=3, G=None, fab_jitter=0.0,
                genie=False):
    """fab_jitter: std of a complex multiplicative error per written symbol
    (models shot-to-shot variability of depth / reflectance in writing).
    genie=True: neighbours are assumed known (nominal templates subtracted) --
    an upper bound for any joint / CNN decoder working on the same images."""
    rng = np.random.default_rng(seed)
    if G is None:
        G = build_templates(p)
    S = CROP * CAM                      # index of symbol centre in G
    half = ARR // 2
    RP = (half + 1) * CAM               # region half-size in pixels (32)
    W2 = CAM                            # decode window: cell +- 0.5 cell -> 16x16 px
    # template windows (16x16) centred on the symbol
    nsym = G.shape[0]
    T = G[:, S - W2:S + W2, S - W2:S + W2].reshape(nsym, -1)
    Tn = np.sum(np.abs(T) ** 2, axis=1)
    Th = T.conj().T
    sigma = 1.0 / math.sqrt(photons_per_cell / CAM ** 2)
    offs = [(i, j) for i in range(-half, half + 1) for j in range(-half, half + 1)]
    central = [n for n, (i, j) in enumerate(offs) if abs(i) <= 1 and abs(j) <= 1]

    def contrib(b, i, j):
        # contribution of symbol b at cell offset (i,j) to the region
        r0 = S - RP - i * CAM
        c0 = S - RP - j * CAM
        return G[b, r0:r0 + 2 * RP, c0:c0 + 2 * RP]

    def win(img, i, j):
        r0 = RP + i * CAM - W2
        c0 = RP + j * CAM - W2
        return img[r0:r0 + 2 * W2, c0:c0 + 2 * W2].reshape(-1)

    true_all, est_all = [], []
    for _ in range(trials):
        sym = rng.integers(0, nsym, len(offs))
        img = np.zeros((2 * RP, 2 * RP), np.complex64)
        jit = 1 + (fab_jitter / math.sqrt(2)) * (rng.standard_normal(len(offs))
                                                + 1j * rng.standard_normal(len(offs)))
        for b, (i, j), g in zip(sym, offs, jit):
            img += g * contrib(b, i, j)
        img += (sigma / math.sqrt(2)) * (rng.standard_normal(img.shape)
                                         + 1j * rng.standard_normal(img.shape))
        # initial decisions
        Yw = np.stack([win(img, i, j) for (i, j) in offs])
        est = np.argmin(Tn[None, :] - 2 * np.real(Yw @ Th), axis=1)
        if genie:
            est = sym.copy()
        for _it in range(1 if genie else sic_iters):
            recon = np.zeros_like(img)
            parts = []
            for b, (i, j) in zip(est, offs):
                c = contrib(b, i, j)
                parts.append(c)
                recon += c
            Yw = np.stack([win(img - recon + parts[n], i, j)
                           for n, (i, j) in enumerate(offs)])
            new = np.argmin(Tn[None, :] - 2 * np.real(Yw @ Th), axis=1)
            if genie:
                est = np.where(np.isin(np.arange(len(offs)), central), new, sym)
            else:
                est = new
        true_all.extend(sym[central])
        est_all.extend(est[central])
    return np.array(true_all), np.array(est_all)


def mutual_info(x, y, nx):
    C = np.zeros((nx, nx))
    np.add.at(C, (x, y), 1)
    P = C / C.sum()
    px, py = P.sum(1, keepdims=True), P.sum(0, keepdims=True)
    nz = P > 0
    return float(np.sum(P[nz] * np.log2(P[nz] / (px @ py)[nz])))


def summarize(p, ph, t, e, fab_jitter=0.0):
    ft, fe = np.array([split_byte(b) for b in t]), np.array([split_byte(b) for b in e])
    names, sizes = ["azimuth", "depth_slope", "curvature", "reflectance"], [8, 4, 4, 2]
    dof = {}
    mi_sum = 0.0
    for d, (nm, n) in enumerate(zip(names, sizes)):
        ser = float(np.mean(ft[:, d] != fe[:, d]))
        mi = mutual_info(ft[:, d], fe[:, d], n)
        mi_sum += mi
        dof[nm] = {"ser": ser, "mi_bits": mi, "max_bits": math.log2(n)}
    az_conf = np.zeros((8, 8), int)
    np.add.at(az_conf, (ft[:, 0], fe[:, 0]), 1)
    return {
        "pitch_um": p, "photons_per_cell": ph, "fab_jitter": fab_jitter, "n": int(len(t)),
        "symbol_error_rate": float(np.mean(t != e)),
        "bits_per_symbol_lb": mi_sum,
        "density_bits_per_um2": mi_sum / p ** 2,
        "claimed_density_bits_per_um2": 8 / p ** 2,
        "dof": dof, "azimuth_confusion": az_conf.tolist(),
    }


# --------------------------------------------------------------------------
# Experiment 2: rotational skew -- absolute vs DARP vs pilot symbols
# --------------------------------------------------------------------------
def run_skew(p=0.5, sigma=None, eps_list=range(0, 91, 5), rows=400, row_len=64,
             pilot_every=16, seed=1, target_ser=0.02):
    rng = np.random.default_rng(seed)
    opt = Optics(p, 1)
    angles = np.arange(360)
    T = np.stack([opt.image(render_delta(opt.X, opt.Y, p, a, 0, 0, 0)) for a in angles])
    T = T[:, 0:2 * CAM, 0:2 * CAM].reshape(360, -1)   # 16x16 window (isolated symbol)
    Tn = np.sum(np.abs(T) ** 2, 1)
    Th = T.conj().T

    def measure(theta_true_deg, sig):
        idx = np.mod(np.round(theta_true_deg).astype(int), 360)
        Y = T[idx] + (sig / math.sqrt(2)) * (rng.standard_normal(T[idx].shape)
                                             + 1j * rng.standard_normal(T[idx].shape))
        return angles[np.argmin(Tn[None, :] - 2 * np.real(Y @ Th), axis=1)].astype(float)

    def wrap(a):
        return np.mod(a + 180, 360) - 180

    # calibrate sigma so that the absolute decoder has ~target_ser at eps=0
    if sigma is None:
        lo, hi = 0.01, 5.0
        for _ in range(18):
            mid = math.sqrt(lo * hi)
            D = rng.integers(0, 8, 4000)
            th = measure(D * 45.0, mid)
            ser = np.mean(np.mod(np.round(th / 45), 8) != D)
            lo, hi = (mid, hi) if ser < target_ser else (lo, mid)
        sigma = math.sqrt(lo * hi)

    res = {"pitch_um": p, "sigma": sigma, "eps": [], "absolute": [], "darp": [], "pilot": [],
           "pilot_overhead": 1 / pilot_every}
    for eps in eps_list:
        err_abs = err_darp = err_pil = 0
        tot = 0
        for _ in range(rows):
            D = rng.integers(0, 8, row_len)
            # absolute
            th = measure(D * 45.0 + eps, sigma)
            err_abs += np.sum(np.mod(np.round(th / 45), 8) != D)
            # DARP: anchor at 0 then cumulative
            theta = np.concatenate([[0.0], np.cumsum(D * 45.0)])
            th = measure(theta + eps, sigma)
            Dh = np.mod(np.round(wrap(np.diff(th)) / 45), 8)
            err_darp += np.sum(Dh != D)
            # pilots: anchor (theta=0) every pilot_every positions
            pos = np.arange(row_len)
            is_p = (pos % pilot_every) == 0
            theta = np.where(is_p, 0.0, D * 45.0)
            th = measure(theta + eps, sigma)
            ph = np.radians(th[is_p])
            eps_hat = math.degrees(math.atan2(np.mean(np.sin(ph)), np.mean(np.cos(ph))))
            Dh = np.mod(np.round(wrap(th - eps_hat) / 45), 8)
            err_pil += np.sum(Dh[~is_p] != D[~is_p])
            tot += row_len
        n_data_pil = rows * int(np.sum((np.arange(row_len) % pilot_every) != 0))
        res["eps"].append(float(eps))
        res["absolute"].append(err_abs / tot)
        res["darp"].append(err_darp / tot)
        res["pilot"].append(err_pil / n_data_pil)
    # Gray vs natural mapping from the eps=0 absolute confusion
    D = rng.integers(0, 8, 200000)
    th = measure(D * 45.0, sigma)
    Dh = np.mod(np.round(th / 45), 8).astype(int)
    gray = lambda n: n ^ (n >> 1)
    nat_ber = np.mean([bin(a ^ b).count("1") for a, b in zip(D, Dh)]) / 3
    # with Gray coding the *bits* b = gray^-1(angle index); bit errors = popcount(gray^-1(a) ^ gray^-1(b))
    inv = {gray(n): n for n in range(8)}
    gray_ber = np.mean([bin(inv[a] ^ inv[b]).count("1") for a, b in zip(D, Dh)]) / 3
    res["gray"] = {"ser": float(np.mean(D != Dh)), "ber_natural": float(nat_ber),
                   "ber_gray": float(gray_ber)}
    return res


# --------------------------------------------------------------------------
# Experiment 3: physical RLE glyphs vs software compression
# --------------------------------------------------------------------------
def rle_symbols(data):
    """Symbols needed with the v2 rule: [S] + k bullets -> 2^k copies of S.
    Runs that are not powers of two are split into power-of-two chunks."""
    n, i = 0, 0
    while i < len(data):
        j = i
        while j < len(data) and data[j] == data[i]:
            j += 1
        run = j - i
        while run > 0:
            k = run.bit_length() - 1
            n += 1 + k
            run -= 1 << k
        i = j
    return n


def run_rle():
    rng = np.random.default_rng(2)
    import glob
    text = b""
    for fn in sorted(glob.glob(os.path.join(os.path.dirname(json.__file__), "*.py")))[:6]:
        text += open(fn, "rb").read()
    text = text[:65536]
    weights = rng.standard_normal(16384).astype(np.float32).tobytes()
    db = bytearray()
    for r in range(1024):  # fixed-width records with zero padding
        rec = f"{r:06d};customer_{rng.integers(1e6):07d};{rng.integers(0, 99999)}".encode()
        db += rec + b"\x00" * (64 - len(rec))
    sets = {
        "4 KB zero page": bytes(4096),
        "Padded database": bytes(db),
        "Text / source code": text,
        "Neural-net weights (float32)": weights,
        "Compressed / encrypted data": rng.integers(0, 256, 65536, dtype=np.uint8).tobytes(),
    }
    out = []
    for name, d in sets.items():
        out.append({
            "dataset": name, "bytes": len(d),
            "symbols_raw": len(d),
            "symbols_physical_rle": rle_symbols(d),
            "symbols_zlib9": len(zlib.compress(d, 9)),
            "symbols_lzma": len(lzma.compress(d, format=lzma.FORMAT_RAW,
                                              filters=[{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME}])),
        })
    return out


# --------------------------------------------------------------------------
def run_extra(pitches, trials=2000):
    """Genie-aided bound for the wedge alphabet + an isotropic APSK-16 alphabet."""
    for p in pitches:
        t0 = time.time()
        G = build_templates(p)
        for label, jit in (("wedge_genie_64k", 0.0), ("wedge_genie_64k_j10", 0.10)):
            t, e = run_lattice(p, 64_000, trials, seed=7, G=G, fab_jitter=jit, genie=True)
            s = summarize(p, 64_000, t, e, jit); s["config"] = label
            json.dump(s, open(os.path.join(OUT, f"lattice_p{int(round(p*1000))}_{label}.json"), "w"), indent=1)
            print(f"p={p} {label} bits={s['bits_per_symbol_lb']:.2f} dens={s['density_bits_per_um2']:.1f}", flush=True)
        for alph in ("apsk16",):
            G = build_templates(p, alph)
            n = G.shape[0]
            for label, jit, genie in ((f"{alph}_64k", 0.0, False), (f"{alph}_64k_j10", 0.10, False),
                                      (f"{alph}_genie_64k_j10", 0.10, True)):
                t, e = run_lattice(p, 64_000, trials, seed=11, G=G, fab_jitter=jit, genie=genie)
                mi = mutual_info(t, e, n)
                s = {"pitch_um": p, "config": label, "alphabet": alph, "fab_jitter": jit,
                     "symbol_error_rate": float(np.mean(t != e)), "bits_per_symbol_lb": mi,
                     "max_bits": math.log2(n), "density_bits_per_um2": mi / p ** 2, "n": int(len(t))}
                json.dump(s, open(os.path.join(OUT, f"lattice_p{int(round(p*1000))}_{label}.json"), "w"), indent=1)
                print(f"p={p} {label} SER={s['symbol_error_rate']:.3f} bits={mi:.2f} dens={mi/p**2:.1f} "
                      f"({time.time()-t0:.0f}s)", flush=True)


def _density(p, alphabet, t, e, jit):
    """bits/symbol (lower bound) and bits/um^2 for either alphabet."""
    if alphabet == "wedge256":
        s = summarize(p, 64_000, t, e, jit)
        return s["bits_per_symbol_lb"], s["density_bits_per_um2"], s["symbol_error_rate"]
    mi = mutual_info(t, e, 16)
    return mi, mi / p ** 2, float(np.mean(t != e))


def run_sensitivity(pitches, trials=2000, jitters=(0.05, 0.20)):
    """Writing-variability sensitivity for both alphabets, practical decoder."""
    out = []
    for p in pitches:
        for alph in ("wedge256", "apsk16"):
            G = build_templates(p, alph)
            for jit in jitters:
                t, e = run_lattice(p, 64_000, trials, seed=31 + int(p * 1000), G=G, fab_jitter=jit)
                bits, dens, ser = _density(p, alph, t, e, jit)
                out.append({"pitch_um": p, "alphabet": alph, "fab_jitter": jit, "bits_per_symbol": bits,
                            "density_bits_per_um2": dens, "symbol_error_rate": ser, "n": int(len(t))})
                print(f"sens p={p} {alph} jit={jit} bits={bits:.2f} dens={dens:.1f}", flush=True)
    return out


def run_spread(seeds=5, trials=2000):
    """Seed-to-seed spread of the two headline numbers (10% writing variability)."""
    out = []
    for alph, p in (("apsk16", 0.3), ("wedge256", 0.5)):
        G = build_templates(p, alph)
        d = []
        for sd in range(seeds):
            t, e = run_lattice(p, 64_000, trials, seed=1000 + sd, G=G, fab_jitter=0.10)
            d.append(_density(p, alph, t, e, 0.10)[1])
        out.append({"alphabet": alph, "pitch_um": p, "seeds": seeds, "trials_per_seed": trials,
                    "densities": d, "mean": float(np.mean(d)), "std": float(np.std(d, ddof=1))})
        print(f"spread {alph} p={p}: {np.mean(d):.2f} +- {np.std(d, ddof=1):.2f}", flush=True)
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    QUICK = os.environ.get("QUICK") == "1"      # smoke run: few trials, 2 pitches
    ALL_P = [0.3, 0.5] if QUICK else [0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8]
    NTR = 60 if QUICK else 2000
    if which in ("all", "sensitivity"):
        json.dump(run_sensitivity(ALL_P, NTR), open(os.path.join(OUT, "sensitivity.json"), "w"), indent=1)
    if which in ("all", "spread"):
        json.dump(run_spread(2 if QUICK else 5, NTR), open(os.path.join(OUT, "spread.json"), "w"), indent=1)
    if which in ("all", "rle"):
        json.dump(run_rle(), open(os.path.join(OUT, "rle.json"), "w"), indent=1)
        print("rle done")
    if which == "all":
        run_extra(ALL_P, NTR)
    if which in ("all", "skew"):
        kw = {"rows": 40, "eps_list": range(0, 91, 15)} if QUICK else {}
        json.dump(run_skew(**kw), open(os.path.join(OUT, "skew.json"), "w"), indent=1)
        print("skew done")
    if which.startswith("extra"):
        ps = [0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8]
        if ":" in which:
            ps = [float(x) for x in which.split(":")[1].split(",")]
        run_extra(ps, NTR)
    if which in ("all", "lattice") or which.startswith("lattice:"):
        pitches = ALL_P
        if which.startswith("lattice:"):
            pitches = [float(x) for x in which.split(":")[1].split(",")]
        configs = [  # (label, photons per cell, fabrication jitter)
            ("ideal_64k", 64_000, 0.0),
            ("ideal_6k4", 6_400, 0.0),
            ("ideal_640k", 640_000, 0.0),
            ("realistic_64k_j10", 64_000, 0.10),
        ]
        trials = int(os.environ.get("TRIALS", str(NTR)))
        for p in pitches:
            t0 = time.time()
            G = build_templates(p)
            for label, ph, jit in configs:
                t, e = run_lattice(p, ph, trials, seed=int(p * 1000) + ph % 97, G=G, fab_jitter=jit)
                s = summarize(p, ph, t, e, jit)
                s["config"] = label
                fn = os.path.join(OUT, f"lattice_p{int(round(p*1000))}_{label}.json")
                json.dump(s, open(fn, "w"), indent=1)
                print(f"p={p} {label} SER={s['symbol_error_rate']:.3f} "
                      f"bits={s['bits_per_symbol_lb']:.2f} dens={s['density_bits_per_um2']:.1f} "
                      f"({time.time()-t0:.0f}s)", flush=True)
