"""Shared matplotlib style for the reports: readable in an IEEE two-column PDF, colour-blind safe.

Usage in an analysis script:
    import sys; sys.path.insert(0, ".claude/skills/results-analysis/scripts")
    from plot_style import apply_style, new_figure, savefig, color_for, plot_median_iqr
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Okabe–Ito palette (colour-blind safe), fixed order so a method keeps its colour across figures
OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
_assigned = {}

COLUMN_WIDTH_IN = 3.5   # IEEE single column
TEXT_WIDTH_IN = 7.16    # IEEE double column (figure*)


def apply_style():
    plt.rcParams.update({
        "font.family": "serif", "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8,
        "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "lines.linewidth": 1.2, "lines.markersize": 4, "errorbar.capsize": 2,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42,
    })


def new_figure(width="column", height=2.4):
    apply_style()
    w = COLUMN_WIDTH_IN if width == "column" else TEXT_WIDTH_IN
    return plt.subplots(figsize=(w, height))


def color_for(name):
    if name not in _assigned:
        i = len(_assigned)
        _assigned[name] = (OKABE_ITO[i % len(OKABE_ITO)], MARKERS[i % len(MARKERS)])
    return _assigned[name]


def plot_median_iqr(ax, x, median, q1, q3, label):
    """Median line with IQR as asymmetric error bars."""
    c, m = color_for(label)
    yerr = [[md - lo for md, lo in zip(median, q1)], [hi - md for md, hi in zip(median, q3)]]
    ax.errorbar(x, median, yerr=yerr, label=label, color=c, marker=m)


def savefig(fig, path_without_ext):
    """Save as PDF (for LaTeX) and PNG (for README/preview)."""
    p = Path(path_without_ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p.with_suffix(".pdf"))
    fig.savefig(p.with_suffix(".png"), dpi=200)
    plt.close(fig)
    return p.with_suffix(".pdf")
