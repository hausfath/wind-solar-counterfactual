"""FaIR runs: temperature effect of the no-renewable-growth counterfactual.

FaIR v2.2.2, fair-calibrate v1.4.5 calibrated constrained ensemble (841
members), emissions-driven, ch4_method Thornhill2021, 1750-2051 (annual means
to 2050). Recipe follows the author's FaIR attribution runs for IPCC AR7 WG1 Ch2 (paired, emissions-driven).

Emissions:
  1750-2025  historical_1750-2025.csv (fair-calibrate)
  2026-2051  medium-extension, offset-harmonised to 2025 historical:
             E(t) = E_hist(2025) + (E_ext(t) - E_ext(2025)), floored at 0.
             Identical in every scenario, so dT after 2025 is the legacy of
             2006-2025 deployment only. Solar/volcanic forcing: medium-extension,
             identical in every scenario.
  Perturbation: delta_emissions.csv added to CO2 FFI, Sulfur, NOx, BC, OC,
  CH4 for 2006-2025 (timepoint y+0.5 = calendar year y).

Every scenario is paired with a 'base' run in the same batch: dT = T_scen -
T_base member-by-member (identical configs and seeds).

Scenarios needed for the checks in 08_analyze.py are run here (zero
perturbation, 0.5x/2x, single species, stochastic_run=False).
Usage: python3.13 07_fair.py [batch ...]   (default: all batches)

Output: ../data/fair/dT_members.npz (scenario -> [years x 841]),
        ../data/fair/erf_members.npz (headline ERF by specie),
        ../data/fair/dT_percentiles.csv
"""
import copy
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from fair import FAIR
from fair.interface import fill, initialise
from fair.io import read_properties
from fair.structure import units as fair_units

HERE = Path(__file__).resolve().parent
D = HERE.parent / "data"
OUT = D / "fair"
OUT.mkdir(exist_ok=True)
CAL = D / "inputs" / "fair_calibration"   # fair-calibrate v1.4.5 ensemble + emissions (see data/inputs/fair_calibration/README.md)
PARAMS = CAL / "calibrated_constrained_parameters_1.4.5.csv"
SPECIES_FILE = CAL / "species_configs_properties_1.4.5.csv"
HIST = CAL / "historical_1750-2025.csv"
EXT = CAL / "extensions_1750-2500.csv"
VOLC_SOLAR = CAL / "volcanic_solar.csv"
T0, T1 = 1750, 2051
MAP = {"CO2": "CO2 FFI", "SO2": "Sulfur", "NOx": "NOx", "BC": "BC", "OC": "OC", "CH4_upstream": "CH4"}
PCT = (5, 17, 50, 83, 95)

_UNIT_SNAP = {n: copy.deepcopy(getattr(fair_units, n))
              for n in ("desired_emissions_units", "desired_concentration_units", "compound_convert")}


def _restore_units():
    for n, snap in _UNIT_SNAP.items():
        t = getattr(fair_units, n)
        t.clear()
        t.update(copy.deepcopy(snap))


# ------------------------------------------------------------ emissions

def base_emissions():
    h = pd.read_csv(HIST)
    x = pd.read_csv(EXT)
    x = x[x.scenario == "medium-extension"].set_index("variable")
    h = h.set_index("variable")
    cols_h = [c for c in h.columns if c[0].isdigit()]
    fut = [f"{y}.5" for y in range(2026, T1)]
    b = h[["unit"] + cols_h].copy()
    for c in fut:
        b[c] = (h["2025.5"] + (x[c] - x["2025.5"])).clip(lower=0)
    return b  # index variable


def delta_table(rule="F1", techset="wso", comps=("fill", "lifecycle_amortized"), species=tuple(MAP), scale=1.0,
                species_scale=None):
    d = pd.read_csv(D / "delta_emissions.csv")
    d = d[(d.rule == rule) & (d.techset == techset) & d.component.isin(comps)]
    g = d.groupby("year")[list(MAP)].sum()
    out = pd.DataFrame(0.0, index=g.index, columns=list(MAP))
    for s in species:
        out[s] = g[s] * scale * (species_scale or {}).get(s, 1.0)
    return out.loc[2006:2025]


