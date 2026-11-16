"""Illustrations for README and papers (no statistics, just pictures).

  figures/fig0_symbols.png        -- what the symbols look like before and after the optics
  figures/fig6_samm_pipeline.png  -- one SAMM frame: written, photographed, decoded

Usage: python3 make_illustrations.py
"""
import math

import numpy as np
from matplotlib.patches import Rectangle
from plotstyle import EDGE, ERR, INK, INK2, S1, plt, save

import samm_sim as S
import vods_sim as V

plt.rcParams.update({"font.size": 10, "axes.grid": False})


def fig_symbols():
    # (label, kind, args): wedge args = (theta, z, k, r); APSK args = phase index, reflectance
    syms = [("Wedge 0°, straight", "w", (0, 0, 0, 0)),
            ("Wedge 135°, left arc", "w", (135, 2, 1, 0)),
            ("Wedge 270°, S-wave", "w", (270, 1, 3, 1)),
            ("APSK dot, phase 2", "a", (2, 0)),
            ("APSK dot, phase 6", "a", (6, 1))]
    rows = [("Written\n(500 nm pitch)", 0.5, "obj"), ("Read\n(500 nm pitch)", 0.5, "img"),
            ("Read\n(150 nm pitch)", 0.15, "img")]
    fig, axes = plt.subplots(3, 5, figsize=(10, 6.4))
    for ri, (rl, p, what) in enumerate(rows):
        opt = V.Optics(p, 1)
        c, h = opt.N // 2, V.OS
        for ci, (lab, kind, a) in enumerate(syms):
            if kind == "w":
                d = V.render_delta(opt.X, opt.Y, p, *a)
            else:
                dot = (np.abs(opt.X) < 0.3 * p) & (np.abs(opt.Y) < 0.3 * p)
                ph = 2 * np.pi * a[0] / 8 + np.pi / 8
                d = np.where(dot, V.A_FLOOR[a[1]] * np.exp(1j * ph) - 1, 0)
            ax = axes[ri, ci]
            if what == "obj":
                field = (1 + d)[c - h:c + h, c - h:c + h]
                written = np.abs(d[c - h:c + h, c - h:c + h]) > 1e-9
                ph = np.where(written, np.angle(field), np.nan)
                ax.imshow(np.where(written, 0.0, 1.0), cmap="gray", vmin=0, vmax=1.6)
                ax.imshow(ph, cmap="twilight", vmin=-np.pi, vmax=np.pi)
            else:
                img = np.abs(1 + opt.image(d))
                ax.imshow(img, cmap="gray", vmin=0, vmax=1.6, interpolation="nearest")
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_color(EDGE)
            if ri == 0:
                ax.set_title(lab, fontsize=9.5, color=INK)
            if ci == 0:
                ax.set_ylabel(rl, fontsize=10, color=INK2, rotation=0, ha="right", va="center", labelpad=8)
    fig.suptitle("At 500 nm each symbol leaves a distinct footprint; at 150 nm they all fade into the same faint blur",
                 x=0.02, ha="left", fontsize=12, color=INK)
    fig.text(0.02, 0.01, "Simulated: 405 nm, NA 0.90, coherent interferometric readout; window = 2 x 2 cells. "
             "Row 1 colour = engraving phase (depth); rows 2-3 show image amplitude only.", fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    save(fig, "fig0_symbols", dpi=180)


def fig_samm():
    rng = np.random.default_rng(2026)
    na, k = 0.45, 1.1
    p = round(k * S.LAM / na, 3)
    rd = S.Reader(na, p)
    levels = rng.integers(0, 4, (S.N, S.N))
    levels[S.ROLE == 1] = S.PILOT[S.ROLE == 1]
    T = (math.radians(27.0), 1.02, 0.3, -0.2)
    jit = rng.normal(0, S.JITTER, (S.N, S.N))
    R = rd.render(levels, T, jit)
    rr, cc = np.meshgrid(np.arange(rd.nc), np.arange(rd.nc), indexing="ij")
    span = rd.nc / 2
    gain = 1 + 0.2 * (0.8 * (rr - span) - 0.6 * (cc - span)) / (span * math.sqrt(2))
    img = rd.image(R, gain) + rng.normal(0, S.NOISE, (rd.nc, rd.nc))
    cands = rd.find_corners(img)
    est, M = rd.decode(img)
    data = S.ROLE == 0
    ok = (est == levels) | ~data
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.2))
    ext = [-rd.nf / 2 * rd.dx, rd.nf / 2 * rd.dx, rd.nf / 2 * rd.dx, -rd.nf / 2 * rd.dx]
    axes[0].imshow(R, cmap="gray", vmin=0, vmax=1, extent=ext)
    axes[0].set_title("1. Written frame (rotated 27°, scale +2%)", fontsize=10)
    axes[1].imshow(img, cmap="gray", interpolation="nearest")
    if cands:
        P = cands[0]
        axes[1].plot(P[:, 1], P[:, 0], "o", ms=9, mfc="none", mec=S1, mew=2)
    axes[1].set_title("2. Camera image (NA 0.45, tilted light);\n    finders found (blue)", fontsize=10)
    grid = np.where(S.ROLE == 2, np.nan, S.LEVELS[est])
    axes[2].imshow(grid, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    for (i, j) in np.argwhere(S.ROLE == 1):
        axes[2].add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=S1, lw=1))
    for (i, j) in np.argwhere(~ok):
        axes[2].add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=ERR, lw=2))
    n_err = int(np.sum(~ok))
    axes[2].set_title(f"3. Decoded and straightened: {data.sum() - n_err} of {data.sum()}\n"
                      f"    data cells correct (pilots outlined in blue)", fontsize=10)
    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"SAMM frame, 24 x 24 cells, pitch {p:.2f} µm, read with a budget 20x objective",
                 x=0.02, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "fig6_samm_pipeline", dpi=180)
    return n_err


if __name__ == "__main__":
    fig_symbols()
    print("SAMM demo errors:", fig_samm())
