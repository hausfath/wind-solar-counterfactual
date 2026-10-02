"""Country x year x fuel emission factors per MWh of fossil electricity.

Why not Ember emissions: Ember's factors are lifecycle CO2e incl. upstream CH4
at GWP 21 and nearly constant in time (Ember methodology PDF). Why not raw
CEDS 1A1a / Ember TWh: CEDS's electricity-vs-heat allocation is inconsistent
across countries (China books ~half of power-sector coal CO2 as
"Heat-production", Poland and Russia nearly all), so CO2 per TWh is
unreliable where heat or autoproducer allocation is large, even though CEDS
1A1a totals are right (14.7 Gt in 2023).

CO2 (combustion, tCO2/MWh):
  USA    EIA Monthly Energy Review Tab. 11.6 (electric power CO2 by fuel) /
         Tab. 7.2b (electric power net generation), Aug 2026 edition. Anchor
         years below; linear interpolation between.
  CHN    coal: MEE "2023 electricity CO2 emission factors" national
         fossil-fuel power EF 0.8273 kgCO2/kWh (2023), scaled back/forward by
         the national net coal consumption rate for power supply
         (gce/kWh; NDRC/NEA 2021 coal-power upgrade plan: 2020 = 305.5, and
         -64.5/-27.5/-9.9 vs 2005/2010/2015; CEC 2025 annual report: 2024 =
         302.4, +0.51 y/y => 2023 = 301.9). Linear interpolation between.
         gas/oil: CEDS path below.
  other  CEDS 1A1a electricity subsectors (public + autoproducer) CO2 /
         Ember TWh, accepted if inside a plausibility band
         (coal 0.75-1.25, gas 0.33-0.65, oil 0.60-1.00 t/MWh); otherwise
         "Ember-scaled": k_f x Ember's own country-year intensity for that
         fuel, where k_f is the generation-weighted median of accepted
         (CEDS or EIA/MEE) / Ember over all accepted country-years
         (computed at run time; ~1.02 coal, ~0.81 gas, ~1.20 oil). This keeps
         Ember's cross-country technology differences (Gibon/Jordaan factors)
         but calibrates the level to combustion CO2.
  2024-25: hold 2023 (CHN uses its 2024 value, held for 2025).

Co-emitted species (SO2, NOx, BC, OC): per-fuel ratio to CO2 from CEDS 1A1a
  (electricity subsectors if they hold >=30% of the fuel's 1A1a CO2, else all
  1A1a), times the CO2 factor above. Ratios are robust to the heat/electricity
  allocation because they come from the same fuel in the same boilers.
  Ratio outliers are capped at the 99th pct of accepted country-years.

Upstream CH4 (tCH4/MWh):
  coal: CEDS 1B1 fugitive CH4 / CEDS all-sector coal CO2, country-specific for
        CHN, IND, USA (production ~ consumption), global ratio elsewhere;
        times coal CO2 factor.
  gas:  global CEDS 1B2b (NG production + distribution) CH4 / global all-sector
        gas CO2, times gas CO2 factor. Oil: global 1B2 (petr) ratio.

Output: ../data/emission_factors.csv  (iso, year, fuel, species, t_per_MWh, source)
"""
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
YEARS = range(2000, 2026)
FUELMAP = {"hard_coal": "coal", "brown_coal": "coal", "coal_coke": "coal", "natural_gas": "gas",
           "heavy_oil": "oil", "light_oil": "oil", "diesel_oil": "oil", "biomass": "bio"}
BAND = {"coal": (0.75, 1.25), "gas": (0.33, 0.65), "oil": (0.60, 1.00)}
SPECIES = ["SO2", "NOx", "BC", "OC"]

# EIA MER Tab 11.6 / Tab 7.2b (fetched 2026-09-27): CO2 MMT / net gen billion kWh
EIA = {  # year: {fuel: t/MWh}
    2005: {"coal": 1983 / 1992.054, "gas": 319 / 683.829, "oil": 98 / 116.482},
    2010: {"coal": 1828 / 1827.738, "gas": 400 / 901.389, "oil": 31 / 34.679},
    2015: {"coal": 1351 / 1340.993, "gas": 525 / 1238.842, "oil": 24 / 26.505},
    2020: {"coal": 788 / 767.702, "gas": 635 / 1522.299, "oil": 16 / 16.333},
    2023: {"coal": 694 / 670.569, "gas": 705 / 1699.855, "oil": 15 / 15.388},
    2024: {"coal": 672 / 647.676, "gas": 735 / 1765.974, "oil": 14 / 14.394},
}
CHN_GCE = {2005: 370.0, 2010: 333.0, 2015: 315.4, 2020: 305.5, 2023: 301.9, 2024: 302.4}
CHN_MEE_2023 = 0.8273


def interp(anchors, years):
    ys = sorted(anchors)
    return {y: float(np.interp(y, ys, [anchors[k] for k in ys])) for y in years}


