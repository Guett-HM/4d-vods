"""Builds the result figures (figures/fig1-fig7) and results/summary.json from results/*.json."""
import json
import os

import numpy as np
from plotstyle import INK2, S1, S2, S3, S4, SURF, plt, save, title

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(D, "results")

PITCHES = [150, 200, 250, 300, 400, 500, 600, 800]
BD = 25e9 * 8 / (np.pi * (58 ** 2 - 24 ** 2) * 1e6)   # BD-25 user bits per um^2
BDXL = BD * 33.4 / 25                                 # BDXL: 33.4 GB per layer, same optics


def load(cfg):
    return [json.load(open(os.path.join(R, f"lattice_p{p}_{cfg}.json"))) for p in PITCHES]


def series(cfg, key="density_bits_per_um2"):
    return np.array([d[key] for d in load(cfg)])


p_nm = np.array(PITCHES)

# ---- Fig 1: areal density vs pitch ---------------------------------------
fig, ax = plt.subplots(figsize=(7.6, 4.6))
claim = 8 / (p_nm / 1000) ** 2
w_real = series("realistic_64k_j10")
w_gen = series("wedge_genie_64k_j10")
a_real = series("apsk16_64k_j10")
ax.plot(p_nm, claim, color=INK2, lw=1.5, ls=(0, (4, 3)), label="Naive estimate (8 bits per symbol)")
ax.plot(p_nm, w_gen, color=S1, lw=1.5, ls=(0, (2, 2)), marker="o", ms=4, mfc=SURF,
        label="Voxel-Wedge, ideal decoder (upper bound)")
ax.plot(p_nm, w_real, color=S1, lw=2, marker="o", ms=7, mec=SURF, mew=1.5,
        label="Voxel-Wedge, practical decoder")
ax.plot(p_nm, a_real, color=S2, lw=2, marker="s", ms=7, mec=SURF, mew=1.5,
        label="APSK-16 dots (0.6p square), practical decoder")
ax.axhline(BDXL, color=INK2, lw=1, ls=(0, (1, 1)), label=f"BDXL 33.4 GB per layer, net user data ({BDXL:.1f})")
ax.axhline(BD, color=INK2, lw=1, ls=":", label=f"Blu-ray 25 GB per layer, net user data ({BD:.1f})")
ax.text(805, BDXL * 1.05, "BDXL", color=INK2, fontsize=8.5, ha="right", va="bottom")
ax.text(805, BD * 0.95, "Blu-ray", color=INK2, fontsize=8.5, ha="right", va="top")
ax.set_yscale("log")
ax.set_ylim(0.1, 600)
ax.set_xlabel("Lattice pitch (nm)")
ax.set_ylabel("Information before error correction (bits/µm², log)")
ax.set_xticks(PITCHES)
ax.legend(loc="lower right", fontsize=8.5)
title(ax, "Effective density vs pitch (405 nm, NA 0.90, 10% writing variability)")
fig.tight_layout()
save(fig, "fig1_density_vs_pitch",
     ["pitch_nm", "naive_estimate", "wedge_ideal_decoder", "wedge_practical", "apsk16_practical",
      "bdxl_net", "bluray_net"],
     [(int(p), float(c), float(g), float(w), float(a), BDXL, BD)
      for p, c, g, w, a in zip(p_nm, claim, w_gen, w_real, a_real)])

# ---- Fig 2: per-DoF delivered fraction vs pitch ---------------------------
fig, ax = plt.subplots(figsize=(7.6, 4.3))
rows = load("realistic_64k_j10")
names = [("reflectance", "Reflectance ρ (1 bit)", S3, "D"),
         ("depth_slope", "Depth/slope Z (2 bits)", S2, "s"),
         ("azimuth", "Azimuth θ (3 bits)", S1, "o"),
         ("curvature", "Curvature κ (2 bits)", S4, "^")]
for key, lab, col, mk in names:
    y = [100 * r["dof"][key]["mi_bits"] / r["dof"][key]["max_bits"] for r in rows]
    ax.plot(p_nm, y, color=col, lw=2, marker=mk, ms=7, mec=SURF, mew=1.5, label=lab)
