"""Extract fossil combustion CO2 by country, fuel and sector group from the CEDS detailed release
(for the non-power shares used in 13_rebound.py).

Source: CEDS v_2025_03_18 detailed release, as in 01_extract_ceds.py
  https://zenodo.org/records/15059443  (CEDS_v_2025_03_18_detailed.zip, 77 MB)

Sector groups (CEDS 1A combustion sectors only; process emissions such as 2C1 blast furnaces are not included):
  elec          1A1a_Electricity-public, 1A1a_Electricity-autoproducer
  heat          1A1a_Heat-production
  transform     1A1bc_Other-transformation (refineries, coke ovens)
  iron_steel    1A2a_Ind-Comb-Iron-steel (plus all coal_coke use, wherever booked)
  industry      other 1A2 sectors
  buildings     1A4a commercial, 1A4b residential
  other         transport, agriculture, 1A5

Usage: python3 01b_extract_ceds_sectors.py /path/to/CEDS_v_2025_03_18_detailed.zip
Output: ../data/ceds_co2_sector_groups.csv (Mt CO2, 2000-2023). The raw zip can be deleted afterwards.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

ZIP = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent / "data"
YEARS = [f"X{y}" for y in range(2000, 2024)]
FUEL = {"hard_coal": "coal", "brown_coal": "coal", "coal_coke": "coal",
        "natural_gas": "gas", "heavy_oil": "oil", "light_oil": "oil", "diesel_oil": "oil"}


def group(sector, fuel):
    if fuel == "coal_coke":
        return "iron_steel"
    if sector.startswith("1A1a_Electricity"):
        return "elec"
    if sector.startswith("1A1a_Heat"):
        return "heat"
    if sector.startswith("1A1bc"):
        return "transform"
    if sector.startswith("1A2a"):
        return "iron_steel"
    if sector.startswith("1A2"):
        return "industry"
    if sector.startswith(("1A4a", "1A4b")):
        return "buildings"
    return "other"


with zipfile.ZipFile(ZIP) as z:
    name = next(n for n in z.namelist() if n.startswith("CEDS_") and "/CO2_CEDS_" in n and n.endswith(".csv"))
    d = pd.read_csv(z.open(name), usecols=["country", "sector", "fuel", "units"] + YEARS)
assert set(d.units) == {"ktCO2"}, d.units.unique()
d = d[d.sector.str.startswith("1A") & d.fuel.isin(FUEL)].copy()
d["f"] = d.fuel.map(FUEL)
d["group"] = [group(s, f) for s, f in zip(d.sector, d.fuel)]
g = d.groupby(["country", "f", "group"])[YEARS].sum().reset_index()
L = g.melt(id_vars=["country", "f", "group"], var_name="year", value_name="Mt")
L["year"] = L.year.str[1:].astype(int)
L["Mt"] = L.Mt / 1e3
L = L[L.Mt != 0].rename(columns={"country": "iso", "f": "fuel"})
L.to_csv(OUT / "ceds_co2_sector_groups.csv", index=False, float_format="%.4f")
w = L[L.year == 2023].groupby(["fuel", "group"]).Mt.sum().unstack().round(0)
print(w)
print("wrote", OUT / "ceds_co2_sector_groups.csv")
