"""Shareable figures for the rebound adjustments (series style of 09_figures.py). Every number in titles,
subtitles and labels is read from 13_rebound.py / 14_rebound_fair.py outputs.

Outputs: ../figures/fig7_rebound_waterfall.png, ../figures/fig8_rebound_comparison.png, ../figures/fig9_rebound_tornado.png
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
fig9 = importlib.import_module("09_figures")
ROOT = Path(__file__).resolve().parent.parent
D, FIG = ROOT / "data", ROOT / "figures"
NOTE = "Ranges are scenario cases (low and high parameter values), not a probability interval."
SRC = ("Data: github.com/hausfath/wind-solar-counterfactual (wind, solar and geothermal held at 2005). Fuel markets: CEDS v2025-03-18 combustion CO₂\n"
       "by sector; elasticities from Burke & Liao 2015, Hausman & Kellogg 2015, Prest et al. 2024; cycling from Kaffine et al. 2020.")
CRIT_CENTRAL, CRIT_LO, CRIT_HI = 16.0, 4.0, 17.0       # critique's stated estimates (Gt CO2, 2006-2025), as posted


def load():
    S = pd.read_csv(D / "rebound_scenarios.csv").set_index("scenario")
    T = pd.read_csv(D / "fair" / "rebound_dT.csv")
    return S, T


def dT(T, name, y=2050):
    return T[(T.scenario == name) & (T.year == y)].p50.iloc[0]


def waterfall(S, T):
    head, cen = S.loc["Headline"].cum_Gt, S.loc["Central (all channels)"].cum_Gt
    lo, hi = S.loc["All low"].cum_Gt, S.loc["All high"].cum_Gt
    steps = ["1 cycling", "2 + electricity rebound", "3 + fuel-market rebound"]
    labs = ["Cycling\npenalty", "Electricity-\ndemand rebound", "Fuel-market\nrebound"]
    prev = [head] + [S.loc[s].cum_Gt for s in steps[:-1]]
    t50h, t50c = dT(T, "Headline"), dT(T, "Central (all channels)")
    title = f"Allowing for rebound effects, wind and solar still avoided about {cen:.0f} billion tonnes of CO₂"
    sub = (f"Our headline estimate of {head:.1f} Gt avoided over 2006–2025 falls to {cen:.1f} Gt ({100 * cen / head:.0f}%) after three adjustments; "
           f"scenarios span {hi:.1f}–{lo:.1f} Gt.\n"
           f"Avoided warming by 2050: from {t50h:.4f} to {t50c:.4f} °C (FaIR median). The all-high case adds an EU ETS waterbed and whole-market coal demand.")
    fig9.setup()
    f = fig9.frame(title, sub, NOTE + "\n" + SRC, tsize=27)
    ax = f.add_axes([0.07, 0.17, 0.88, 0.58]); fig9.style_ax(ax)
    x = np.arange(len(steps) + 2)
    ax.bar(0, head, color=fig9.OBS, width=0.62)
    ax.text(0, head + 0.5, f"{head:.1f}", ha="center", va="bottom", fontsize=17, fontweight="bold", color=fig9.INK)
    for i, (s, p) in enumerate(zip(steps, prev), start=1):
        v = S.loc[s].cum_Gt
        ax.bar(i, p - v, bottom=v, color=fig9.CF, width=0.62)
        ax.plot([i - 1 + 0.31, i - 0.31], [p, p], color=fig9.INK3, lw=1, ls=":")
        a, b = S.loc[f"{s}|low"].cum_Gt, S.loc[f"{s}|high"].cum_Gt
        ax.errorbar(i, v, yerr=[[v - b], [a - v]], color=fig9.INK, capsize=7, lw=1.6)
        ax.text(i + 0.36, (p + v) / 2, f"−{p - v:.1f}", ha="left", va="center", fontsize=16, fontweight="bold", color=fig9.CF,
                bbox=dict(facecolor=fig9.SURFACE, edgecolor="none", pad=1.5))
        rl = "0" if abs(p - a) < 0.05 else (f"+{a - p:.1f}" if p - a < 0 else f"−{p - a:.1f}")
        ax.text(i, max(p, a) + 0.5, f"range {rl} to −{p - b:.1f}", ha="center", va="bottom", fontsize=12.5, color=fig9.INK2)
    n = len(steps) + 1
    ax.plot([n - 1 + 0.31, n - 0.31], [cen, cen], color=fig9.INK3, lw=1, ls=":")
    ax.bar(n, cen, color=fig9.CO2C, width=0.62)
    ax.errorbar(n, cen, yerr=[[cen - hi], [lo - cen]], color=fig9.INK, capsize=7, lw=1.6)
    ax.text(n + 0.36, cen, f"{cen:.1f}", ha="left", va="center", fontsize=17, fontweight="bold", color=fig9.CO2C)
    ax.text(n, lo + 0.5, f"all-low to all-high\n{hi:.1f} to {lo:.1f}", ha="center", va="bottom", fontsize=12.5, color=fig9.INK2)
    ax.set_xticks(x)
    ax.set_xticklabels(["Headline\nestimate"] + labs + ["Adjusted\n(central)"], fontsize=15)
    ax.set_xlim(-0.6, n + 0.8)
    ax.set_ylim(0, head * 1.13)
    ax.set_ylabel("Avoided CO₂, 2006–2025 (Gt)", fontsize=15)
    f.savefig(FIG / "fig7_rebound_waterfall.png", dpi=200, facecolor=fig9.SURFACE)


def comparison(S, T):
    head, cen = S.loc["Headline"].cum_Gt, S.loc["Central (all channels)"].cum_Gt
    lo, hi = S.loc["All low"].cum_Gt, S.loc["All high"].cum_Gt
    alt = S.loc["Alternative: whole-market coal elasticity (s = 1 for coal)"].cum_Gt
    crit = S.loc["Critic's construction (integrated markets, s = 1)"].cum_Gt
    rows = [  # label, point, (lo, hi) or None, colour, note
        ("Original estimate\n(no rebound)", head, None, fig9.OBS, "Demand held at observed levels; displacement 1:1 by construction"),
        ("This assessment", cen, (hi, lo), fig9.CO2C, "Cycling, electricity demand, fuel markets by region and buyer type (high case adds EU ETS waterbed)"),
        ("Alternative: whole-market\ncoal elasticity", alt, None, fig9.CO2C, "Burke & Liao's elasticity of total coal use applied to the whole coal market (conservative reading)"),
        ("Critique's price rebound\n(our reproduction)", crit, None, fig9.CF, f"One global market per fuel, whole market rebounds; critique states ~{CRIT_CENTRAL:.0f} Gt"),
        ("Critique's combined\nrange", None, (CRIT_LO, CRIT_HI), fig9.CF, "Low end combines cross-country displacement ratios below 1 with a separate price rebound"),
    ]
    title = f"Rebound effects cut the CO₂ avoided by wind and solar by about {100 * (1 - cen / head):.0f}% in our central case"
    sub = (f"Avoided CO₂ over 2006–2025 under different treatments of rebound. Our central estimate is {cen:.1f} Gt; reading the coal demand elasticity\n"
           f"as whole-market gives {alt:.1f} Gt, near the critique's price-rebound case (~{CRIT_CENTRAL:.0f} Gt). The critique's {CRIT_LO:.0f} Gt low end relies on displacement ratios.")
    fig9.setup()
    f = fig9.frame(title, sub, NOTE + "\n" + SRC, tsize=27)
    ax = f.add_axes([0.21, 0.17, 0.75, 0.56]); fig9.style_ax(ax)
    ax.grid(axis="y", visible=False); ax.grid(axis="x", color=fig9.GRID, lw=1)
    yy = np.arange(len(rows))[::-1]
    for y, (lab, pt, rng, col, note) in zip(yy, rows):
        if rng:
            ax.plot(rng, [y, y], color=col, lw=9, alpha=0.35, solid_capstyle="round")
            ax.text(rng[0] - 0.3, y, f"{rng[0]:.1f}" if rng[0] % 1 else f"{rng[0]:.0f}", ha="right", va="center", fontsize=14, color=fig9.INK2)
            ax.text(rng[1] + 0.3, y, f"{rng[1]:.1f}" if rng[1] % 1 else f"{rng[1]:.0f}", ha="left", va="center", fontsize=14, color=fig9.INK2)
        if pt is not None:
            ax.scatter([pt], [y], s=260, color=col, zorder=5, edgecolor=fig9.SURFACE, linewidth=2)
            ax.text(pt, y + 0.27, f"{pt:.1f}", ha="center", va="bottom", fontsize=15, fontweight="bold", color=col)
        ax.text(0.3, y - 0.36, note, ha="left", va="center", fontsize=12, color=fig9.INK3)
    ax.set_yticks(yy); ax.set_yticklabels([r[0] for r in rows], fontsize=15)
    ax.set_xlim(0, 25.5); ax.set_ylim(-0.75, len(rows) - 0.4)
    ax.set_xlabel("Avoided CO₂, 2006–2025 (Gt)", fontsize=15)
    f.savefig(FIG / "fig8_rebound_comparison.png", dpi=200, facecolor=fig9.SURFACE)


def tornado(S):
    cen = S.loc["Central (all channels)"].cum_Gt
    P = [  # label (range shown low / central / high adjustment), OAT key or (low-case, high-case) scenario names
        ("Cycling penalty at 10% wind+solar share (3.8 / 6.5 / 9%)", "Cycling"),
        ("Electricity price change (+1% / −1% / −3%) & elasticity", "Electricity-demand rebound"),
        ("Electrification share of extra demand (40% / 0 / 0)", "Electrification netting"),
        ("China & India coal supply elasticity (∞ / 3 / 1.55)", "China & India coal supply"),
        ("US & rest-of-world coal supply elasticity (3 / 1.55 / 0.8)", "US & RoW coal supply"),
        ("Non-power coal demand elasticity (China −0.2 / −0.3 / −0.5)", "Coal demand elasticity"),
        ("Gas supply elasticity (1.5 / 0.81 / 0.5)", "Gas supply"),
        ("Gas demand elasticities (industry −0.3 / −0.45 / −0.6)", "Gas demand elasticity"),
        ("EU ETS waterbed (0 / 0 / 20–60%)", "EU ETS waterbed"),
        ("Oil supply elasticity (1.0 / 0.42 / 0.42)", "Oil market"),
        ("Steel & heat-plant demand elasticity (0 / −0.1 / −0.1)", "Steel & heat-plant elasticity"),
        ("Share of extra coal imported (China 10 / 15 / 20%)", "Coal import margin"),
        ("Gas oil-indexed contract era (f = 0 / f = 0 / ignored)", "Gas contract era"),
        ("Whole-market coal elasticity (alternative)", (None, "Alternative: whole-market coal elasticity (s = 1 for coal)")),
        ("Linear small-change formula (alternative)", (None, "Alternative: linear (small-change) fuel-market formula")),
    ]
    rows = []
    for lab, key in P:
        if isinstance(key, tuple):
            a = S.loc[key[0]].cum_Gt if key[0] else cen
            b = S.loc[key[1]].cum_Gt if key[1] else cen
        else:
            a, b = S.loc[f"{key}|low"].cum_Gt, S.loc[f"{key}|high"].cum_Gt
        rows.append((lab, a, b))
    rows.sort(key=lambda r: abs(r[1] - r[2]))
    top = rows[-1]
    big = [r[0] for r in rows[::-1][:2]]
    assert big[0].startswith("Whole-market coal") and big[1].startswith("Electricity price"), big
    title = "How coal demand is modelled and the electricity rebound drive the uncertainty most"
    sub = (f"Avoided CO₂ over 2006–2025 when one assumption at a time is moved to its low or high value, with all others at central ({cen:.1f} Gt).\n"
           f"Values in brackets: smallest / central / largest adjustment. Largest single swing: {top[0].split(' (')[0].lower()}.")
    fig9.setup()
    f = fig9.frame(title, sub, NOTE + "\n" + SRC, tsize=27)
    ax = f.add_axes([0.40, 0.15, 0.56, 0.60]); fig9.style_ax(ax)
    ax.grid(axis="y", visible=False); ax.grid(axis="x", color=fig9.GRID, lw=1)
    for y, (lab, a, b) in enumerate(rows):
        for v, col in ((a, fig9.CO2C), (b, fig9.CF)):
            if abs(v - cen) > 1e-6:
                ax.barh(y, v - cen, left=cen, color=col, height=0.62)
                ax.text(v + (0.12 if v > cen else -0.12), y, f"{v:.1f}", ha="left" if v > cen else "right", va="center", fontsize=12.5, color=fig9.INK2)
    ax.axvline(cen, color=fig9.INK, lw=1.4)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows], fontsize=13)
    lo_, hi_ = min(min(r[1], r[2]) for r in rows), max(max(r[1], r[2]) for r in rows)
    ax.set_xlim(lo_ - 0.9, hi_ + 0.7); ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("Avoided CO₂, 2006–2025 (Gt)", fontsize=15)
    ax.text(cen + 0.08, len(rows) - 0.55, f"central {cen:.1f}", fontsize=13, color=fig9.INK, va="bottom")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=fig9.CO2C, label="smaller adjustment"), Patch(color=fig9.CF, label="larger adjustment")],
              loc="lower left", frameon=False, fontsize=13)
    f.savefig(FIG / "fig9_rebound_tornado.png", dpi=200, facecolor=fig9.SURFACE)


def main():
    S, T = load()
    waterfall(S, T); comparison(S, T); tornado(S)
    print("wrote fig7-fig9")


if __name__ == "__main__":
    main()