def scenario_rows(name, base, delta):
    b = base.copy()
    if delta is not None:
        for s, var in MAP.items():
            for y, v in delta[s].items():
                b.loc[var, f"{y}.5"] += v
    b = b.reset_index()
    b.insert(0, "scenario", name)
    b.insert(1, "region", "World")
    return b


def forcing_file(names, path):
    vs = pd.read_csv(VOLC_SOLAR)
    vs = vs.rename(columns={vs.columns[0]: "Scenario"})
    sub = vs[vs.Scenario == "medium-extension"]
    pd.concat([sub.assign(Scenario=n) for n in names]).to_csv(path, index=False)


# ------------------------------------------------------------ run

def run_batch(tag, scen, stochastic=True):
    """scen: dict name -> delta DataFrame or None. Always includes 'base'."""
    _restore_units()
    base = base_emissions()
    names = ["base"] + [n for n in scen if n != "base"]
    em = pd.concat([scenario_rows(n, base, scen.get(n)) for n in names])
    ef, ff = OUT / f"_em_{tag}.csv", OUT / f"_vs_{tag}.csv"
    em.to_csv(ef, index=False)
    forcing_file(names, ff)
    params = pd.read_csv(PARAMS, index_col=0)
    pfile = PARAMS
    if not stochastic:
        params["stochastic_run"] = False
        pfile = OUT / "_params_nostoch.csv"
        params.to_csv(pfile)
    f = FAIR(ch4_method="Thornhill2021")
    f.define_time(T0, T1, 1)
    f.define_scenarios(names)
    f.define_configs(params.index)
    species, properties = read_properties(filename=str(SPECIES_FILE))
    f.define_species(species, properties)
    f.allocate()
    f.fill_from_csv(emissions_file=str(ef), forcing_file=str(ff))
    for sp in ("Volcanic", "Solar"):
        fill(f.forcing, f.forcing.sel(specie=sp) * params[f"forcing_scale[{sp}]"].values.squeeze(), specie=sp)
    f.fill_species_configs(str(SPECIES_FILE))
    f.override_defaults(str(pfile))
    initialise(f.concentration, f.species_configs["baseline_concentration"])
    initialise(f.forcing, 0)
    initialise(f.temperature, 0)
    initialise(f.cumulative_emissions, 0)
    initialise(f.airborne_emissions, 0)
    initialise(f.ocean_heat_content_change, 0)
    t = time.time()
    f.run(progress=False)
    print(f"  batch {tag}: {len(names)} scenarios in {time.time()-t:.0f}s", flush=True)
    ef.unlink(); ff.unlink()

    T = f.temperature.sel(layer=0)
    years = f.timebounds[:-1].astype(int)
    tbase = 0.5 * (T.sel(scenario="base").values[:-1] + T.sel(scenario="base").values[1:])
    dT = {n: 0.5 * (T.sel(scenario=n).values[:-1] + T.sel(scenario=n).values[1:]) - tbase for n in names if n != "base"}
    erf = {}
    groups = {"CO2": ["CO2"], "CH4": ["CH4"], "Ozone": ["Ozone"], "Aer-rad": ["Aerosol-radiation interactions"],
              "Aer-cloud": ["Aerosol-cloud interactions"], "Strat H2O": ["Stratospheric water vapour"],
              "BC on snow": ["Light absorbing particles on snow and ice"]}
    for n in names:
        if n == "base":
            continue
        for g, sps in groups.items():
            F = sum(f.forcing.sel(scenario=n, specie=s).values - f.forcing.sel(scenario="base", specie=s).values for s in sps)
            erf[(n, g)] = 0.5 * (F[:-1] + F[1:])
    del f
    return years, dT, erf


def pct(a):
    return np.percentile(a, PCT, axis=-1)


