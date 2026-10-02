"""Figures for the no-renewable-growth counterfactual (3200x1800 PNG, social-media sized).

fig1_power_co2.png      observed vs counterfactual power-sector CO2, 2000-2025,
                        F1 headline with the gas-only / coal-only range
fig2_avoided_warming.png  dT 2006-2050: CO2 only vs all effects (5-95% band)
fig3_sensitivities.png  cumulative avoided CO2 and dT(2050) across fill rules
                        and sensitivities (two panels, separate axes)

All numbers in titles and labels are computed from ../data outputs.
Style matches 00_power_mix.py (surface, ink, fonts, byline).
"""
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
D = HERE.parent / "data"
FIG = HERE.parent / "figures"
FIG.mkdir(exist_ok=True)

SURFACE, INK, INK2, INK3, GRID = "#fcfcfb", "#1a1a19", "#5f5c58", "#8a8680", "#e4e2dd"
OBS = "#3f3a37"        # observed (neutral ink, reference series)
CF = "#eb6834"         # counterfactual / all effects (categorical slot 2)
CO2C = "#2a78d6"       # CO2 only (categorical slot 1)
BYLINE = "Zeke Hausfather · The Climate Brink"


def setup():
    names = {x.name for x in fm.fontManager.ttflist}
    for f in ["Helvetica Neue", "Arial", "DejaVu Sans"]:
        if f in names:
            plt.rcParams["font.family"] = f
            break
    plt.rcParams.update({"axes.edgecolor": INK3, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})


def frame(title, subtitle, source, tsize=30):
    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.045, 0.935, title, fontsize=tsize, color=INK, ha="left", va="top")
    fig.text(0.045, 0.855, subtitle, fontsize=16.5, color=INK2, ha="left", va="top", linespacing=1.45)
    fig.text(0.045, 0.03, source, fontsize=11.5, color=INK3, ha="left", va="bottom", linespacing=1.4)
    fig.text(0.955, 0.03, BYLINE, fontsize=12.5, color=INK3, ha="right", va="bottom")
    return fig


def style_ax(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=14, length=0)
    ax.spines["left"].set_visible(False)


# ------------------------------------------------------------------ data

def world_observed_co2():
    """World power-sector combustion CO2 = World Ember TWh by fuel x generation-weighted
    world factor from the country factors (consistent with validation V3)."""
    e = pd.read_csv(D / "ember_subset_2000_2025.csv")
    ef = pd.read_csv(D / "emission_factors.csv")
    ef = ef[ef.species == "CO2"]
    c = e[(e["Area type"] == "Country or economy") & (e.Category == "Electricity generation") & (e.Subcategory == "Fuel")]
    g = c.pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value")
    twh = pd.DataFrame({"coal": g["Coal"], "gas": g["Gas"], "oil": g["Other Fossil"]}).stack().rename("twh")
    twh.index.names = ["iso", "year", "fuel"]
    j = ef.set_index(["iso", "year", "fuel"]).join(twh, how="inner")
    wef = j.groupby(["year", "fuel"]).apply(lambda d: (d.t_per_MWh * d.twh).sum() / d.twh.sum(), include_groups=False)
    w = e[(e.Area == "World") & (e.Category == "Electricity generation") & (e.Subcategory == "Fuel")].pivot_table(index="Year", columns="Variable", values="Value")
    wt = pd.DataFrame({"coal": w["Coal"], "gas": w["Gas"], "oil": w["Other Fossil"]}).stack()
    wt.index.names = ["year", "fuel"]
    return (wt * wef.reindex(wt.index)).groupby("year").sum() / 1e3  # Gt


def delta_co2(rule, techset="wso", comps=("fill", "lifecycle_amortized")):
    d = pd.read_csv(D / "delta_emissions.csv")
    d = d[(d.rule == rule) & (d.techset == techset) & d.component.isin(comps)]
    return d.groupby("year").CO2.sum()


