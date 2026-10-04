"""China's electricity generation mix (% of generation), 1985-2025. Social-media figure.

Data: Our World in Data share-elec-by-source (Energy Institute before 2000, Ember from 2000), the same input as
00_power_mix.py. Shares are renormalised to 100% (pre-2000 rows carry a small residual). Every number in the
title and subtitle is computed here.

Output: ../figures/fig6_china_mix.png
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
fig9 = importlib.import_module("09_figures")
ROOT = Path(__file__).resolve().parent.parent
Y0, Y1 = 1985, 2025

# bottom -> top; colours as in 00_power_mix.py (CVD-checked there)
BANDS = [("Coal", ["coal"], "#3f3a37"), ("Oil", ["oil"], "#8a5a38"), ("Gas", ["gas"], "#d18f4a"),
         ("Nuclear", ["nuclear"], "#a566c9"), ("Hydro", ["hydro"], "#1a5da6"),
         ("Bioenergy & other", ["bioenergy", "other_renewables_excluding_bioenergy"], "#3f9142"),
         ("Wind", ["wind"], "#58b7e8"), ("Solar", ["solar"], "#f0a919")]


def last_cross(a, b):
    """first year of the final continuous period with a > b"""
    ys = sorted(a.index)
    for y in ys:
        if all(a[z] > b[z] for z in ys if z >= y):
            return y
    return None


def main():
    d = pd.read_csv(ROOT / "data" / "inputs" / "owid" / "share_elec_by_source.csv")
    c = d[d.entity == "China"].set_index("year").sort_index().loc[Y0:Y1].fillna(0)
    sh = pd.DataFrame({n: c[[f"{k}_share_of_electricity__pct" for k in ks]].sum(axis=1) for n, ks, _ in BANDS})
    sh = sh.div(sh.sum(axis=1), axis=0) * 100
    coal, ws = sh.Coal, sh.Wind + sh.Solar
    peak_y, peak = int(coal.idxmax()), coal.max()
    assert coal.idxmin() == Y1, "coal-share 'lowest' claim requires the minimum to be the last year"
    ws15 = ws[2015]
    x_hydro, x_wind = last_cross(ws, sh.Hydro), last_cross(sh.Solar, sh.Wind)
    title = f"Coal's share of China's electricity has fallen from {peak:.0f}% to {coal[Y1]:.0f}%"
    sub = (f"Coal peaked at {peak:.0f}% of generation in {peak_y}; in {Y1} it was {coal[Y1]:.0f}%, the lowest since at least {Y0}.\n"
           f"Wind and solar rose from {ws15:.0f}% in 2015 to {ws[Y1]:.0f}% in {Y1}, passing hydro in {x_hydro}"
           + (f", and solar overtook wind in {x_wind}." if x_wind == Y1 else f"; solar has led wind since {x_wind}."))
    src = ("Data: Ember yearly electricity data (2000–2025) and Energy Institute Statistical Review (1985–1999), via Our World in Data.\n"
           "Share of electricity generation. 'Bioenergy & other' includes geothermal and other renewables.")
    print(title); print(sub)
    fig9.setup()
    f = fig9.frame(title, sub, src, tsize=30)
    ax = f.add_axes([0.06, 0.13, 0.72, 0.60]); fig9.style_ax(ax)
    x = sh.index.values
    cum = np.zeros(len(x))
    mids = {}
    for n, _, col in BANDS:
        top = cum + sh[n].values
        ax.fill_between(x, cum, top, color=col, lw=0)
        ax.plot(x, top, color=fig9.SURFACE, lw=1.2)   # thin surface gap between bands
        mids[n] = (cum[-1] + top[-1]) / 2
        cum = top
    ax.set_xlim(Y0, Y1); ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100]); ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xticks([1985, 1995, 2005, 2015, 2025])
    ax.grid(False)
    # direct labels at the right edge, spread so thin bands don't collide (min 3.4 points apart)
    order = [n for n, _, _ in BANDS]
    ys = [mids[n] for n in order]
    for _ in range(50):
        for i in range(1, len(ys)):
            if ys[i] - ys[i - 1] < 4.2:
                ys[i] = ys[i - 1] + 4.2
        if ys[-1] > 99:
            ys[-1] = 99
            for i in range(len(ys) - 2, -1, -1):
                if ys[i + 1] - ys[i] < 4.2:
                    ys[i] = ys[i + 1] - 4.2
    for (n, _, col), yl in zip(BANDS, ys):
        ax.plot([Y1 + 0.15, Y1 + 0.55], [mids[n], yl], color=col, lw=1.2, clip_on=False)
        ax.text(Y1 + 0.7, yl, f"{n}  {sh[n][Y1]:.1f}%", va="center", fontsize=14, color=fig9.INK, clip_on=False)
    # in-band annotations for the big bands
    ax.text(1990, coal[1990] / 2, "COAL", fontsize=26, fontweight="bold", color="white", alpha=0.9, va="center")
    f.savefig(ROOT / "figures" / "fig6_china_mix.png", dpi=200, facecolor=fig9.SURFACE)
    print("wrote", ROOT / "figures" / "fig6_china_mix.png")


if __name__ == "__main__":
    main()