def main():
    e = pd.read_csv(D / "ember_subset_2000_2025.csv")
    ctry = e[(e["Area type"] == "Country or economy") & (e.Category == "Electricity generation") & (e.Subcategory == "Fuel")]
    gen = ctry.pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value")
    gen.index.names = ["iso", "year"]
    region = e[e["Area type"] == "Country or economy"].groupby("ISO 3 code")["Ember region"].first()
    twh = pd.DataFrame({"coal": gen["Coal"], "gas": gen["Gas"], "oil": gen["Other Fossil"]})

    c = pd.read_csv(D / "ceds_power_fugitive_2000_2023.csv")
    c["iso"] = c.country.str.upper()
    c["f"] = c.fuel.map(FUELMAP)
    p = c[c.sector.str.startswith("1A1a") & c.f.isin(["coal", "gas", "oil"])].copy()
    p["part"] = np.where(p.sector.str.contains("Heat"), "heat", "elec")
    pv = p.pivot_table(index=["iso", "year", "f"], columns=["em", "part"], values="value", aggfunc="sum").fillna(0)

    tot = pd.read_csv(D / "ceds_country_totals_2000_2023.csv")  # all-sector totals (not by fuel)
    rows = []

    # ---------- CO2 from CEDS electricity subsectors, banded
    co2_elec = pv[("CO2", "elec")].unstack("f") / 1e3  # Mt
    ei = (co2_elec / twh.reindex(co2_elec.index)).where(twh.reindex(co2_elec.index) > 0.5)
    accepted = pd.DataFrame({f: ei[f].where(ei[f].between(*BAND[f])) for f in ["coal", "gas", "oil"]})
    # Ember's own intensities (lifecycle, used only for relative cross-country shape)
    em = e[(e["Area type"] == "Country or economy") & (e.Category == "Power sector emissions") & (e.Subcategory == "Fuel")]
    emb = em.pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value")
    emb.index.names = ["iso", "year"]
    emb_int = pd.DataFrame({"coal": emb["Coal"] / gen["Coal"], "gas": emb["Gas"] / gen["Gas"],
                            "oil": emb["Other Fossil"] / gen["Other Fossil"]}).replace([np.inf, -np.inf], np.nan)
    ef = {}
    for f in ["coal", "gas", "oil"]:
        for (iso, yr), val in twh[f].items():
            if yr > 2023 or pd.isna(val):
                continue
            v = accepted[f].get((iso, yr), np.nan)
            if not pd.isna(v):
                ef[(iso, yr, f)] = (v, "CEDS-elec")
    # primary-source overrides are applied before calibrating k (they count as accepted)
    # overrides
    eia = interp({y: EIA[y]["coal"] for y in EIA}, YEARS), interp({y: EIA[y]["gas"] for y in EIA}, YEARS), interp({y: EIA[y]["oil"] for y in EIA}, YEARS)
    for y in YEARS:
        for f, s in zip(["coal", "gas", "oil"], eia):
            ef[("USA", y, f)] = (s[y], "EIA-MER")
    gce = interp(CHN_GCE, YEARS)
    for y in YEARS:
        ef[("CHN", y, "coal")] = (CHN_MEE_2023 * gce[min(y, 2024)] / CHN_GCE[2023], "MEE2023xCEC-gce")
    # calibrate k_f on accepted values, fill remaining country-years with k_f x Ember intensity
    K = {}
    for f in ["coal", "gas", "oil"]:
        acc = pd.Series({(i, y): v[0] for (i, y, ff), v in ef.items() if ff == f and y <= 2023})
        j = pd.concat([acc.rename("a"), emb_int[f].rename("m"), twh[f].rename("w")], axis=1, join="inner").dropna()
        j = j[j.w > 0.5]
        j["k"] = j.a / j.m
        j = j.sort_values("k")
        cw = j.w.cumsum() / j.w.sum()
        K[f] = float(j.k[cw >= 0.5].iloc[0])
        wmed_m = emb_int[f].groupby(level="year").median()
        for (iso, yr), val in twh[f].items():
            if yr > 2023 or pd.isna(val) or (iso, yr, f) in ef:
                continue
            m = emb_int[f].get((iso, yr), np.nan)
            ef[(iso, yr, f)] = (K[f] * (m if not pd.isna(m) else wmed_m[yr]), "Ember-scaled")
    print("calibration k_f:", {f: round(v, 3) for f, v in K.items()})
    pd.Series(K).to_csv(D / "ember_calibration_k.csv", header=["k"])
    # extend 2024-25 by holding 2023 (EIA/MEE overrides already cover their years)
    for (iso, yr, f), v in list(ef.items()):
        if yr == 2023:
            for y in (2024, 2025):
                ef.setdefault((iso, y, f), (v[0], v[1] + "-held2023"))
    co2 = pd.Series({k: v[0] for k, v in ef.items()}, name="t_per_MWh")
    co2src = pd.Series({k: v[1] for k, v in ef.items()}, name="source")
    co2.index.names = co2src.index.names = ["iso", "year", "fuel"]
    rows.append(pd.DataFrame({"t_per_MWh": co2, "source": co2src}).assign(species="CO2"))

    # ---------- pollutant ratios to CO2
    for sp in SPECIES:
        num_e, num_a = pv[(sp, "elec")], pv[(sp, "elec")] + pv[(sp, "heat")]
        den_e, den_a = pv[("CO2", "elec")], pv[("CO2", "elec")] + pv[("CO2", "heat")]
        use_elec = den_e >= 0.3 * den_a
        ratio = (num_e / den_e).where(use_elec, num_a / den_a).replace([np.inf, -np.inf], np.nan)
        ratio = ratio.unstack("f")
        # cap at 99th percentile per fuel
        for f in ratio:
            ratio[f] = ratio[f].clip(upper=ratio[f].quantile(0.99))
        glob = (pv[(sp, "elec")] + pv[(sp, "heat")]).groupby(["year", "f"]).sum() / (pv[("CO2", "elec")] + pv[("CO2", "heat")]).groupby(["year", "f"]).sum()
        out = {}
        for (iso, yr, f), cf in co2.items():
            y = min(yr, 2023)
            r = ratio[f].get((iso, y), np.nan) if f in ratio else np.nan
            src = "CEDS-ratio" + ("-held2023" if yr > 2023 else "")
            if pd.isna(r):
                r, src = glob.get((y, f), np.nan), "CEDS-global-ratio"
            out[(iso, yr, f)] = (cf * r, src)  # kt/kt * t/MWh = t/MWh
        s = pd.DataFrame(out, index=["t_per_MWh", "source"]).T
        s.index.names = ["iso", "year", "fuel"]
        rows.append(s.assign(species=sp))

    # ---------- upstream CH4 per MWh
    fug = c[(c.em == "CH4")]
    coal_ch4 = fug[fug.sector == "1B1_Fugitive-solid-fuels"].groupby(["iso", "year"]).value.sum()
    gas_ch4 = fug[fug.sector.isin(["1B2b_Fugitive-NG-prod", "1B2b_Fugitive-NG-distr"])].groupby("year").value.sum()
    oil_ch4 = fug[fug.sector == "1B2_Fugitive-petr"].groupby("year").value.sum()
    # CH4 per tonne of combustion CO2 from that fuel (all 1A sectors), i.e. per unit fuel burned
    ac = pd.read_csv(D / "ceds_co2_by_fuel_all_sectors.csv").set_index(["iso", "year", "f"]).value
    g_coal = coal_ch4.groupby("year").sum() / ac.xs("coal", level="f").groupby("year").sum()
    g_gas = gas_ch4 / ac.xs("gas", level="f").groupby("year").sum()
    g_oil = oil_ch4 / ac.xs("oil", level="f").groupby("year").sum()
    out = {}
    for (iso, yr, f), cf in co2.items():
        y = min(yr, 2023)
        if f == "coal":
            if iso in ("CHN", "IND", "USA"):
                r = coal_ch4.get((iso, y), np.nan) / ac.get((iso.lower(), y, "coal"), np.nan)
                src = "CEDS-1B1-country"
            else:
                r, src = g_coal[y], "CEDS-1B1-global"
        elif f == "gas":
            r, src = g_gas[y], "CEDS-1B2b-global"
        else:
            r, src = g_oil[y], "CEDS-1B2-global"
        out[(iso, yr, f)] = (cf * r, src)
    s = pd.DataFrame(out, index=["t_per_MWh", "source"]).T
    s.index.names = ["iso", "year", "fuel"]
    rows.append(s.assign(species="CH4_upstream"))

    res = pd.concat(rows).reset_index()
    res["t_per_MWh"] = res.t_per_MWh.astype(float)
    res.to_csv(D / "emission_factors.csv", index=False)
    print("wrote", len(res), "rows")
    # diagnostics
    src = res[res.species == "CO2"].groupby(["fuel", "source"]).size()
    print(src)
    piv = res.pivot_table(index=["iso", "fuel"], columns=["species", "year"], values="t_per_MWh")
    for iso in ["CHN", "USA", "IND", "DEU", "JPN", "BRA", "GBR"]:
        for f in ["coal", "gas"]:
            if (iso, f) in piv.index:
                r = piv.loc[(iso, f)]
                print(iso, f, " ".join(f"{sp}:" + "/".join(f"{r[(sp, y)]*(1e3 if sp!='CO2' else 1):.3g}" for y in (2005, 2015, 2023)) for sp in ["CO2", "SO2", "NOx", "BC", "CH4_upstream"]))


if __name__ == "__main__":
    main()
