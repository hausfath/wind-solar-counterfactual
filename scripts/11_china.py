"""China: power-sector CO2 with and without wind and solar growth, and what met demand growth each year.
A social-media figure (not in the blog post).

Left panel: observed power-sector combustion CO2 (Ember TWh x our country-year factors; China coal uses
MEE/CEC factors, see METHODS.md) and the counterfactual with wind, solar and geothermal held at 2005 and the
gap filled with China's own fossil mix (rule F1; China is not pooled, so F1 = F1nat). China's fossil mix is
~95% coal, so a gas-only bound is not meaningful here and is not shown.
Right panel: year-on-year change in generation by group (fossil; wind + solar; hydro, nuclear, bioenergy)
with the change in demand marked. Ember reports no 'Other Renewables' for China (treated as 0).

Outputs: ../data/china.csv, ../figures/fig5_china.png
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
fig9 = importlib.import_module("09_figures")
D = Path(__file__).resolve().parent.parent / "data"
FIG = Path(__file__).resolve().parent.parent / "figures"
Y0, Y1, B0 = 2005, 2025, 2015


def main():
    e = pd.read_csv(D / "ember_subset_2000_2025.csv")
    c = e[(e["ISO 3 code"] == "CHN") & (e["Area type"] == "Country or economy")]
    g = c[(c.Category == "Electricity generation") & (c.Subcategory == "Fuel")].pivot_table(index="Year", columns="Variable", values="Value").fillna(0)
    dem = c[c.Category == "Electricity demand"].set_index("Year").Value
    assert Y1 in g.index and Y1 in dem.index, "China 2025 not reported by Ember"
    obs = pd.read_csv(D / "observed_power_emissions.csv").set_index(["iso", "year"]).CO2.xs("CHN") / 1000   # Gt
    dbc = pd.read_csv(D / "delta_by_country.csv")
    d1 = dbc[(dbc.rule == "F1") & (dbc.techset == "wso") & (dbc.iso == "CHN")].set_index("year").CO2
    yrs = list(range(Y0, Y1 + 1))
    ws = g.Wind + g.Solar + (g["Other Renewables"] if "Other Renewables" in g else 0)
    df = pd.DataFrame({"co2_obs": obs.reindex(yrs), "co2_cf": obs.reindex(yrs) + d1.reindex(yrs).fillna(0),
                       "fossil": (g.Coal + g.Gas + g["Other Fossil"]).reindex(yrs), "wind_solar": ws.reindex(yrs),
                       "other_clean": (g.Hydro + g.Nuclear + g.Bioenergy).reindex(yrs), "coal": g.Coal.reindex(yrs),
                       "demand": dem.reindex(yrs)}, index=pd.Index(yrs, name="year"))
    df.to_csv(D / "china.csv")
    ch = df.diff()
    s = {"pct_higher": 100 * (df.co2_cf[Y1] / df.co2_obs[Y1] - 1), "obs": df.co2_obs[Y1], "cf": df.co2_cf[Y1],
         "obs_change_last": 100 * (df.co2_obs[Y1] / df.co2_obs[Y1 - 1] - 1), "obs_change_all": 100 * (df.co2_obs[Y1] / df.co2_obs[Y0] - 1),
         "demand_ratio": df.demand[Y1] / df.demand[Y0], "ws_share_last": 100 * ch.wind_solar[Y1] / ch.demand[Y1],
         "fossil_change_last": 100 * (df.fossil[Y1] / df.fossil[Y1 - 1] - 1), "cum": d1.loc[Y0 + 1:Y1].sum()}
    for k, v in s.items():
        print(f"{k}: {v:.3f}")

    fig9.setup()
    title = f"Without wind and solar, China's power emissions would be {s['pct_higher']:.0f}% higher"
    sub = (f"China's electricity demand grew {s['demand_ratio']:.1f}-fold between 2005 and 2025. In {Y1}, wind and solar growth met "
           f"{s['ws_share_last']:.0f}% of the increase in demand,\nand fossil generation fell {abs(s['fossil_change_last']):.0f}%. "
           f"Wind and solar avoided {s['cum']:.1f} billion tonnes of CO₂ from China's power sector over 2006–{Y1}.")
    src = ("Data: Ember yearly electricity data; CO₂ factors from China MEE/CEC and CEDS. Counterfactual: wind, solar and geothermal held at 2005 levels,\n"
           "gap filled with China's own fossil mix (~95% coal). Combustion CO₂, net of renewables' manufacturing emissions.")
    f = fig9.frame(title, sub, src, tsize=28)
    # left: CO2
    ax = f.add_axes([0.06, 0.13, 0.36, 0.58]); fig9.style_ax(ax)
    x = df.index.values
    ax.fill_between(x, df.co2_obs, df.co2_cf, color=fig9.CF, alpha=0.14, lw=0)
    ax.plot(x, df.co2_cf, color=fig9.CF, lw=3.2)
    ax.plot(x, df.co2_obs, color=fig9.OBS, lw=3.2)
    ax.set_xlim(Y0, Y1); ax.set_ylim(0, df.co2_cf.max() * 1.12)
    ax.set_xticks([2005, 2010, 2015, 2020, 2025])
    ax.set_ylabel("Gt CO₂ per year", fontsize=15)
    ax.text(0, 1.04, "China power-sector CO₂", transform=ax.transAxes, fontsize=17, fontweight="bold", color=fig9.INK)
    ax.text(Y1 + 0.4, df.co2_cf[Y1], f"without wind\nand solar\n{df.co2_cf[Y1]:.1f} Gt", color=fig9.CF, fontsize=14, va="center", clip_on=False)
    ax.text(Y1 + 0.4, df.co2_obs[Y1], f"actual\n{df.co2_obs[Y1]:.1f} Gt", color=fig9.INK, fontsize=14, va="center", clip_on=False)
    # right: annual change in generation by group
    bx = f.add_axes([0.58, 0.13, 0.38, 0.58]); fig9.style_ax(bx)
    yy = np.arange(B0, Y1 + 1)
    cols = [("wind_solar", "Wind and solar", "#1BAF7A"), ("other_clean", "Hydro, nuclear, bio", "#2A78D6"), ("fossil", "Fossil", "#8A8680")]
    pos = np.zeros(len(yy)); neg = np.zeros(len(yy))
    for key, lab, col in cols:
        v = ch[key].reindex(yy).values
        base = np.where(v >= 0, pos, neg)
        bx.bar(yy, v, bottom=base, color=col, width=0.72, label=lab)
        pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
    bx.scatter(yy, ch.demand.reindex(yy), marker="_", s=420, color=fig9.INK, linewidths=3, zorder=5, label="Change in demand")
    bx.axhline(0, color=fig9.INK3, lw=1)
    bx.set_xticks([2015, 2017, 2019, 2021, 2023, 2025])
    bx.set_ylabel("TWh change from previous year", fontsize=15)
    bx.text(0, 1.04, "What met China's demand growth each year", transform=bx.transAxes, fontsize=17, fontweight="bold", color=fig9.INK)
    bx.legend(loc="upper left", frameon=False, fontsize=13)
    lo = min(neg.min(), 0)
    bx.set_ylim(lo * 1.25 - 50, max(pos.max(), ch.demand.reindex(yy).max()) * 1.18)
    f.savefig(FIG / "fig5_china.png", dpi=200, facecolor=fig9.SURFACE)
    print("wrote", FIG / "fig5_china.png")


if __name__ == "__main__":
    main()
