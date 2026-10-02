"""
Global share of electricity generation by source, 1985-2025(+2026 est.)

Data: Our World in Data "share-elec-by-source" grapher dataset, which combines
Energy Institute Statistical Review of World Energy (pre-2000) and Ember
yearly electricity data (2000 onward) for the World aggregate.
Download: https://ourworldindata.org/grapher/share-elec-by-source.csv?useColumnShortNames=true

All headline numbers in titles/annotations are computed from the data, not hardcoded.

Output: ../figures/power_mix_*.png (3200x1800, for social media). The blog's first figure is
power_mix_lines_1985_2026est.png; the 2026 estimate (build_2026_estimate) is also used by the counterfactual write-up.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ---------------------------------------------------------------- config

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FIGDIR = ROOT / "figures"
CSV = ROOT / "data" / "inputs" / "owid" / "share_elec_by_source.csv"
YR0, YR1 = 1985, 2025

# 2026 estimate: apply IEA "Electricity 2026" growth outlook to Ember 2025 data.
# Rates hand-verified from https://www.iea.org/reports/electricity-2026/supply
# (fetched 2026-08-10): coal -0.9%/yr avg 2026-30; gas +2.6%/yr; nuclear +2.8%/yr;
# wind ~+10%/yr; solar >+600 TWh/yr (~+22% on 2025's ~2,780 TWh); renewables
# total ~+1,050 TWh/yr. Hydro (+2.5%) and oil (-2%, the 2025 actual) are our
# assumptions, not IEA-stated; both bands are small so shares shift <0.2 pp
# under reasonable alternatives. Shares renormalized after growth is applied,
# so only relative growth matters (IEA demand +3.6%/yr implied total checks
# to within 0.3% of the summed sources).
GROWTH_2026 = {
    "Coal": -0.009, "Gas": 0.026, "Oil": -0.02, "Nuclear": 0.028,
    "Hydro": 0.025, "Other renewables": 0.02, "Wind": 0.10, "Solar": 0.22,
}
USE_2026 = True


def build_2026_estimate(shares):
    last = shares.iloc[-1]
    grown = {n: last[n] * (1 + GROWTH_2026[n]) for n in shares.columns}
    tot = sum(grown.values())
    return {n: v / tot * 100 for n, v in grown.items()}

# Stack order bottom->top. Adjacency-order palette validated for CVD
# separation (worst adjacent pair dE 9.1 protan) and normal-vision floor
# (worst 17.5). Coal near-black and solar bright yellow are deliberate
# semantic choices; every band gets a direct label as the relief channel.
GROUPS = [
    # name, column(s), color, label color for inline text
    ("Oil",        ["oil_share_of_electricity__pct"],                 "#8a5a38"),
    ("Coal",       ["coal_share_of_electricity__pct"],                "#3f3a37"),
    ("Gas",        ["gas_share_of_electricity__pct"],                 "#d18f4a"),
    ("Nuclear",    ["nuclear_share_of_electricity__pct"],             "#a566c9"),
    ("Hydro",      ["hydro_share_of_electricity__pct"],               "#1a5da6"),
    ("Other renewables", ["bioenergy_share_of_electricity__pct",
                    "other_renewables_excluding_bioenergy_share_of_electricity__pct"], "#3f9142"),
    ("Wind",       ["wind_share_of_electricity__pct"],                "#58b7e8"),
    ("Solar",      ["solar_share_of_electricity__pct"],               "#f0a919"),
]
FOSSIL = {"Oil", "Coal", "Gas"}

SURFACE = "#fcfcfb"
INK     = "#1a1a19"
INK2    = "#5f5c58"
INK3    = "#8a8680"


def load_data():
    """Full World series (1900-2025). The chart plots YR0 onward; the full
    history (pre-1965 from the Pinto et al. 2023 reconstruction, via OWID)
    is kept so 'lowest since' claims can be computed rather than assumed."""
    df = pd.read_csv(CSV)
    w = df[df["entity"] == "World"].set_index("year").sort_index()
    w = w.loc[:YR1]
    shares = pd.DataFrame(index=w.index)
    for name, cols, _ in GROUPS:
        shares[name] = w[cols].sum(axis=1)
    # renormalize to 100 (pre-2000 EI years sum to ~99.4 due to rounding/residual)
    tot = shares.sum(axis=1)
    assert (tot > 98.5).all() and (tot < 101.5).all(), f"share sums off: {tot.describe()}"
    shares = shares.div(tot, axis=0) * 100.0
    return shares


def key_stats(shares):
    s = {}
    fossil = shares[[g for g in shares.columns if g in FOSSIL]].sum(axis=1)
    s["fossil_first"] = fossil.loc[YR0]
    s["fossil_last"] = fossil.iloc[-1]
    s["fossil_last_is_min"] = fossil.iloc[-1] == fossil.loc[YR0:].min()
    # last year (full history) with a fossil share below the latest value;
    # phrased as "about N years" since the exact 1930s year is sensitive to
    # reconstruction uncertainty (1932/1933/1935 all sit just below 2025)
    below = fossil.loc[:YR1 - 1][fossil.loc[:YR1 - 1] < fossil.iloc[-1]]
    s["fossil_low_since"] = int(below.index.max()) if len(below) else None
    s["fossil_low_years"] = (YR1 - s["fossil_low_since"]
                             if s["fossil_low_since"] else None)
    s["clean_last"] = 100 - fossil.iloc[-1]
    s["wind_solar_last"] = shares["Wind"].iloc[-1] + shares["Solar"].iloc[-1]
    solar_gt_wind = shares.index[shares["Solar"] > shares["Wind"]]
    s["solar_passes_wind"] = int(solar_gt_wind[0]) if len(solar_gt_wind) else None
    s["fossil_series"] = fossil.loc[YR0:]
    return s


def setup_fonts():
    for f in ["Helvetica Neue", "Arial", "DejaVu Sans"]:
        if any(f == fm.FontProperties(fname=p).get_name() for p in []) or f in {
            x.name for x in fm.fontManager.ttflist}:
            plt.rcParams["font.family"] = f
            break


def make_plot(shares, stats, est_2026=None):
    shares = shares.loc[YR0:YR1]
    setup_fonts()
    fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    yrs = shares.index.values
    names = [g[0] for g in GROUPS]
    colors = {g[0]: g[2] for g in GROUPS}
    data = np.vstack([shares[n].values for n in names])

    ax.stackplot(yrs, data, colors=[colors[n] for n in names],
                 edgecolor=SURFACE, linewidth=1.2)

    # optional 2026 estimated bar as a hatched extension
    x_end = yrs[-1]
    if est_2026 is not None:
        x_est0, x_est1 = YR1 + 0.35, YR1 + 1.35
        bottom = 0.0
        for n in names:
            v = est_2026[n]
            ax.fill_between([x_est0, x_est1], bottom, bottom + v,
                            color=colors[n], alpha=0.75, hatch="//",
                            edgecolor=SURFACE, linewidth=1.2)
            bottom += v
        x_end = x_est1
        ax.text((x_est0 + x_est1) / 2, 101.5, "2026\nest.", fontsize=11.5,
                color=INK2, ha="center", va="bottom", linespacing=1.1)

    # fossil/clean divider: heavy line at top of the fossil block
    fossil = stats["fossil_series"]
    ax.plot(yrs, fossil.values, color=SURFACE, lw=4.5, solid_capstyle="round")
    ax.plot(yrs, fossil.values, color=INK, lw=1.8, solid_capstyle="round")

    # in-band block labels (computed values), centered inside coal / hydro bands
    coal_mid = (shares.loc[1993, "Oil"] + shares.loc[1993, "Oil"]
                + shares.loc[1993, "Coal"]) / 2
    hydro_bot = fossil.loc[1993] + shares.loc[1993, "Nuclear"]
    hydro_mid = hydro_bot + shares.loc[1993, "Hydro"] / 2
    ax.text(1993, coal_mid + 1.5, "FOSSIL FUELS",
            fontsize=26, fontweight="bold", color="white", alpha=0.92)
    ax.text(1993, coal_mid - 4.0,
            f"{stats['fossil_first']:.0f}% of world power in {YR0}, "
            f"{stats['fossil_last']:.0f}% in {YR1}",
            fontsize=15, color="white", alpha=0.85)
    ax.text(1993, hydro_mid + 1.5, "CLEAN POWER",
            fontsize=26, fontweight="bold", color="white", alpha=0.92)
    ax.text(1993, hydro_mid - 4.0,
            f"{100 - stats['fossil_first']:.0f}% in {YR0}, "
            f"{stats['clean_last']:.0f}% in {YR1}",
            fontsize=15, color="white", alpha=0.85)

    # right-edge direct labels: name + latest share, collision-resolved
    last = shares.iloc[-1] if est_2026 is None else pd.Series(est_2026)
    cum = 0.0
    positions = []
    for n in names:
        v = last[n]
        positions.append((n, cum + v / 2, v))
        cum += v
    # enforce minimum vertical gap of 3.4 pts of axis units, bottom-up
    MIN_GAP = 3.6
    adj = []
    for i, (n, y, v) in enumerate(positions):
        if adj and y - adj[-1][1] < MIN_GAP:
            y = adj[-1][1] + MIN_GAP
        adj.append((n, y, v))
    # top-down clamp
    for i in range(len(adj) - 2, -1, -1):
        n, y, v = adj[i]
        if adj[i + 1][1] - y < MIN_GAP:
            adj[i] = (n, adj[i + 1][1] - MIN_GAP, v)
    for n, y, v in adj:
        ax.annotate(f"{n}  {v:.1f}%",
                    xy=(x_end, y), xytext=(14, 0), textcoords="offset points",
                    fontsize=14.5, fontweight="bold", color=INK,
                    va="center", ha="left",
                    annotation_clip=False)
        # leader dot in series color
        ax.annotate("●", xy=(x_end, y), xytext=(4, 0),
                    textcoords="offset points", fontsize=9, color=colors[n],
                    va="center", ha="left", annotation_clip=False)

    # axes cosmetics
    ax.set_xlim(YR0, x_end)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels([f"{t}%" for t in [0, 20, 40, 60, 80, 100]],
                       fontsize=14, color=INK2)
    xticks = [1985, 1995, 2005, 2015, 2025]
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(t) for t in xticks], fontsize=14, color=INK2)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    # title block (computed claims)
    sub_bits = []
    if stats["fossil_last_is_min"] and stats["fossil_low_years"]:
        n = int(round(stats["fossil_low_years"] / 5) * 5)
        sub_bits.append(
            f"Fossil fuels supplied {stats['fossil_last']:.0f}% of global electricity in {YR1}, "
            f"their lowest share in about {n} years.")
    if stats["solar_passes_wind"] == YR1:
        sub_bits.append(f"In {YR1}, solar passed wind for the first time.")
    if (est_2026 is not None and est_2026["Solar"] > est_2026["Nuclear"]
            and shares["Solar"].iloc[-1] < shares["Nuclear"].iloc[-1]):
        sub_bits.append("IEA forecasts imply it passes nuclear in 2026.")
    fig.text(0.045, 0.955, "The changing shape of global electricity",
             fontsize=30, fontweight="bold", color=INK, ha="left", va="top")
    if len(sub_bits) > 2:
        sub = sub_bits[0] + "\n" + "  ".join(sub_bits[1:])
    else:
        sub = "  ".join(sub_bits)
    fig.text(0.045, 0.905, sub, fontsize=16.5, color=INK2, ha="left",
             va="top", linespacing=1.45)

    src = ("Data: Ember Yearly Electricity Data (2000–2025) and Energy Institute "
           "Statistical Review (1985–1999), compiled by Our World in Data.")
    y_src = 0.022
    if est_2026 is not None:
        y_src = 0.040
        fig.text(0.045, 0.016,
                 "2026: estimated by applying the IEA Electricity 2026 "
                 "growth outlook by source to the 2025 data.",
                 fontsize=11.5, color=INK3, ha="left")
    fig.text(0.045, y_src, src, fontsize=11.5, color=INK3, ha="left")
    fig.text(0.955, 0.016 if est_2026 is not None else y_src,
             "Zeke Hausfather · The Climate Brink",
             fontsize=11.5, color=INK3, ha="right")

    fig.subplots_adjust(left=0.045, right=0.845, top=0.83, bottom=0.09)
    out = "power_mix_1985_2025.png" if est_2026 is None else "power_mix_1985_2026est.png"
    fig.savefig(FIGDIR / out, dpi=200, facecolor=SURFACE)
    print(f"saved {out}")
    return out


# ------------------------------------------------------- line-chart variant

# 6-series semantic palette for the unstacked line chart. All-pairs CVD
# validated to worst 6.3 (protan, gas vs non-hydro renewables; WARN band,
# mitigated by direct end labels on every line and the annotated crossing).
# Worst normal-vision pair is oil vs gas (14.2), which never cross.
LINE_GROUPS = [
    ("Coal",    ["Coal"],    "#3f3a37"),
    ("Gas",     ["Gas"],     "#b5732e"),
    ("Oil",     ["Oil"],     "#7d5230"),
    ("Nuclear", ["Nuclear"], "#bb58b8"),
    ("Hydro",   ["Hydro"],   "#1a5da6"),
    ("Wind, solar & other\nrenewables", ["Wind", "Solar", "Other renewables"],
     "#0e8a63"),
]
NHR = "Wind, solar & other\nrenewables"


def line_series(shares, est_2026=None):
    ls = pd.DataFrame(index=shares.index)
    for name, cols, _ in LINE_GROUPS:
        ls[name] = shares[cols].sum(axis=1)
    est = None
    if est_2026 is not None:
        est = {name: sum(est_2026[c] for c in cols)
               for name, cols, _ in LINE_GROUPS}
    return ls, est


def line_stats(ls, est):
    s = {}
    s["coal_last_is_min"] = ls["Coal"].iloc[-1] == ls["Coal"].min()
    s["coal_last"] = ls["Coal"].iloc[-1]
    # "more than a century" requires: no year in the full record beats the
    # latest value, and the record reaches back at least 100 years. (Ember's
    # own historical series differs pre-1965 but supports >=106 years too.)
    s["coal_century_low"] = (s["coal_last_is_min"]
                             and int(ls.index.min()) <= YR1 - 100)
    for other in ["Nuclear", "Hydro"]:
        # most recent crossing: year after the last year NHR was at or below
        # (nuclear was zero pre-1956, so "first year above" would give 1916)
        below = ls.index[ls[NHR] <= ls[other]]
        if len(below) and ls[NHR].iloc[-1] > ls[other].iloc[-1]:
            s[f"nhr_passes_{other.lower()}"] = int(below.max()) + 1
        else:
            s[f"nhr_passes_{other.lower()}"] = None
    s["nhr_passes_gas_2026"] = (est is not None and ls[NHR].iloc[-1] < ls["Gas"].iloc[-1]
                                and est[NHR] > est["Gas"])
    return s


def make_line_plot(ls, lstats, est=None):
    ls = ls.loc[YR0:YR1]
    setup_fonts()
    fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    yrs = ls.index.values
    colors = {g[0]: g[2] for g in LINE_GROUPS}
    x_end = yrs[-1] if est is None else yrs[-1] + 1

    for n in ls.columns:
        ax.plot(yrs, ls[n], color=colors[n], lw=3, solid_capstyle="round",
                zorder=3)
        if est is not None:
            ax.plot([yrs[-1], yrs[-1] + 1], [ls[n].iloc[-1], est[n]],
                    color=colors[n], lw=3, ls=(0, (2, 1.4)), zorder=3)
            ax.plot([yrs[-1] + 1], [est[n]], marker="o", ms=9, mfc=SURFACE,
                    mec=colors[n], mew=2.2, zorder=4, clip_on=False)
        else:
            ax.plot([yrs[-1]], [ls[n].iloc[-1]], marker="o", ms=9,
                    color=colors[n], mec=SURFACE, mew=1.8, zorder=4,
                    clip_on=False)

    # right-edge labels, collision-resolved (single-line height units)
    last = ls.iloc[-1] if est is None else pd.Series(est)
    order = last.sort_values().index.tolist()
    MIN_GAP = 2.6
    ys = {}
    prev = -99.0
    for n in order:
        y = max(last[n], prev + MIN_GAP)
        # two-line NHR label needs extra clearance above
        if n == NHR:
            y = max(y, prev + MIN_GAP + 0.6)
        ys[n] = y
        prev = y + (1.4 if n == NHR else 0.0)
    for n in ls.columns:
        v = last[n]
        ax.annotate(f"{n}  {v:.1f}%",
                    xy=(x_end, ys[n]), xytext=(16, 0),
                    textcoords="offset points", fontsize=15,
                    fontweight="bold", color=INK, va="center", ha="left",
                    linespacing=1.15, annotation_clip=False)

    ax.set_xlim(YR0, x_end)
    ax.set_ylim(0, 45)
    ax.set_yticks([0, 10, 20, 30, 40])
    ax.set_yticklabels([f"{t}%" for t in [0, 10, 20, 30, 40]],
                       fontsize=14, color=INK2)
    ax.grid(axis="y", color="#e8e6e3", lw=1, zorder=0)
    xticks = [1985, 1995, 2005, 2015, 2025]
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(t) for t in xticks], fontsize=14, color=INK2)
    if est is not None:
        ax.text(yrs[-1] + 1, est["Coal"] + 2.2, "2026\nest.", fontsize=11.5,
                color=INK2, ha="center", va="bottom", linespacing=1.1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    # title block (computed claims)
    sub_bits = []
    if lstats["coal_century_low"]:
        sub_bits.append(
            f"Coal's share of global power, {lstats['coal_last']:.0f}% in {YR1}, "
            f"is its lowest in more than a century.")
    elif lstats["coal_last_is_min"]:
        sub_bits.append(
            f"Coal's share of global power, {lstats['coal_last']:.0f}% in {YR1}, "
            f"is the lowest since at least {YR0}.")
    y_nuc, y_hyd = lstats["nhr_passes_nuclear"], lstats["nhr_passes_hydro"]
    if y_nuc and y_hyd:
        bit = (f"Wind, solar and other renewables passed nuclear in {y_nuc} "
               f"and hydro in {y_hyd}")
        if lstats["nhr_passes_gas_2026"]:
            bit += ", and IEA forecasts imply they pass gas in 2026"
        sub_bits.append(bit + ".")
    fig.text(0.045, 0.955, "The changing shape of global electricity",
             fontsize=30, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.045, 0.905, "\n".join(sub_bits), fontsize=16.5, color=INK2,
             ha="left", va="top", linespacing=1.45)

    src = ("Data: Ember Yearly Electricity Data (2000–2025) and Energy Institute "
           "Statistical Review (1985–1999), compiled by Our World in Data.")
    y_src = 0.022
    if est is not None:
        y_src = 0.040
        fig.text(0.045, 0.016,
                 "2026: estimated by applying the IEA Electricity 2026 "
                 "growth outlook by source to the 2025 data.",
                 fontsize=11.5, color=INK3, ha="left")
    fig.text(0.045, y_src, src, fontsize=11.5, color=INK3, ha="left")
    fig.text(0.955, y_src, "Zeke Hausfather · The Climate Brink",
             fontsize=11.5, color=INK3, ha="right")

    fig.subplots_adjust(left=0.045, right=0.80, top=0.82, bottom=0.09)
    out = ("power_mix_lines_1985_2025.png" if est is None
           else "power_mix_lines_1985_2026est.png")
    fig.savefig(FIGDIR / out, dpi=200, facecolor=SURFACE)
    print(f"saved {out}")
    return out


# --------------------------------------------- absolute (TWh) line variant

TWH_CSV = ROOT / "data" / "inputs" / "owid" / "electricity_prod_by_source.csv"
TWH_COLS = {
    "Oil": ["oil_generation__twh"],
    "Coal": ["coal_generation__twh"],
    "Gas": ["gas_generation__twh"],
    "Nuclear": ["nuclear_generation__twh"],
    "Hydro": ["hydro_generation__twh"],
    "Other renewables": ["bioenergy_stacked_generation__twh",
                         "other_renewables_generation__twh"],
    "Wind": ["wind_generation__twh"],
    "Solar": ["solar_generation__twh"],
}


def load_twh():
    df = pd.read_csv(TWH_CSV)
    w = df[df["entity"] == "World"].set_index("year").sort_index().loc[:YR1]
    twh = pd.DataFrame(index=w.index)
    for name, cols in TWH_COLS.items():
        twh[name] = w[cols].sum(axis=1)
    # cross-check against the shares file (same Ember/EI vintage expected)
    shares = load_data()
    implied = twh.div(twh.sum(axis=1), axis=0) * 100
    err = (implied.loc[YR0:] - shares.loc[YR0:]).abs().max().max()
    assert err < 0.5, f"TWh and share files disagree by up to {err:.2f} pp"
    return twh


def build_2026_estimate_twh(twh):
    last = twh.iloc[-1]
    return {n: last[n] * (1 + GROWTH_2026[n]) for n in twh.columns}


def abs_stats(tl, est):
    s = {}
    tot = tl.sum(axis=1)
    s["growth_ratio"] = tot.iloc[-1] / tot.loc[YR0]
    s["coal_is_largest"] = tl.iloc[-1].idxmax() == "Coal"
    s["coal_peak_year"] = int(tl["Coal"].idxmax())
    s["coal_frac_of_peak"] = tl["Coal"].iloc[-1] / tl["Coal"].max()
    return s


def make_line_plot_abs(tl, astats, lstats, est=None):
    tl = tl.loc[YR0:YR1]
    setup_fonts()
    fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    yrs = tl.index.values
    colors = {g[0]: g[2] for g in LINE_GROUPS}
    x_end = yrs[-1] if est is None else yrs[-1] + 1

    for n in tl.columns:
        ax.plot(yrs, tl[n], color=colors[n], lw=3, solid_capstyle="round",
                zorder=3)
        if est is not None:
            ax.plot([yrs[-1], yrs[-1] + 1], [tl[n].iloc[-1], est[n]],
                    color=colors[n], lw=3, ls=(0, (2, 1.4)), zorder=3)
            ax.plot([yrs[-1] + 1], [est[n]], marker="o", ms=9, mfc=SURFACE,
                    mec=colors[n], mew=2.2, zorder=4, clip_on=False)
        else:
            ax.plot([yrs[-1]], [tl[n].iloc[-1]], marker="o", ms=9,
                    color=colors[n], mec=SURFACE, mew=1.8, zorder=4,
                    clip_on=False)

    YMAX = 11500
    last = tl.iloc[-1] if est is None else pd.Series(est)
    order = last.sort_values().index.tolist()
    MIN_GAP = 660
    ys = {}
    prev = -1e9
    for n in order:
        y = max(last[n], prev + MIN_GAP)
        if n == NHR:
            y = max(y, prev + MIN_GAP + 150)
        ys[n] = y
        prev = y + (360 if n == NHR else 0.0)
    for n in tl.columns:
        ax.annotate(f"{n}  {last[n]:,.0f}",
                    xy=(x_end, ys[n]), xytext=(16, 0),
                    textcoords="offset points", fontsize=15,
                    fontweight="bold", color=INK, va="center", ha="left",
                    linespacing=1.15, annotation_clip=False)

    ax.set_xlim(YR0, x_end)
    ax.set_ylim(0, YMAX)
    yticks = [0, 2000, 4000, 6000, 8000, 10000]
    ax.set_yticks(yticks)
    ax.set_yticklabels(["0", "2,000", "4,000", "6,000", "8,000",
                        "10,000 TWh"], fontsize=14, color=INK2)
    ax.grid(axis="y", color="#e8e6e3", lw=1, zorder=0)
    xticks = [1985, 1995, 2005, 2015, 2025]
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(t) for t in xticks], fontsize=14, color=INK2)
    if est is not None:
        ax.text(yrs[-1] + 1, est["Coal"] + 0.05 * YMAX, "2026\nest.",
                fontsize=11.5, color=INK2, ha="center", va="bottom",
                linespacing=1.1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    sub_bits = []
    if astats["growth_ratio"] >= 3:
        bit = f"World electricity generation has more than tripled since {YR0}"
        if astats["coal_is_largest"] and astats["coal_frac_of_peak"] > 0.98:
            bit += (f", and coal, still the largest source, sits near its "
                    f"{astats['coal_peak_year']} record high.")
        else:
            bit += "."
        sub_bits.append(bit)
    y_nuc, y_hyd = lstats["nhr_passes_nuclear"], lstats["nhr_passes_hydro"]
    if y_nuc and y_hyd:
        bit = (f"But wind, solar and other renewables passed nuclear in {y_nuc} "
               f"and hydro in {y_hyd}")
        if lstats["nhr_passes_gas_2026"]:
            bit += ", and IEA forecasts imply they pass gas in 2026"
        sub_bits.append(bit + ".")
    fig.text(0.045, 0.955, "The changing shape of global electricity",
             fontsize=30, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.045, 0.905, "\n".join(sub_bits), fontsize=16.5, color=INK2,
             ha="left", va="top", linespacing=1.45)

    src = ("Data: Ember Yearly Electricity Data (2000–2025) and Energy Institute "
           "Statistical Review (1985–1999), compiled by Our World in Data.")
    y_src = 0.022
    if est is not None:
        y_src = 0.040
        fig.text(0.045, 0.016,
                 "2026: estimated by applying the IEA Electricity 2026 "
                 "growth outlook by source to the 2025 data.",
                 fontsize=11.5, color=INK3, ha="left")
    fig.text(0.045, y_src, src, fontsize=11.5, color=INK3, ha="left")
    fig.text(0.955, y_src, "Zeke Hausfather · The Climate Brink",
             fontsize=11.5, color=INK3, ha="right")

    fig.subplots_adjust(left=0.088, right=0.80, top=0.82, bottom=0.09)
    out = ("power_mix_twh_1985_2025.png" if est is None
           else "power_mix_twh_1985_2026est.png")
    fig.savefig(FIGDIR / out, dpi=200, facecolor=SURFACE)
    print(f"saved {out}")
    return out


if __name__ == "__main__":
    shares = load_data()
    stats = key_stats(shares)
    for k, v in stats.items():
        if k != "fossil_series":
            print(f"{k}: {v}")
    make_plot(shares, stats, est_2026=None)
    est = None
    if USE_2026:
        est = build_2026_estimate(shares)
        print("2026 est:", {k: round(v, 1) for k, v in est.items()},
              "fossil:", round(sum(est[n] for n in FOSSIL), 1))
        make_plot(shares, stats, est_2026=est)

    ls, lest = line_series(shares, est)
    lstats = line_stats(ls, lest)
    print({k: v for k, v in lstats.items()})
    make_line_plot(ls, lstats, est=None)
    if lest is not None:
        make_line_plot(ls, lstats, est=lest)

    twh = load_twh()
    est_twh = build_2026_estimate_twh(twh) if USE_2026 else None
    tl, tlest = line_series(twh, est_twh)
    astats = abs_stats(tl, tlest)
    # crossing claims recomputed on TWh (same years as shares by construction)
    tlstats = line_stats(tl, tlest)
    print({k: (round(v, 3) if isinstance(v, float) else v)
           for k, v in astats.items()}, {k: v for k, v in tlstats.items()})
    make_line_plot_abs(tl, astats, tlstats, est=None)
    if tlest is not None:
        make_line_plot_abs(tl, astats, tlstats, est=tlest)
