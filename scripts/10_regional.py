"""Where fossil power is already falling: power-sector CO2 in the US, UK and EU27, 2005-2025.

Two views, both from the same observed emissions (Ember TWh x our country-year combustion factors,
../data/observed_power_emissions.csv):

1. Decomposition of the 2005->2025 change (exact, additive, two-factor midpoint):
       CO2 = F x I   with F = fossil generation (TWh), I = CO2 / F (fossil intensity)
       F = D - WS - O  (D = total generation, WS = wind + solar + geothermal/other RE, O = nuclear + hydro + bio)
       dCO2 = Ibar*dD  - Ibar*dWS  - Ibar*dO  + Fbar*dI
              demand    wind/solar  other clean  fuel switching & efficiency
   D is generation, so it includes changes in net imports (matters for the UK).
2. The counterfactual (rule F1nat, national fill, wind/solar/geothermal frozen at 2005, fill + amortized
   lifecycle): what emissions would have been without wind and solar growth. National fill (not the
   European pool) so that each region's counterfactual stays inside the region.

Outputs: ../data/regional.csv (per region and year), ../data/regional_decomp.csv, ../figures/fig4_regional.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import importlib
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
fig9 = importlib.import_module("09_figures")

D = Path(__file__).resolve().parent.parent / "data"
FIG = Path(__file__).resolve().parent.parent / "figures"
Y0, Y1 = 2005, 2025


def regions(e):
    c = e[e["Area type"] == "Country or economy"]
    eu = sorted(c[c.EU == 1]["ISO 3 code"].unique())
    assert len(eu) == 27
    return {"United States": ["USA"], "United Kingdom": ["GBR"], "European Union": eu}


def main():
    e = pd.read_csv(D / "ember_subset_2000_2025.csv")
    c = e[(e["Area type"] == "Country or economy") & (e.Category == "Electricity generation") & (e.Subcategory == "Fuel")]
    g = c.pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value").fillna(0)
    obs = pd.read_csv(D / "observed_power_emissions.csv").set_index(["iso", "year"]).CO2 / 1000   # Gt
    dl = pd.read_csv(D / "delta_emissions.csv")   # global only; country deltas below
    dbc = pd.read_csv(D / "delta_by_country.csv")
    dcf = dbc[(dbc.rule == "F1nat") & (dbc.techset == "wso")].set_index(["iso", "year"]).CO2   # Gt, fill only
    rows, dec = [], []
    for name, isos in regions(e).items():
        for y in range(2000, Y1 + 1):
            idx = [(i, y) for i in isos]
            missing = [i for i, yy in idx if (i, yy) not in g.index]
            assert not missing or y < 2005, (name, y, missing)
            G = g.reindex(idx).sum()
            rows.append(dict(region=name, year=y, co2_obs=float(obs.reindex(idx).sum()),
                             co2_cf=float(obs.reindex(idx).sum() + dcf.reindex(idx).fillna(0).sum()),
                             gen=float(G.sum()), ws=float(G.Wind + G.Solar + G["Other Renewables"]),
                             other_clean=float(G.Nuclear + G.Hydro + G.Bioenergy),
                             coal=float(G.Coal), gas=float(G.Gas), fossil=float(G.Coal + G.Gas + G["Other Fossil"])))
        r = pd.DataFrame([x for x in rows if x["region"] == name]).set_index("year")
        a, b = r.loc[Y0], r.loc[Y1]
        Ia, Ib = a.co2_obs / a.fossil, b.co2_obs / b.fossil
        Im, Fm = (Ia + Ib) / 2, (a.fossil + b.fossil) / 2
        parts = {"demand": Im * (b.gen - a.gen), "wind_solar": -Im * (b.ws - a.ws), "other_clean": -Im * (b.other_clean - a.other_clean),
                 "fuel_switch": Fm * (Ib - Ia)}
        tot = b.co2_obs - a.co2_obs
        assert abs(sum(parts.values()) - tot) < 1e-9 + 1e-6 * abs(tot), (name, sum(parts.values()), tot)
        dec.append(dict(region=name, co2_2005=a.co2_obs, co2_2025=b.co2_obs, pct_change=100 * tot / a.co2_obs,
                        cf_2025=b.co2_cf, cf_pct_change=100 * (b.co2_cf / a.co2_obs - 1),
                        **{f"d_{k}": v for k, v in parts.items()}, **{f"share_{k}": 100 * v / tot for k, v in parts.items()},
                        gen_pct=100 * (b.gen / a.gen - 1), coal_share_fossil_2005=100 * a.coal / a.fossil, coal_share_fossil_2025=100 * b.coal / b.fossil,
                        ws_2005=a.ws, ws_2025=b.ws))
    R = pd.DataFrame(rows); R.to_csv(D / "regional.csv", index=False)
    DE = pd.DataFrame(dec); DE.to_csv(D / "regional_decomp.csv", index=False)
    pd.set_option("display.width", 250)
    print(DE.round(3).T.to_string())

    # ---- figure: small multiples, actual vs no-wind-and-solar, plus decomposition bars
    fig9.setup()
    us, uk, eu = (DE[DE.region == n].iloc[0] for n in ["United States", "United Kingdom", "European Union"])
    title = "Where fossil power is already falling"
    sub = (f"Power-sector CO₂ fell {abs(uk['pct_change']):.0f}% in the UK, {abs(eu['pct_change']):.0f}% in the EU and {abs(us['pct_change']):.0f}% in the US between 2005 and 2025.\n"
           "Wind and solar did most of the work in the EU; in the US, switching from coal to gas mattered about as much.")
    src = ("Combustion CO₂: Ember generation × country-year emission factors (CEDS, US EIA). Bars: exact split of fossil generation × fossil intensity;\n"
           "'demand' is total generation, so it includes net imports. Counterfactual: wind, solar, geothermal held at 2005, own fossil mix.")
    f = fig9.frame(title, sub, src, tsize=30)
    cols = {"demand": "#8A8680", "wind_solar": "#1BAF7A", "other_clean": "#2A78D6", "fuel_switch": "#D18F4A"}
    labs = {"demand": "Demand", "wind_solar": "Wind and solar", "other_clean": "Nuclear, hydro, bio", "fuel_switch": "Coal-to-gas, efficiency"}
    keys = ["demand", "wind_solar", "other_clean", "fuel_switch"]
    X0 = [0.15, 0.43, 0.71]; WD = 0.20
    for k, (name, _) in enumerate(regions(e).items()):
        r = R[R.region == name].set_index("year").loc[2000:]
        d = DE[DE.region == name].iloc[0]
        ax = f.add_axes([X0[k], 0.44, WD, 0.25]); fig9.style_ax(ax)
        ax.plot(r.index, r.co2_cf * 1000, color="#EB6834", lw=2.6)
        ax.plot(r.index, r.co2_obs * 1000, color="#3F3A37", lw=2.8)
        ax.set_xlim(2000, 2025); ax.set_ylim(0, r.co2_cf.max() * 1000 * 1.12)
        ax.set_xticks([2005, 2015, 2025])
        ax.text(0, 1.15, f"{name}", transform=ax.transAxes, fontsize=17, color=fig9.INK, fontweight="bold")
        ax.text(0, 1.02, f"{d['pct_change']:+.0f}% since 2005", transform=ax.transAxes, fontsize=14, color=fig9.INK2)
        if k == 0: ax.set_ylabel("Mt CO₂ per year", fontsize=13)
        ax.tick_params(labelsize=12)
        yo, yc = r.co2_obs.iloc[-1] * 1000, r.co2_cf.iloc[-1] * 1000
        ax.text(2025.6, yo, "actual", fontsize=12, va="center", color=fig9.INK, clip_on=False)
        ax.text(2025.6, yc, "without wind\nand solar", fontsize=12, va="center", color="#EB6834", clip_on=False)
        bx = f.add_axes([X0[k], 0.13, WD, 0.2]); fig9.style_ax(bx)
        vals = [d[f"d_{kk}"] * 1000 for kk in keys]
        yy = np.arange(len(keys))[::-1]
        bx.barh(yy, vals, color=[cols[kk] for kk in keys], height=0.62)
        bx.axvline(0, color=fig9.INK3, lw=1)
        bx.set_yticks(yy); bx.set_yticklabels([labs[kk] for kk in keys] if k == 0 else [], fontsize=12)
        bx.grid(axis="x", color=fig9.GRID); bx.grid(axis="y", visible=False)
        lim = max(abs(v) for v in vals)
        bx.set_xlim(-lim * 1.45, lim * 1.45)
        for yv, v in zip(yy, vals):
            bx.text(v + (lim * 0.05 if v >= 0 else -lim * 0.05), yv, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=11, color=fig9.INK2)
        bx.tick_params(labelsize=11)
        if k == 1: bx.set_xlabel("contribution to the 2005–2025 change (Mt CO₂)", fontsize=12)
    f.savefig(FIG / "fig4_regional.png", dpi=200, facecolor=fig9.SURFACE)
    print("wrote", FIG / "fig4_regional.png")


if __name__ == "__main__":
    main()
