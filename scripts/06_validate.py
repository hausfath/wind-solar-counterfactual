"""Validation checks for the data and emissions layers (DESIGN.md 'Validation').

V1  Reproduce Ember GER 2026 p.27: "Had wind and solar not grown since 2000 ...
    This would have added 4,065 MtCO2e annually" (2025). Method inferred:
    World-average fossil lifecycle intensity x (W+S 2025 - W+S 2000) minus
    W+S own lifecycle emissions. Tolerance 1%.
V2  Sum of country generation vs Ember World, per fuel, every year (tolerance
    0.5%; residual is routed through ROW_residual by construction).
V3  Observed power-sector combustion CO2 implied by our factors vs bounds:
    CEDS 1A1a electricity subsectors (lower; misses heat-booked plants) and
    CEDS 1A1a incl. heat (upper). Plus Ember lifecycle for reference.
V4  Observed power SO2/NOx implied by our factors, China / India / USA / EU27,
    printed for comparison with published inventories.
V5  Fill identity: coal + gas + oil fill = gap, every rule except F5.
V6  Implied per-fuel capacity factors under F1 (2024), top gap countries.

Writes ../data/validation_summary.csv and prints a report.
"""
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
res = []


def record(check, value, target, tol, note=""):
    ok = abs(value - target) <= tol if target is not None else None
    res.append(dict(check=check, value=value, target=target, tol=tol, passed=ok, note=note))
    flag = "PASS" if ok else ("n/a" if ok is None else "FAIL")
    print(f"[{flag}] {check}: {value:,.3f}" + (f" vs {target:,.3f} (tol {tol:,.3f})" if target is not None else "") + (f"  {note}" if note else ""))


e = pd.read_csv(D / "ember_subset_2000_2025.csv")
w = e[e.Area == "World"]
wg = w[(w.Category == "Electricity generation") & (w.Subcategory == "Fuel")].pivot_table(index="Year", columns="Variable", values="Value")
wm = w[(w.Category == "Power sector emissions") & (w.Subcategory == "Fuel")].pivot_table(index="Year", columns="Variable", values="Value")

# ---- V1
fos = ["Coal", "Gas", "Other Fossil"]
gap = (wg.loc[2025, ["Wind", "Solar"]].sum() - wg.loc[2000, ["Wind", "Solar"]].sum())
inten = wm.loc[2025, fos].sum() / wg.loc[2025, fos].sum()
ws_life = wm.loc[2025, ["Wind", "Solar"]].sum() - wm.loc[2000, ["Wind", "Solar"]].sum()
v1 = gap * inten - ws_life
record("V1 Ember GER2026 W+S-since-2000 added emissions 2025 (MtCO2e)", v1, 4065, 0.01 * 4065,
       f"gap {gap:,.0f} TWh x {inten*1000:.0f} g/kWh - W+S lifecycle {ws_life:.0f} Mt")

# ---- V2
c = e[(e["Area type"] == "Country or economy") & (e.Category == "Electricity generation") & (e.Subcategory == "Fuel")]
cs = c.pivot_table(index="Year", columns="Variable", values="Value", aggfunc="sum")
for f in ["Coal", "Gas", "Other Fossil", "Wind", "Solar"]:
    rel = (cs[f] / wg[f] - 1).loc[2005:2024]
    worst = rel.abs().idxmax()
    record(f"V2 max |country sum / World - 1| {f} 2005-2024 (%)", 100 * rel.abs().max(), 0, 0.5, f"worst year {worst}")
rel25 = (cs.loc[2025, ["Coal", "Gas", "Wind", "Solar"]] / wg.loc[2025, ["Coal", "Gas", "Wind", "Solar"]] - 1) * 100
print("    2025 (reported countries only, before carry-forward):", rel25.round(1).to_dict())

# ---- V3
obs = pd.read_csv(D / "observed_power_emissions.csv")
ceds = pd.read_csv(D / "ceds_power_fugitive_2000_2023.csv")
cc = ceds[(ceds.em == "CO2") & ceds.sector.str.startswith("1A1a") &
          ceds.fuel.isin(["hard_coal", "brown_coal", "coal_coke", "natural_gas", "heavy_oil", "light_oil", "diesel_oil"])]
lo = cc[cc.sector.str.contains("Electricity")].groupby("year").value.sum() / 1e6
hi = cc.groupby("year").value.sum() / 1e6
ours = obs.groupby("year").CO2.sum() / 1e3
emb = wm[fos].sum(axis=1) / 1e3
print("\n    year  ours  CEDS-elec  CEDS-1A1a(incl heat)  Ember-lifecycle   [Gt CO2]")
for y in [2005, 2010, 2015, 2020, 2023]:
    print(f"    {y}  {ours[y]:.2f}  {lo[y]:.2f}  {hi[y]:.2f}  {emb[y]:.2f}")
    record(f"V3 {y} ours within [CEDS-elec, CEDS-1A1a]", float(lo[y] <= ours[y] <= hi[y]), 1, 0)

# ---- V4
for iso in ["CHN", "IND", "USA"]:
    o = obs[obs.iso == iso].set_index("year")
    g = c[c["ISO 3 code"] == iso].pivot_table(index="Year", columns="Variable", values="Value")
    print(f"    {iso} observed power SO2 / NOx (Mt) and coal SO2 intensity (g/kWh):",
          {y: (round(o.SO2[y], 2), round(o.NOx[y], 2)) for y in [2005, 2010, 2015, 2020, 2023]})
eu = e[(e.EU == 1) & (e["Area type"] == "Country or economy")]["ISO 3 code"].unique()
oe = obs[obs.iso.isin(eu)].groupby("year")[["SO2", "NOx"]].sum()
print("    EU27 observed power SO2 / NOx (Mt):", {y: tuple(oe.loc[y].round(2)) for y in [2005, 2015, 2023]})

# ---- V5
fill = pd.read_csv(D / "fill_by_country.csv")
f5 = fill[fill.rule != "F5"].groupby(["rule", "techset", "year"])[["gap", "coal", "gas", "oil"]].sum()
err = (f5[["coal", "gas", "oil"]].sum(1) - f5.gap).abs().max()
record("V5 max |fill - gap| any rule/techset/year (TWh)", err, 0, 0.5)

# ---- V6
cap = e[(e["Area type"] == "Country or economy") & (e.Category == "Capacity")].pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value")
g24 = c[c.Year == 2024].pivot_table(index="ISO 3 code", columns="Variable", values="Value")
f1 = fill[(fill.rule == "F1") & (fill.techset == "wso") & (fill.year == 2024)].set_index("iso")
top = f1.sort_values("gap", ascending=False).head(15).index
print("\n    V6 implied 2024 F1 capacity factors (observed -> counterfactual; nb = new build TWh):")
for i in top:
    try:
        k = cap.loc[(i, 2024)]
        s = []
        for f, col in [("coal", "Coal"), ("gas", "Gas")]:
            if k[col] > 0:
                ob = g24.loc[i, col] / (k[col] * 8.76)
                cf = (g24.loc[i, col] + f1.loc[i, f] - f1.loc[i, f"nb_{f}"]) / (k[col] * 8.76)
                s.append(f"{f} {ob:.2f}->{cf:.2f}")
        print(f"      {i}: gap {f1.loc[i,'gap']:.0f} TWh; " + ", ".join(s) + f"; nb {f1.loc[i,'nb_coal']+f1.loc[i,'nb_gas']:.0f}")
    except KeyError:
        pass

pd.DataFrame(res).to_csv(D / "validation_summary.csv", index=False)
