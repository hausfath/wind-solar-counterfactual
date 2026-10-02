"""Counterfactual minus observed emissions, by rule, technology set, year, species.

Components (kept separate so each can be switched on/off downstream):
  fill                   sum_c sum_f fill(c,t,f) x EF(c,t,f); ROW_residual rows
                         (and F0) use the generation-weighted World-average EF.
  lifecycle_amortized    minus the frozen techs' own lifecycle emissions:
                         (World tech(t) - tech(2005)) x Ember lifecycle
                         intensity (treated as CO2; they sit in observed
                         industrial emissions). Central case.
  lifecycle_frontloaded  alternative: embodied emissions booked at installation,
                         dGW(t) x intensity x CF x 8.76 x 25-yr life (sensitivity).
  bio_coemis             techset 'wsob' only: minus bioenergy's own
                         SO2/NOx/BC/OC (global CEDS 1A1a biomass per Ember bio TWh).
                         Biogenic CO2 treated as neutral (not in FaIR CO2 FFI).

Species/units (FaIR conventions): CO2 Gt CO2; SO2 Mt SO2; NOx Mt NO2; BC Mt;
OC Mt; CH4 Mt CH4 (upstream fugitive only).

Also writes observed power-sector emissions (Ember TWh x EF) for validation.
Outputs: ../data/delta_emissions.csv, ../data/observed_power_emissions.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
SPECIES = ["CO2", "SO2", "NOx", "BC", "OC", "CH4_upstream"]
UNIT_SCALE = {"CO2": 1e-3, "SO2": 1.0, "NOx": 1.0, "BC": 1.0, "OC": 1.0, "CH4_upstream": 1.0}  # TWh x t/MWh = Mt; CO2 -> Gt
TECHSETS = {"wso": ["Wind", "Solar", "Other Renewables"], "ws": ["Wind", "Solar"],
            "wsob": ["Wind", "Solar", "Other Renewables", "Bioenergy"]}
LIFE_YR = 25


def main():
    fill = pd.read_csv(D / "fill_by_country.csv")
    ef = pd.read_csv(D / "emission_factors.csv")
    e = pd.read_csv(D / "ember_subset_2000_2025.csv")
    ctry = e[(e["Area type"] == "Country or economy") & (e.Category == "Electricity generation") & (e.Subcategory == "Fuel")]
    gen = ctry.pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value")
    gen.index.names = ["iso", "year"]
    twh = pd.DataFrame({"coal": gen["Coal"], "gas": gen["Gas"], "oil": gen["Other Fossil"]}).stack()
    twh.index.names = ["iso", "year", "fuel"]
    E = ef.pivot_table(index=["iso", "year", "fuel"], columns="species", values="t_per_MWh")

    # World generation-weighted EF per fuel-year (for ROW_residual / F0)
    j = E.join(twh.rename("twh"), how="inner")
    wEF = j.groupby(["year", "fuel"]).apply(lambda d: (d[SPECIES].mul(d.twh, axis=0)).sum() / d.twh.sum(), include_groups=False)

    # observed (for validation): countries with EF
    obs = j[SPECIES].mul(j.twh, axis=0)
    obs = obs.groupby(["iso", "year"]).sum()
    obs.to_csv(D / "observed_power_emissions.csv")

    # ---- fill component
    long = fill.melt(id_vars=["rule", "techset", "iso", "year"], value_vars=["coal", "gas", "oil"], var_name="fuel", value_name="twh")
    cty = long[~long.iso.isin(["WORLD", "ROW_residual"])].merge(E.reset_index(), on=["iso", "year", "fuel"], how="left")
    miss = cty[cty.CO2.isna() & (cty.twh.abs() > 0)]
    if len(miss):
        # countries without an EF row (e.g. fuel absent in Ember that year): use World EF
        print(f"note: {len(miss)} country-fuel-years ({miss.twh.abs().sum():.1f} TWh summed over rules) lack EF; World EF used")
    wld = long[long.iso.isin(["WORLD", "ROW_residual"])].merge(wEF.reset_index(), on=["year", "fuel"], how="left")
    cty = cty.set_index(["year", "fuel"])
    cty[SPECIES] = cty[SPECIES].fillna(wEF.reindex(cty.index))
    cty = cty.reset_index()
    both = pd.concat([cty, wld])
    for s in SPECIES:
        both[s] = both[s] * both.twh * UNIT_SCALE[s]
    comp_fill = both.groupby(["rule", "techset", "year"])[SPECIES].sum()
    comp_fill["component"] = "fill"

    # low-aerosol sensitivity ("fill_lowaer"): official-inventory scaling where
    # CEDS runs high (METHODS V4). China coal-dominated fill: SO2 and NOx per
    # kWh ramped linearly from CEDS (2014) to the CEC 2022 coal-unit values
    # (83 mg SO2, 133 mg NOx per kWh) by 2022 and held after. India SO2 x
    # CREA/ours (4.33 Mt Jun22-May23 vs our 2022 value).
    chn = E.xs(("CHN", 2022, "coal"))
    r_so2, r_nox = 0.083e-3 / chn["SO2"], 0.133e-3 / chn["NOx"]
    ind_so2_obs = (E.xs("IND", level="iso")["SO2"] * twh.xs("IND", level="iso")).xs(2022, level="year").sum()
    r_ind = 4.33 / ind_so2_obs
    ramp = lambda y, r: np.where(y <= 2014, 1.0, np.where(y >= 2022, r, 1 + (r - 1) * (y - 2014) / 8))
    low = both.copy()
    m = low.iso == "CHN"
    low.loc[m, "SO2"] *= ramp(low.loc[m, "year"].values, r_so2)
    low.loc[m, "NOx"] *= ramp(low.loc[m, "year"].values, r_nox)
    low.loc[low.iso == "IND", "SO2"] *= r_ind
    print(f"low-aerosol scaling: CHN SO2 x{r_so2:.2f}, NOx x{r_nox:.2f} (from 2022); IND SO2 x{r_ind:.2f}")
    comp_low = low.groupby(["rule", "techset", "year"])[SPECIES].sum()
    comp_low["component"] = "fill_lowaer"
    comp_fill = pd.concat([comp_fill, comp_low])
    # by-country CO2 for diagnostics
    both.groupby(["rule", "techset", "iso", "year"])[SPECIES].sum().to_csv(D / "delta_by_country.csv")

    # ---- lifecycle of frozen RE (World level)
    w = e[(e.Area == "World")]
    wg = w[(w.Category == "Electricity generation") & (w.Subcategory == "Fuel")].pivot_table(index="Year", columns="Variable", values="Value")
    wm = w[(w.Category == "Power sector emissions") & (w.Subcategory == "Fuel")].pivot_table(index="Year", columns="Variable", values="Value")
    wc = w[(w.Category == "Capacity")].pivot_table(index="Year", columns="Variable", values="Value")
    rows = []
    for tset, techs in TECHSETS.items():
        for yr in range(2005, 2026):
            am = fr = 0.0
            for t in techs:
                if t == "Bioenergy":
                    continue  # bio lifecycle is mostly non-CO2/land; handled by bio_coemis only
                inten = wm.loc[yr, t] / wg.loc[yr, t]  # MtCO2e/TWh = t/MWh
                am += (wg.loc[yr, t] - wg.loc[2005, t]) * inten
                if yr > 2005 and t in wc:
                    dgw = max(wc.loc[yr, t] - wc.loc[yr - 1, t], 0)
                    cf = wg.loc[yr, t] / (wc.loc[yr, t] * 8.76)
                    fr += dgw * cf * 8.76 * LIFE_YR * inten
            rows.append(dict(techset=tset, year=yr, component="lifecycle_amortized", CO2=-am * 1e-3))
            rows.append(dict(techset=tset, year=yr, component="lifecycle_frontloaded", CO2=-fr * 1e-3))
    life = pd.DataFrame(rows)

    # ---- bio co-emissions (wsob only)
    c = pd.read_csv(D / "ceds_power_fugitive_2000_2023.csv")
    bio = c[c.sector.str.startswith("1A1a") & (c.fuel == "biomass")].groupby(["em", "year"]).value.sum().unstack("em") / 1e3  # Mt
    bio_ef = bio.div(wg["Bioenergy"].reindex(bio.index), axis=0)  # t/MWh
    brow = []
    for yr in range(2005, 2026):
        y = min(yr, 2023)
        dtwh = wg.loc[yr, "Bioenergy"] - wg.loc[2005, "Bioenergy"]
        brow.append(dict(techset="wsob", year=yr, component="bio_coemis",
                         **{s: -dtwh * bio_ef.loc[y, s] for s in ["SO2", "NOx", "BC", "OC"]}))
    bioc = pd.DataFrame(brow)

    rules = comp_fill.index.get_level_values("rule").unique()
    extra = pd.concat([life, bioc])
    extra = pd.concat([extra.assign(rule=r) for r in rules])
    out = pd.concat([comp_fill.reset_index(), extra]).fillna(0.0)
    out = out[["rule", "techset", "component", "year"] + SPECIES]
    out.to_csv(D / "delta_emissions.csv", index=False)

    # summary
    net = out[out.component.isin(["fill", "lifecycle_amortized", "bio_coemis"])].groupby(["rule", "techset", "year"])[SPECIES].sum()
    print("\nwso headline, selected years (fill + amortized lifecycle):")
    print(net.xs("wso", level="techset").loc[(slice(None), [2010, 2015, 2020, 2025]), :].round(3).to_string())
    cum = net.groupby(["rule", "techset"]).sum()
    print("\ncumulative 2006-2025 CO2 (Gt):\n", cum.CO2.unstack("techset").round(1))
    lf = life.groupby(["techset", "component"]).CO2.sum().unstack()
    print("\nlifecycle cumulative (Gt):\n", lf.round(2))


if __name__ == "__main__":
    main()
