"""Extract power-sector and fugitive-fuel emissions from the CEDS detailed release.

Source: CEDS v_2025_03_18 "Emissions by country, fuel and sector"
  https://zenodo.org/records/15059443  (CEDS_v_2025_03_18_detailed.zip, 77 MB)
  Latest CEDS emissions release as of 2026-09-27 (the April 2025 release is
  gridded data from the same inventory).

Stream-processes one species at a time from the zip (never fully unzipped) and
keeps only what the counterfactual needs, 2000-2023:
  - sectors 1A1a_Electricity-public, 1A1a_Electricity-autoproducer,
    1A1a_Heat-production (kept separately), 1B1 (fugitive solid fuels),
    1B2 subsectors (fugitive oil/gas)
  - plus per-country all-sector totals (for validation against published totals)

Usage: python3 01_extract_ceds.py /path/to/CEDS_v_2025_03_18_detailed.zip
Output: ../data/ceds_power_fugitive_2000_2023.csv (long format, kt/yr)
        ../data/ceds_country_totals_2000_2023.csv
The raw zip can be deleted afterwards.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

ZIP = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

SPECIES = ["CO2", "SO2", "NOx", "BC", "OC", "CH4"]
YEARS = [f"X{y}" for y in range(2000, 2024)]
KEEP_PREFIX = ("1A1a_", "1B1_", "1B2")

parts, totals = [], []
with zipfile.ZipFile(ZIP) as z:
    for sp in SPECIES:
        name = next(n for n in z.namelist()
                    if n.startswith("CEDS_") and f"/{sp}_CEDS_" in n and n.endswith(".csv"))
        with z.open(name) as fh:
            d = pd.read_csv(fh, usecols=["em", "country", "sector", "fuel", "units"] + YEARS)
        units = d.units.unique()
        assert len(units) == 1, units
        if sp == "CO2":  # all combustion sectors by fuel, for upstream-CH4 ratios
            fmap = {"hard_coal": "coal", "brown_coal": "coal", "coal_coke": "coal",
                    "natural_gas": "gas", "heavy_oil": "oil", "light_oil": "oil", "diesel_oil": "oil"}
            comb = d[d.sector.str.startswith("1A")].assign(f=d.fuel.map(fmap)).dropna(subset=["f"])
            byfuel = comb.groupby(["country", "f"])[YEARS].sum().reset_index()
        tot = d.groupby("country")[YEARS].sum().reset_index()
        tot.insert(0, "em", sp)
        tot.insert(2, "units", units[0])
        totals.append(tot)
        keep = d[d.sector.str.startswith(KEEP_PREFIX)]
        parts.append(keep)
        print(f"{sp}: {len(d)} rows -> {len(keep)} kept; units {units[0]}; "
              f"global 2023 total {d['X2023'].sum():,.0f}, "
              f"1A1a elec (pub+auto) {keep[keep.sector.str.contains('Electricity')]['X2023'].sum():,.0f}")

def to_long(df):
    idx = [c for c in df.columns if not c.startswith("X")]
    long = df.melt(id_vars=idx, var_name="year", value_name="value")
    long["year"] = long.year.str[1:].astype(int)
    return long

p = to_long(pd.concat(parts))
p = p[p.value != 0]
p.to_csv(OUT / "ceds_power_fugitive_2000_2023.csv", index=False)
to_long(pd.concat(totals)).to_csv(OUT / "ceds_country_totals_2000_2023.csv", index=False)
bf = to_long(byfuel).rename(columns={"country": "iso"})
bf.to_csv(OUT / "ceds_co2_by_fuel_all_sectors.csv", index=False)
print("wrote", OUT)