ax.set_ylim(-3, 105)
ax.set_xticks(PITCHES)
ax.set_xlabel("Lattice pitch (nm)")
ax.set_ylabel("Information recovered (% of maximum)")
ax.legend(loc="lower right", fontsize=9.5)
title(ax, "Which degrees of freedom survive as the pitch shrinks")
fig.tight_layout()
save(fig, "fig2_dof_vs_pitch", ["pitch_nm"] + [k + "_percent" for k, *_ in names],
     [(int(p), *[100 * r["dof"][k]["mi_bits"] / r["dof"][k]["max_bits"] for k, *_ in names])
      for p, r in zip(p_nm, rows)])

# ---- Fig 3: rotational skew ----------------------------------------------
sk = json.load(open(os.path.join(R, "skew.json")))
fig, ax = plt.subplots(figsize=(7.6, 4.3))
e = np.array(sk["eps"])
for key, lab, col, mk in (("absolute", "Absolute angle", INK2, "o"),
                          ("darp", "DARP (differential)", S1, "s"),
                          ("pilot", "Pilot symbols (1 in 16)", S2, "D")):
    ax.plot(e, 100 * np.array(sk[key]), color=col, lw=2, marker=mk, ms=6, mec=SURF, mew=1.2, label=lab)
ax.set_yscale("log")
ax.set_ylim(1, 110)
ax.set_xlabel("Systematic media rotation ε (degrees)")
ax.set_ylabel("Azimuth symbol error (%, log)")
ax.set_xticks(range(0, 91, 15))
ax.legend(loc="center right", fontsize=9.5)
title(ax, "Rotation robustness: absolute vs DARP vs pilots (500 nm pitch)")
fig.tight_layout()
save(fig, "fig3_skew", ["rotation_deg", "absolute_percent", "darp_percent", "pilot_percent"],
     [(float(ei), 100 * a, 100 * d, 100 * q) for ei, a, d, q in zip(e, sk["absolute"], sk["darp"], sk["pilot"])])

# ---- Fig 4: RLE vs software compression ----------------------------------
rl = json.load(open(os.path.join(R, "rle.json")))
labels = [r["dataset"] for r in rl]
phys = np.array([100 * r["symbols_physical_rle"] / r["symbols_raw"] for r in rl])
soft = np.array([100 * min(r["symbols_lzma"], r["symbols_zlib9"]) / r["symbols_raw"] for r in rl])
fig, ax = plt.subplots(figsize=(7.6, 4.0))
y = np.arange(len(rl))
h = 0.36
ax.barh(y - h / 2 - 0.01, phys, h, color=S1, label="Physical • glyphs (on-media RLE)")
ax.barh(y + h / 2 + 0.01, soft, h, color=S2, label="Software compression (zlib/LZMA) before writing")
for yi, v in zip(y, phys):
    ax.text(v + 1, yi - h / 2, f"{v:.1f}%", va="center", fontsize=9, color=INK2)
for yi, v in zip(y, soft):
    ax.text(v + 1, yi + h / 2, f"{v:.1f}%", va="center", fontsize=9, color=INK2)
ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.invert_yaxis()
ax.set_xlim(0, 118)
ax.grid(axis="y", visible=False)
ax.set_xlabel("Symbols written (% of uncompressed data)")
ax.legend(loc="lower center", bbox_to_anchor=(0.45, -0.42), ncol=1, fontsize=9.5)
title(ax, "Physical symbols needed: on-media RLE vs software compression")
fig.tight_layout()
save(fig, "fig4_rle", ["dataset", "onmedia_rle_percent", "software_compression_percent"],
     [(lab, float(a), float(b)) for lab, a, b in zip(labels, phys, soft)], bbox_inches="tight")

# ---- summary table for the paper -----------------------------------------
summ = {"bd_bits_per_um2": BD, "bdxl_bits_per_um2": BDXL, "rows": []}
for i, p in enumerate(PITCHES):
    row = {"pitch_nm": p, "claim": float(claim[i])}
    for cfg in ("ideal_64k", "realistic_64k_j10", "wedge_genie_64k_j10", "apsk16_64k_j10",
                "apsk16_genie_64k_j10", "ideal_6k4", "ideal_640k"):
        d = json.load(open(os.path.join(R, f"lattice_p{p}_{cfg}.json")))
        row[cfg] = {"bits": d["bits_per_symbol_lb"], "dens": d["density_bits_per_um2"],
                    "ser": d["symbol_error_rate"]}
    summ["rows"].append(row)
summ["skew"] = {k: sk[k] for k in ("sigma", "gray")}

