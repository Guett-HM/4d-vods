"""One visual style for every figure of the project.

Colours: the categorical slots are used in a fixed order (slot 1 blue, 2 orange, 3 aqua,
4 yellow) and the same entity keeps the same colour in every figure (Voxel-Wedge = slot 1,
APSK-16 = slot 2). The four slots pass a colour-vision-deficiency check (protan, deutan and
tritan separation of adjacent slots >= 9 Delta E); slots 3 and 4 have low contrast against
the background, so every series also carries a marker, a legend entry, and its numbers in
figures/data/*.csv.

Every figure is saved three times: PNG for the web, PDF (vector) for print, and a CSV of the
plotted values so that nobody has to read numbers off a chart.
"""
import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
DATA = os.path.join(FIG, "data")

S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"     # categorical slots 1-4
ERR = "#e34948"                                                  # decoding errors in illustrations
INK, INK2, GRID, SURF, EDGE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#c3c2b7"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10.5, "axes.edgecolor": INK2,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "figure.facecolor": SURF,
    "axes.facecolor": SURF, "savefig.facecolor": SURF, "legend.frameon": False,
    "text.color": INK, "pdf.fonttype": 42, "svg.fonttype": "none",
})
PDF_META = {"Creator": "4D-VODS sim/plotstyle.py", "Author": "H. Guettal", "CreationDate": None}


def title(ax, text, size=11.5):
    ax.set_title(text, loc="left", fontsize=size, color=INK)


def save(fig, name, header=None, rows=None, dpi=200, **kw):
    """figures/<name>.png + figures/<name>.pdf (+ figures/data/<name>.csv when rows are given)."""
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(os.path.join(FIG, f"{name}.png"), dpi=dpi, **kw)
    fig.savefig(os.path.join(FIG, f"{name}.pdf"), metadata=PDF_META, **kw)
    plt.close(fig)
    if rows is not None:
        os.makedirs(DATA, exist_ok=True)
        with open(os.path.join(DATA, f"{name}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for r in rows:
                w.writerow([f"{v:.6g}" if isinstance(v, float) else v for v in r])
