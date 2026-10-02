"""Extract the Ember yearly electricity variables the counterfactual needs.

Source: Ember yearly full release, long format
  https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/yearly_full_release_long_format.csv
  (49 MB; last-modified 2026-06-23 at download on 2026-09-27)

Keeps generation (TWh) and capacity (GW) by fuel, demand and net imports, and
Ember's own power-sector emissions by fuel (lifecycle CO2e; used ONLY to
reproduce Ember's published headline, never as FaIR input), for countries
and regions, 2000-2025.

Usage: python3 02_extract_ember.py /path/to/yearly_full_release_long_format.csv
Output: ../data/ember_subset_2000_2025.csv
"""
import sys
from pathlib import Path

import pandas as pd

SRC = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

e = pd.read_csv(SRC)
keep = (
    ((e.Category == "Electricity generation") & (e.Unit == "TWh") & e.Subcategory.isin(["Fuel", "Total"]))
    | ((e.Category == "Capacity") & (e.Subcategory == "Fuel") & (e.Unit == "GW"))
    | ((e.Category == "Electricity demand") & (e.Subcategory == "Demand") & (e.Unit == "TWh"))
    | ((e.Category == "Electricity imports") & (e.Unit == "TWh"))
    | ((e.Category == "Power sector emissions") & e.Subcategory.isin(["Fuel", "Total"]))
)
cols = ["Area", "ISO 3 code", "Area type", "Ember region", "EU", "OECD",
        "Year", "Category", "Subcategory", "Variable", "Unit", "Value"]
s = e.loc[keep, cols]
s.to_csv(OUT / "ember_subset_2000_2025.csv", index=False)
print(len(e), "->", len(s), "rows; categories:", s.groupby(["Category", "Unit"]).size().to_dict())