# ---- Fig 5: self-aligning micro-matrix (SAMM), low-cost reader -----------
sm = json.load(open(os.path.join(R, "samm.json")))
fig, ax = plt.subplots(figsize=(7.6, 4.3))
rows5 = []
for na, col, mk in ((0.25, S1, "o"), (0.45, S2, "s"), (0.65, S3, "D")):
    rr = [r for r in sm if r["na"] == na]
    k = [r["pitch_over_lambda_na"] for r in rr]
    lo = [100 * r["align_ci95"][0] for r in rr]
    hi = [100 * r["align_ci95"][1] for r in rr]
    ax.fill_between(k, lo, hi, color=col, alpha=0.15, lw=0)
    ax.plot(k, [100 * r["align_success"] for r in rr],
            color=col, lw=2, marker=mk, ms=7, mec=SURF, mew=1.5, label=f"NA {na}")
    rows5 += [(na, r["pitch_over_lambda_na"], round(r["pitch_um"], 3), r["trials"], 100 * r["align_success"],
               100 * r["align_ci95"][0], 100 * r["align_ci95"][1], r["ser"]) for r in rr]
ax.axhline(99, color=INK2, lw=1, ls=":")
ax.text(1.02, 90, "Dotted line: 99% target.\nShaded bands: 95% confidence intervals,\n200 frames per point.",
        color=INK2, fontsize=8.5, va="top", linespacing=1.4)
ax.set_xlabel("Cell pitch / (λ / NA)")
ax.set_ylabel("Frames found and aligned (%)")
ax.set_ylim(0, 105)
ax.legend(loc="lower right", fontsize=9.5)
title(ax, "SAMM self-alignment, random rotation 0–360°, ±3% scale, ±20% illumination")
fig.tight_layout()
save(fig, "fig5_samm_alignment", ["na", "pitch_over_lambda_na", "pitch_um", "frames", "aligned_percent",
                                  "ci95_low_percent", "ci95_high_percent", "symbol_error_rate"], rows5)
summ["samm"] = sm
# ---- Fig 7: writing-variability sensitivity ------------------------------
sens = json.load(open(os.path.join(R, "sensitivity.json")))
fig, ax = plt.subplots(figsize=(7.6, 4.6))
rows7 = []
for alph, col, mk, base in (("apsk16", S2, "s", "apsk16_64k_j10"), ("wedge256", S1, "o", "realistic_64k_j10")):
    name = "APSK-16" if alph == "apsk16" else "Voxel-Wedge"
    for jit, alpha, ls in ((0.05, 1.0, "-"), (0.10, 0.75, "--"), (0.20, 0.45, ":")):
        if jit == 0.10:
            ys = series(base)
        else:
            ys = [next(r["density_bits_per_um2"] for r in sens if r["alphabet"] == alph and r["fab_jitter"] == jit
                       and abs(r["pitch_um"] * 1000 - p) < 1) for p in PITCHES]
        ax.plot(p_nm, ys, color=col, alpha=alpha, lw=2, ls=ls, marker=mk, ms=5,
                label=f"{name}, {int(jit * 100)}% writing variability")
        rows7 += [(name, jit, int(p), float(v)) for p, v in zip(p_nm, ys)]
ax.axhline(BD, color=INK2, lw=1, ls=":")
ax.text(805, BD * 1.06, "Blu-ray layer (net user data)", color=INK2, fontsize=9, ha="right", va="bottom")
ax.set_xticks(PITCHES)
ax.set_xlabel("Lattice pitch (nm)")
ax.set_ylabel("Information before error correction (bits/µm²)")
ax.legend(fontsize=8.5, loc="upper right")
title(ax, "APSK-16 stays ahead of the Voxel-Wedge at 5%, 10% and 20% writing variability", size=11)
fig.tight_layout()
save(fig, "fig7_sensitivity", ["alphabet", "writing_variability", "pitch_nm", "density_bits_per_um2"], rows7)
summ["sensitivity"] = sens
summ["spread"] = json.load(open(os.path.join(R, "spread.json")))
if os.path.exists(os.path.join(R, "samm_sensitivity.json")):
    summ["samm_sensitivity"] = json.load(open(os.path.join(R, "samm_sensitivity.json")))
with open(os.path.join(R, "summary.json"), "w") as f:
    json.dump(summ, f, indent=1)
print("figures ok")
