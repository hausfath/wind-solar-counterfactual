"""FaIR runs for the rebound-adjusted counterfactuals (paired with a headline run in the same batch).

The F1 / wso perturbation (07_fair.py delta_table) is rescaled year by year with the factors written by
13_rebound.py:
  CO2 and upstream CH4 of the fill  x k_co2(t)  (retained fraction after all channels)
  SO2, NOx, BC, OC of the fill      x k_aer(t)  (power-sector changes only: (1-c)(1-r))
  lifecycle (manufacturing) emissions unchanged.
Co-emissions of the non-power fuel use that rebounds (channel 3) and of the waterbed (channel 4) are not modelled.
Upstream CH4 is scaled by the all-fuel CO2 retained fraction (an approximation; gas carries most upstream CH4).

Usage: python3.13 14_rebound_fair.py
Output: ../data/fair/rebound_dT.csv (percentiles of dT by scenario for 2025, 2035, 2050)
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
fair7 = importlib.import_module("07_fair")
D = Path(__file__).resolve().parent.parent / "data"
RUN = ["Headline", "Central (all channels)", "All low", "All high", "Critic's construction (integrated markets, s = 1)",
       "Alternative: whole-market coal elasticity (s = 1 for coal)"]


def main():
    k = pd.read_csv(D / "rebound_delta_scale.csv").set_index(["scenario", "year"])
    fill = fair7.delta_table(comps=("fill",))
    life = fair7.delta_table(comps=("lifecycle_amortized",))
    scen = {}
    for i, name in enumerate(RUN):
        kk = k.loc[name].reindex(fill.index)
        d = fill.copy()
        for s in ("CO2", "CH4_upstream"):
            d[s] = fill[s] * kk.k_co2
        for s in ("SO2", "NOx", "BC", "OC"):
            d[s] = fill[s] * kk.k_aer
        scen[f"s{i}"] = d + life
    years, dT, _ = fair7.run_batch("G_rebound", scen)
    rows = []
    for i, name in enumerate(RUN):
        a = dT[f"s{i}"]
        for y in (2025, 2035, 2050):
            j = int(np.where(years == y)[0][0])
            p = np.percentile(a[j], (5, 50, 95))
            rows.append(dict(scenario=name, year=y, p5=p[0], p50=p[1], p95=p[2], mean=a[j].mean(), P_pos=(a[j] > 0).mean()))
    out = pd.DataFrame(rows)
    out.to_csv(D / "fair" / "rebound_dT.csv", index=False, float_format="%.5f")
    pd.set_option("display.width", 200)
    print(out.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
