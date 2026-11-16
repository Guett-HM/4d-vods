"""Builds the result figures (figures/fig1-fig7) and results/summary.json from results/*.json."""
import json, os, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(D, "results")
FIG = os.path.join(D, "figures")
os.makedirs(FIG, exist_ok=True)

S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10.5, "axes.edgecolor": INK2,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "figure.facecolor": SURF,
    "axes.facecolor": SURF, "savefig.facecolor": SURF, "legend.frameon": False,
    "text.color": INK,
})
PITCHES = [150, 200, 250, 300, 400, 500, 600, 800]
BD = 25e9 * 8 / (np.pi * (58 ** 2 - 24 ** 2) * 1e6)   # BD-25 user bits per um^2


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
        label="Isotropic APSK-16 dots, practical decoder")
ax.axhline(BD, color=INK2, lw=1, ls=":", label=f"Blu-ray 25 GB per layer ({BD:.0f} bits/µm²)")
ax.set_yscale("log")
ax.set_ylim(0.1, 600)
ax.set_xlabel("Lattice pitch (nm)")
ax.set_ylabel("Information density (bits/µm², log scale)")
ax.set_xticks(PITCHES)
ax.legend(loc="lower right", fontsize=9)
ax.set_title("Effective density vs pitch (405 nm, NA 0.90, 10% write jitter)",
             loc="left", fontsize=11.5, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig1_density_vs_pitch.png"), dpi=200)
plt.close(fig)

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
ax.set_title("Which degrees of freedom survive as the pitch shrinks",
             loc="left", fontsize=11.5, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig2_dof_vs_pitch.png"), dpi=200)
plt.close(fig)

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
ax.set_title("Rotation robustness: absolute vs DARP vs pilots (500 nm pitch)",
             loc="left", fontsize=11.5, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig3_skew.png"), dpi=200)
plt.close(fig)

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
ax.set_title("Physical symbols needed: on-media RLE vs software compression",
             loc="left", fontsize=11.5, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig4_rle.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ---- summary table for the paper -----------------------------------------
summ = {"bd_bits_per_um2": BD, "rows": []}
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
for na, col, mk in ((0.25, INK2, "o"), (0.45, S2, "s"), (0.65, S1, "D")):
    rr = [r for r in sm if r["na"] == na]
    ax.plot([r["pitch_over_lambda_na"] for r in rr], [100 * r["align_success"] for r in rr],
            color=col, lw=2, marker=mk, ms=7, mec=SURF, mew=1.5, label=f"NA {na}")
ax.axhline(99, color=INK2, lw=1, ls=":")
ax.set_xlabel("Cell pitch / (λ / NA)")
ax.set_ylabel("Frames found and aligned (%)")
ax.set_ylim(0, 105)
ax.legend(loc="lower right", fontsize=9.5)
ax.set_title("SAMM self-alignment, random rotation 0–360°, ±3% scale, ±20% illumination",
             loc="left", fontsize=11.5, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig5_samm_alignment.png"), dpi=200)
plt.close(fig)
summ["samm"] = sm
# ---- Fig 7: writing-variability sensitivity ------------------------------
sens = json.load(open(os.path.join(R, "sensitivity.json")))
fig, ax = plt.subplots(figsize=(7.6, 4.6))
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
ax.axhline(BD, color=INK2, lw=1, ls=":")
ax.text(805, BD * 1.06, "Blu-ray layer", color=INK2, fontsize=9, ha="right", va="bottom")
ax.set_xticks(PITCHES)
ax.set_xlabel("Lattice pitch (nm)")
ax.set_ylabel("Information density (bits/µm²)")
ax.legend(fontsize=8.5, loc="upper right")
ax.set_title("APSK-16 stays ahead of the Voxel-Wedge at 5%, 10% and 20% writing variability",
             loc="left", fontsize=11, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig7_sensitivity.png"), dpi=200)
plt.close(fig)
summ["sensitivity"] = sens
summ["spread"] = json.load(open(os.path.join(R, "spread.json")))
if os.path.exists(os.path.join(R, "samm_sensitivity.json")):
    summ["samm_sensitivity"] = json.load(open(os.path.join(R, "samm_sensitivity.json")))
json.dump(summ, open(os.path.join(R, "summary.json"), "w"), indent=1)
print("figures ok")