# ------------------------------------------------------------------ fig 1

def fig1():
    obs = world_observed_co2().loc[2000:2025]
    f1, f3, f4 = (delta_co2(r).reindex(obs.index).fillna(0) for r in ("F1", "F3", "F4"))
    cf = obs + f1
    fl = pd.read_csv(D / "fill_by_country.csv")
    g = fl[fl.rule == "F1"].groupby(["techset", "year"]).gap.sum()
    geo = 100 * (1 - g[("ws", 2025)] / g[("wso", 2025)])
    pct = 100 * f1[2025] / obs[2025]
    cum, cum3, cum4 = f1.loc[2006:].sum(), f3.loc[2006:].sum(), f4.loc[2006:].sum()
    title = f"Without wind and solar growth since 2005, power CO₂ would be {pct:.0f}% higher"
    sub = (f"Power-sector CO₂ if wind and solar (and geothermal, {geo:.1f}% of the gap) had stayed at 2005 levels, with the gap\n"
           f"filled by each country's fossil mix. Cumulative 2006–2025: {cum:.0f} GtCO₂ avoided "
           f"({cum4:.0f}–{cum3:.0f} Gt if all gas or all coal had filled it).")
    src = ("Data: Ember yearly electricity data (2026); emission factors from CEDS v2025_03_18, US EIA, China MEE/CEC. "
           "Combustion CO₂ only; net of renewables' own lifecycle emissions.\n"
           "Demand, nuclear, hydro and bioenergy as observed. Europe pooled as one grid.")
    fig = frame(title, sub, src)
    ax = fig.add_axes([0.06, 0.13, 0.78, 0.62])
    style_ax(ax)
    x = obs.index.values
    ax.fill_between(x, obs + f4, obs + f3, color=CF, alpha=0.14, lw=0)
    ax.plot(x, cf, color=CF, lw=3.2)
    ax.plot(x, obs, color=OBS, lw=3.2)
    ax.set_xlim(2000, 2025)
    ax.set_ylim(0, (obs + f3).max() * 1.08)
    ax.set_ylabel("Gt CO₂ per year", fontsize=15)
    ax.set_xticks([2000, 2005, 2010, 2015, 2020, 2025])
    xe = 2025.35
    ax.text(xe, cf[2025], f"Without wind and\nsolar growth  {cf[2025]:.1f} Gt", color=INK, fontsize=15, va="center", clip_on=False)
    ax.text(xe, obs[2025] - 0.6, f"Actual  {obs[2025]:.1f} Gt", color=INK, fontsize=15, va="center", clip_on=False)
    ax.text(2014.2, (obs + f3)[2019] + 0.35, "range: gas-only to coal-only fill", color=INK2, fontsize=13)
    ax.axvline(2005, color=INK3, lw=1, ls=(0, (3, 3)))
    ax.text(2005.2, ax.get_ylim()[1] * 0.04, "wind and solar\nfrozen after 2005", color=INK2, fontsize=12.5)
    fig.savefig(FIG / "fig1_power_co2.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return dict(pct2025=pct, cum=cum, cum_gas=cum4, cum_coal=cum3, obs2025=obs[2025], cf2025=cf[2025], d2025=f1[2025])


# ------------------------------------------------------------------ fig 2

def fig2():
    z = dict(np.load(D / "fair" / "dT_members.npz"))
    years = z["years"]
    H = pd.read_csv(D / "fair" / "headline_with_ef_uncertainty.csv").set_index("year")
    m = (years >= 2005) & (years <= 2050)
    y = years[m]
    co2 = z["F1_CO2"][m]
    co2p = np.percentile(co2, [5, 50, 95], axis=1)
    H = H.reindex(y)
    H.loc[2005] = 0
    net50, net5, net95 = H.p50.values, H.p5.values, H.p95.values
    k25, k50 = list(y).index(2025), list(y).index(2050)
    ppos = H.P_pos[2025]
    title = f"Aerosols mask wind and solar's avoided warming today; ~{net50[k50]:.3f}°C remains by 2050"
    sub = (f"Temperature difference between a world where wind, solar and geothermal stalled in 2005 and the actual world,\n"
           f"with identical emissions after 2025. Extra coal would also have emitted SO₂, whose cooling offsets most of the\n"
           f"CO₂ warming today (net effect positive in {100*ppos:.0f}% of model samples in 2025); aerosols wash out within years, CO₂ stays.")
    src = ("FaIR v2.2.2, fair-calibrate v1.4.5 (841 members), emissions-driven. Shading: 5–95% range (climate response and, for all effects, emission factors).\n"
           "Values are differences (counterfactual minus actual), so no baseline period applies.")
    fig = frame(title, sub, src, tsize=28)
    ax = fig.add_axes([0.07, 0.13, 0.76, 0.58])
    style_ax(ax)
    ax.fill_between(y, co2p[0], co2p[2], color=CO2C, alpha=0.13, lw=0)
    ax.fill_between(y, net5, net95, color=CF, alpha=0.16, lw=0)
    ax.plot(y, co2p[1], color=CO2C, lw=3)
    ax.plot(y, net50, color=CF, lw=3.2)
    ax.plot(2025, net50[k25], "o", ms=9, color=CF, mec=SURFACE, mew=2, zorder=5)
    ax.axhline(0, color=INK3, lw=1.2)
    ax.axvline(2025, color=INK3, lw=1, ls=(0, (3, 3)))
    ax.text(2025.3, 0.0155, "after 2025: same\nemissions in both worlds", color=INK2, fontsize=12.5, va="top")
    ax.set_xlim(2005, 2050)
    ax.set_ylim(-0.009, 0.016)
    ax.set_yticks(np.arange(-0.008, 0.0161, 0.004))
    ax.set_yticklabels([f"{v:+.3f}" if abs(v) > 1e-9 else "0" for v in np.arange(-0.008, 0.0161, 0.004)])
    ax.set_ylabel("Avoided warming (°C)", fontsize=15)
    xe = 2050.4
    ax.text(xe, co2p[1][-1] - 0.0009, f"CO₂ only\n{co2p[1][-1]:.3f}°C", color=INK, fontsize=14.5, va="center", clip_on=False)
    ax.text(xe, net50[-1] + 0.0011, f"All effects\n{net50[-1]:.3f}°C", color=INK, fontsize=14.5, va="center", clip_on=False)
    ax.annotate(f"2025: {net50[k25]:+.3f}°C\n(CO₂ alone {co2p[1][k25]:+.3f})", xy=(2025, net50[k25]), xytext=(2012.5, -0.0072),
                fontsize=13, color=INK2, arrowprops=dict(arrowstyle="-", color=INK3, lw=1, shrinkA=4, shrinkB=0), annotation_clip=False)
    fig.savefig(FIG / "fig2_avoided_warming.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return dict(net2025=net50[k25], net2025_5=net5[k25], net2025_95=net95[k25], net2050=net50[k50],
                net2050_5=net5[k50], net2050_95=net95[k50], co2_2025=co2p[1][k25], co2_2050=co2p[1][-1], ppos2025=ppos)


# ------------------------------------------------------------------ fig 3

def fig3():
    S = pd.read_csv(D / "fair" / "summary.csv").set_index("scenario")
    rows = [
        ("Headline: country fossil mix, Europe pooled", "F1_full", True),
        ("Fill rule: coal only", "F3_full", False),
        ("Fill rule: gas only", "F4_full", False),
        ("Fill rule: World-average fossil (Ember's method)", "F0_full", False),
        ("Fill rule: build margin", "F2_full", False),
        ("Fill rule: no European pooling", "F1nat_full", False),
        ("Fill rule: lignite not displaced (OECD)", "F1marg_full", False),
        ("Wind and solar only", "ws_F1_full", False),
        ("Add bioenergy to the frozen set*", "wsob_F1_full_nobiocoemis", False),
        ("Official (lower) China/India SO₂ and NOx", "F1_full_lowaer", False),
        ("Manufacturing emissions booked upfront", "F1_full_frontlife", False),
        ("Upstream methane doubled", "F1_full_CH4x2", False),
        ("All shares fixed at 2005 (different counterfactual)", "F5_full", False),
    ]
    de = pd.read_csv(D / "delta_emissions.csv")
    cum_ch4x2 = S.loc["F1_full", "cum_dCO2_Gt"]
    title = "How much the answer depends on the assumptions"
    sub = ("Cumulative avoided CO₂ (2006–2025) and avoided warming in 2050 under alternative choices.\n"
           "The fill rule, whether coal or gas would have filled the gap, matters most.")
    src = ("Bars: 5–95% FaIR climate-response range. *Plotted without bioenergy's own aerosol emissions (CEDS biomass "
           "factors look implausibly high); including them gives a 2050 median of +{:.3f}°C.\nThe last row also undoes coal-to-gas switching and nuclear and hydro changes, "
           "so it is not a sensitivity of the headline.").format(S.loc["wsob_F1_full", "dT2050_p50"])
    fig = frame(title, sub, src)
    axL = fig.add_axes([0.40, 0.13, 0.25, 0.64])
    axR = fig.add_axes([0.70, 0.13, 0.25, 0.64])
    n = len(rows)
    ypos = np.arange(n)[::-1]
    for ax in (axL, axR):
        ax.set_facecolor(SURFACE)
        ax.grid(axis="x", color=GRID, lw=1)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=13, length=0)
        ax.spines["left"].set_visible(False)
        ax.set_ylim(-0.7, n - 0.3)
        ax.set_yticks([])
    h = S.loc["F1_full"]
    axL.axvline(h.cum_dCO2_Gt, color=CF, lw=1.2, alpha=0.6)
    axR.axvline(h.dT2050_p50, color=CF, lw=1.2, alpha=0.6)
    for (lab, key, head), yv in zip(rows, ypos):
        r = S.loc[key]
        col = CF if head else OBS
        axL.text(-0.03, yv, lab, transform=axL.get_yaxis_transform(), ha="right", va="center",
                 fontsize=13.5, color=INK, fontweight="bold" if head else "normal")
        c = r.cum_dCO2_Gt if key != "F1_full_CH4x2" else cum_ch4x2
        axL.plot([0, c], [yv, yv], color=col, lw=2, alpha=0.35)
        axL.plot(c, yv, "o", ms=9, color=col, mec=SURFACE, mew=2)
        axL.text(c + 0.6, yv, f"{c:.0f}", va="center", fontsize=12.5, color=INK2)
        axR.plot([r.dT2050_p5, r.dT2050_p95], [yv, yv], color=col, lw=2.2, alpha=0.5, solid_capstyle="round")
        axR.plot(r.dT2050_p50, yv, "o", ms=9, color=col, mec=SURFACE, mew=2)
    axL.set_xlim(0, 36)
    axR.set_xlim(0, 0.018)
    axR.set_xticks([0, 0.005, 0.010, 0.015])
    axR.set_xticklabels(["0", "0.005", "0.010", "0.015"])
    axL.set_xlabel("Avoided CO₂, 2006–2025 (Gt)", fontsize=14)
    axR.set_xlabel("Avoided warming in 2050 (°C)", fontsize=14)
    fig.savefig(FIG / "fig3_sensitivities.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    a = fig1()
    b = fig2()
    fig3()
    vals = {**a, **b}
    pd.Series(vals).to_csv(D / "headline_numbers.csv", header=["value"])
    for k, v in vals.items():
        print(f"{k}: {v:.4f}")