def main():
    only = set(sys.argv[1:])
    F1 = dict(rule="F1", techset="wso")
    AER = ("CO2", "SO2", "BC", "OC")
    batches = {
        "A_layers": {
            "zero": delta_table(**F1, scale=0.0),
            "F1_CO2": delta_table(**F1, species=("CO2",)),
            "F1_CO2aer": delta_table(**F1, species=AER),
            "F1_CO2aerNOx": delta_table(**F1, species=AER + ("NOx",)),
            "F1_full": delta_table(**F1),
        },
        "B_singles": {
            "F1_SO2": delta_table(**F1, species=("SO2",)),
            "F1_BC": delta_table(**F1, species=("BC",)),
            "F1_OC": delta_table(**F1, species=("OC",)),
            "F1_NOx": delta_table(**F1, species=("NOx",)),
            "F1_CH4": delta_table(**F1, species=("CH4_upstream",)),
            "F1_full_x2": delta_table(**F1, scale=2.0),
            "F1_full_x05": delta_table(**F1, scale=0.5),
        },
        "C_rules": {f"{r}_full": delta_table(rule=r, techset="wso") for r in ["F0", "F1nat", "F1marg", "F2", "F3", "F4", "F5"]},
        "D_sens": {
            "ws_F1_full": delta_table(rule="F1", techset="ws"),
            "wsob_F1_full": delta_table(rule="F1", techset="wsob", comps=("fill", "lifecycle_amortized", "bio_coemis")),
            "F1_full_frontlife": delta_table(**F1, comps=("fill", "lifecycle_frontloaded")),
            "F1_full_nolife": delta_table(**F1, comps=("fill",)),
            "F1_full_lowaer": delta_table(**F1, comps=("fill_lowaer", "lifecycle_amortized")),
            "F1_full_CH4x2": delta_table(**F1, species_scale={"CH4_upstream": 2.0}),
            "F1_CO2_lowaer_aer": delta_table(**F1, comps=("fill_lowaer", "lifecycle_amortized"), species=AER),
        },
        "F_bio": {
            # bioenergy frozen, but its own co-emission changes left out (CEDS
            # 1A1a biomass BC/OC per TWh look implausibly high; see METHODS)
            "wsob_F1_full_nobiocoemis": delta_table(rule="F1", techset="wsob", comps=("fill", "lifecycle_amortized")),
        },
    }
    allT, allE = {}, {}
    for tag, scen in batches.items():
        if only and tag not in only:
            continue
        years, dT, erf = run_batch(tag, scen)
        allT.update(dT)
        allE.update(erf)
    if not only or "E_nostoch" in only:
        years, dT, erf = run_batch("E_nostoch", {"F1_full": delta_table(**F1)}, stochastic=False)
        allT["F1_full_nostoch"] = dT["F1_full"]
        (OUT / "_params_nostoch.csv").unlink(missing_ok=True)

    # merge with any previous results (allows re-running single batches)
    npz = OUT / "dT_members.npz"
    if npz.exists():
        prev = dict(np.load(npz))
        prev.pop("years", None)
        prev.update(allT)
        allT = prev
    keep = years >= 2000  # store 2000-2050 as float32 (differences are ~1e-2 degC; float32 is ample)
    allT = {k: (v[keep] if v.shape[0] == len(years) else v).astype(np.float32) for k, v in allT.items()}
    years = years[keep]
    np.savez_compressed(npz, years=years, **allT)
    epz = OUT / "erf_members.npz"
    ekeys = {f"{n}|{g}": v[keep].astype(np.float32) for (n, g), v in allE.items()
             if n.startswith(("F1_full", "F1_CO2", "F1_SO2", "F1_BC", "F1_OC", "F1_NOx", "F1_CH4"))}
    if epz.exists():
        p = dict(np.load(epz)); p.update(ekeys); ekeys = p
    np.savez_compressed(epz, **ekeys)

    rows = []
    for n, a in allT.items():
        p = pct(a)
        for j, y in enumerate(years):
            if y >= 2000:
                rows.append([n, y] + list(p[:, j]) + [(a[j] > 0).mean()])
    pd.DataFrame(rows, columns=["scenario", "year"] + [f"p{q}" for q in PCT] + ["P_pos"]).to_csv(OUT / "dT_percentiles.csv", index=False)
    print("saved", len(allT), "scenarios")


if __name__ == "__main__":
    main()
