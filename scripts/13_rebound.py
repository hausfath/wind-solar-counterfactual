"""Rebound adjustments to avoided CO2 (rule F1, wind + solar + geothermal frozen at 2005).

Method, parameter sources and caveats: ../METHODS.md ("Rebound adjustments"). Four channels are applied to the
headline fill, row by row (country, year, fuel). No econometric displacement coefficient is applied: the
counterfactual holds electricity demand fixed, so displacement is 1:1 by construction and any demand response
is channel 2.

  1. cycling c_it: fossil units backing up variable output run less efficiently, so fuel saved per MWh of wind and
     solar is below the average-intensity value. Scaled with the country's actual wind+solar share, anchored at
     the US estimate (Kaffine et al. 2020).
  2. electricity-demand rebound r = |eps_e| * (-dp_2025) * D_2025 / gap_2025, constant in time (the price
     effect scales with penetration). dp is the net retail price change; dp > 0 (wind/solar raised prices) gives r < 0.
     Optional electrification netting: a share phi of the extra demand is EVs/heat pumps displacing direct fossil
     use (e_disp t CO2/MWh), so r_row = r (1 - phi e_disp / EF_row).
  3. fuel-market rebound f, by fuel and market segment. Starting from the actual-world segment market Q0
     (CEDS 1A combustion CO2 as the fuel-quantity proxy), the counterfactual adds price-inelastic power demand
     Delta. Constant-elasticity equilibrium for the price ratio x:
         Q0 x^eta = P0 + Delta + sum_k O_k x^(-eps_k)
     where P0 is power (inelastic) and O_k are other buyer groups (industry, buildings, iron & steel, heat ...)
     with their own elasticities. f = sum_k O_k (1 - x^(-eps_k)) / Delta. Small-change limit:
     S/(eta + S), S = sum_k s_k |eps_k|; the critic's integrated formula |eps|/(eta+|eps|) is one group with s = 1.
     China and India: part of the extra coal is imported (import margin m), so it enters the rest-of-world market.
     Gas in oil-indexed contract eras (Europe before 2012, Asian LNG before 2015) and administered-price gas
     markets (Russia, Middle East, Central Asia, ...): f = 0 in the central case.
  4. EU ETS waterbed w_t (high case only): under a fixed binding cap, part of the extra EU power CO2 in the
     counterfactual is offset by lower emissions elsewhere in the ETS. Zero in the central case, because the cap was
     set with expected renewables growth and would not have been the same without wind and solar.

Outputs: ../data/rebound_scenarios.csv     (cumulative 2006-2025 and 2025 avoided CO2, every named case)
         ../data/rebound_annual.csv        (annual avoided CO2 by named case)
         ../data/rebound_segments_2025.csv (per-market Delta/Q0, x, f in 2025, central case)
         ../data/rebound_delta_scale.csv   (annual CO2 and co-emission scale factors for 14_rebound_fair.py)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
YRS = range(2006, 2026)
INF = None                                     # perfectly elastic supply: f = 0

EU = ['AUT', 'BEL', 'BGR', 'CYP', 'CZE', 'DEU', 'DNK', 'ESP', 'EST', 'FIN', 'FRA', 'GRC', 'HRV', 'HUN', 'IRL', 'ITA', 'LTU',
      'LUX', 'LVA', 'MLT', 'NLD', 'POL', 'PRT', 'ROU', 'SVK', 'SVN', 'SWE', 'GBR', 'NOR', 'CHE']
ETS = set(EU)                                  # EU ETS (UK ETS from 2021, Swiss ETS linked 2020; treated alike)
SEGMENTS = {
    "coal": {"China": ["CHN"], "India": ["IND"], "United States": ["USA"]},          # else: Rest of world (seaborne-linked)
    "gas": {"North America": ["USA", "CAN", "MEX"], "Europe": EU, "Asian LNG importers": ["JPN", "KOR", "TWN", "IND"],
            "China": ["CHN"],
            "Administered": ["RUS", "BLR", "IRN", "IRQ", "SAU", "ARE", "QAT", "KWT", "OMN", "BHR", "DZA", "LBY", "EGY",
                             "UZB", "TKM", "KAZ", "AZE", "VEN"]},                       # else: Rest of world (market/LNG-priced)
    "oil": {},                                                                          # one global market
}
ROW = {"coal": "Rest of world", "gas": "Rest of world", "oil": "World"}

# ---- parameters: (low, central, high) adjustment. "low" = smallest adjustment to avoided CO2.
P = {
    "cyc_ref": (0.038, 0.065, 0.09),       # cycling penalty at the anchor share (Kaffine et al. 2020, SPP 2012-14:
                                           # static 3.8%, dynamic 6.5% reduction in marginal CO2 savings from wind)
    "cyc_anchor": 0.10, "cyc_cap": 1.5,    # anchor = SPP wind share (~10%); penalty capped at 1.5x the anchor value
    "elec_dp": (0.01, -0.01, -0.03),       # net retail price change from wind/solar at 2025 penetration
    "elec_eps": (0.3, 0.3, 0.5),           # |long-run electricity demand elasticity|
    "elec_phi": (0.4, 0.0, 0.0),           # share of the price-induced extra demand that is electrification (EVs, heat
                                           # pumps) displacing direct fossil use; central 0 (no direct estimate)
    "e_disp": 0.7,                         # t CO2 of direct fossil use displaced per MWh of electrified end use:
                                           # EV ~0.8 (0.20 kWh/km vs 0.16 kg CO2/km petrol), heat pump ~0.67 (COP 3 vs
                                           # 90% gas boiler at 0.20 t/MWh gas)
    "eta_cn": (INF, 3.0, 1.55),            # China and India coal supply (state-managed / administered)
    "eta_coal": (3.0, 1.55, 0.8),          # US and rest-of-world coal supply
    "eta_gas": (1.5, 0.81, 0.5),           # gas supply (Hausman & Kellogg 2015 long-run 0.81)
    "eta_gas_adm": (INF, INF, 0.81),       # administered-price gas (Russia, Middle East, Central Asia, ...)
    "eta_oil": (1.0, 0.42, 0.42),          # oil (Prest et al. 2024 0.42; OPEC+ management -> higher effective)
    "eps_coal_cn": (0.2, 0.3, 0.5),        # China/India non-power thermal coal demand (policy-capped). Central basis.
    "eps_coal": (0.3, 0.5, 0.7),           # US/RoW non-power thermal coal demand
    "eps_coal_agg": (0.3, 0.5, 0.7),       # alternative basis: whole-market coal elasticity (Burke & Liao 2015: total
                                           # provincial coal use incl. power, two-year response, -0.3 to -0.7 in 2012)
    "eps_gas_ind": (0.3, 0.45, 0.6),       # gas: industry, iron & steel, other
    "eps_gas_bld": (0.1, 0.2, 0.3),        # gas: residential and commercial
    "eps_oil": (0.33, 0.33, 0.33),
    "eps_low": (0.0, 0.1, 0.1),            # coal/gas into iron & steel (incl. coke) and heat plants (regulated, must-run)
    "margin": {"China": (0.10, 0.15, 0.20), "India": (0.10, 0.20, 0.30)},   # share of extra coal imported
    "contract": (True, True, False),       # f = 0 for gas in oil-indexed contract eras
    "waterbed": ((0.0, 0.0), (0.0, 0.0), (0.2, 0.6)),   # (2008-17, 2018-25) share of EU-ETS avoided CO2 re-emitted;
                                           # 0 in central: the cap was set with expected renewables, so it is not
                                           # exogenous to this counterfactual. High-case sensitivity only.
}
CONTRACT_END = {"Europe": 2012, "Asian LNG importers": 2015}
KEYS = ["c", "r", "phi", "eta_cn", "eta_coal", "eps_coal", "eta_gas", "eps_gas", "eps_low", "margin", "contract", "wb", "oil"]
CENTRAL = {k: 1 for k in KEYS}
CRITIC = {"coal": (1.55, 0.5), "gas": (0.81, 0.5), "oil": (0.42, 0.33)}   # critic's elasticities (eta, |eps|)


def segment_of(fuel, iso):
    for name, isos in SEGMENTS[fuel].items():
        if iso in isos:
            return name
    return ROW[fuel]


def fill_co2():
    """Fill CO2 (Mt) by iso, year, fuel for rule F1 / techset wso; rows without a factor use the
    generation-weighted world factor for that fuel and year (as 05_emissions.py)."""
    f = pd.read_csv(D / "fill_by_country.csv")
    f = f[(f.rule == "F1") & (f.techset == "wso")]
    L = f.melt(id_vars=["iso", "year"], value_vars=["coal", "gas", "oil"], var_name="fuel", value_name="twh")
    ef = pd.read_csv(D / "emission_factors.csv")
    ef = ef[ef.species == "CO2"][["iso", "year", "fuel", "t_per_MWh"]]
    m = L.merge(ef, on=["iso", "year", "fuel"], how="left")
    ok = m.t_per_MWh.notna()
    w = m[ok].assign(x=m.twh * m.t_per_MWh).groupby(["year", "fuel"]).apply(lambda d: d.x.sum() / d.twh.sum(), include_groups=False)
    m.loc[~ok, "t_per_MWh"] = [w.get((y, fu), np.nan) for y, fu in zip(m.loc[~ok, "year"], m.loc[~ok, "fuel"])]
    m["co2"] = m.twh * m.t_per_MWh
    m["segment"] = [segment_of(fu, i) for fu, i in zip(m.fuel, m.iso)]
    m = m[m.year.isin(YRS) & (m.co2 > 0)].copy()
    return m.reset_index(drop=True)


def vre_share():
    """Actual-world wind+solar share of generation by iso and year (Ember); world share as fallback."""
    e = pd.read_csv(D / "ember_subset_2000_2025.csv")
    g = e[e.Category == "Electricity generation"]
    g = g.pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value", aggfunc="sum")
    sh = ((g.Wind.fillna(0) + g.Solar.fillna(0)) / g["Total Generation"]).replace([np.inf], np.nan)
    w = e[(e.Area == "World") & (e.Category == "Electricity generation")].pivot_table(index="Year", columns="Variable", values="Value")
    world = (w.Wind + w.Solar) / w["Total Generation"]
    return sh, world


def markets():
    """Actual-world segment markets: Mt CO2 by fuel, segment, year and buyer group (CEDS 1A, 2023 held for 2024-25)."""
    a = pd.read_csv(D / "ceds_co2_sector_groups.csv")
    a["iso"] = a.iso.str.upper()
    a["segment"] = [segment_of(fu, i) for fu, i in zip(a.fuel, a.iso)]
    M = a.groupby(["fuel", "segment", "year", "group"]).Mt.sum().unstack("group").fillna(0)
    for y in (2024, 2025):
        last = M.xs(2023, level="year").copy()
        last["year"] = y
        M = pd.concat([M, last.set_index("year", append=True)])
    return M.sort_index()


def buyer_groups(fuel, seg, row, k, basis):
    """[(O_k, |eps_k|)] for the non-power buyers of one market; power (elec) is the inelastic remainder."""
    lo = P["eps_low"][k["eps_low"]]
    if fuel == "coal":
        if basis == "aggregate":                      # whole-market elasticity: s * eps_nonpower = eps_agg, i.e. s = 1
            return [(row.sum(), P["eps_coal_agg"][k["eps_coal"]])]
        e = P["eps_coal_cn" if seg in ("China", "India") else "eps_coal"][k["eps_coal"]]
        return [(row.industry + row.buildings + row.other, e), (row.iron_steel + row.heat, lo)]
    if fuel == "gas":
        return [(row.industry + row.iron_steel + row.other, P["eps_gas_ind"][k["eps_gas"]]),
                (row.buildings, P["eps_gas_bld"][k["eps_gas"]]), (row.heat, lo)]
    return [(row.sum() - row.elec, P["eps_oil"][k["oil"]])]


def supply_eta(fuel, seg, k):
    if fuel == "coal":
        return P["eta_cn"][k["eta_cn"]] if seg in ("China", "India") else P["eta_coal"][k["eta_coal"]]
    if fuel == "gas":
        return P["eta_gas_adm"][k["eta_gas"]] if seg == "Administered" else P["eta_gas"][k["eta_gas"]]
    return P["eta_oil"][k["oil"]]


def solve(Q0, groups, eta, delta, linear=False):
    """Fraction f of the extra power demand delta given up by other buyers, and the price ratio x."""
    groups = [(o, e) for o, e in groups if o > 0 and e > 0]
    if delta <= 0 or eta is None or not groups:
        return 0.0, 1.0
    if linear:
        S = sum(o * e for o, e in groups) / Q0
        return S / (eta + S), np.nan
    P0 = Q0 - sum(o for o, _ in groups)
    g = lambda x: Q0 * x ** eta - (P0 + delta + sum(o * x ** (-e) for o, e in groups))
    x = brentq(g, 1.0, 1e3)
    return sum(o * (1 - x ** (-e)) for o, e in groups) / delta, x


def elec_r(k):
    e = pd.read_csv(D / "ember_subset_2000_2025.csv")
    dem = e[(e.Area == "World") & (e.Category == "Electricity demand")].set_index("Year").Value
    fl = pd.read_csv(D / "fill_by_country.csv")
    gap = fl[(fl.rule == "F1") & (fl.techset == "wso")].groupby("year").gap.sum()
    return P["elec_eps"][k] * (-P["elec_dp"][k]) * dem[2025] / gap[2025]


def lifecycle():
    d = pd.read_csv(D / "delta_emissions.csv")
    x = d[(d.rule == "F1") & (d.techset == "wso") & (d.component == "lifecycle_amortized")].set_index("year").CO2 * 1000
    return x.reindex(YRS).fillna(0)


def run(F, M, VRE, case=None, basis="nonpower", linear=False, cyc_flat=None, critic=False, only=None, seg_out=None):
    """One named case. case: dict KEYS -> 0/1/2 (default central). only: set of channels to apply
    ({'c','r','f','w'}; default all). critic: integrated global market per fuel, s = 1, critic's elasticities."""
    k = dict(CENTRAL, **(case or {}))
    on = only if only is not None else {"c", "r", "f", "w"}
    sh, world = VRE
    R = F.copy()
    if "c" in on:
        if cyc_flat is not None:
            R["c"] = cyc_flat
        else:
            s = np.array([sh.get((i, y), np.nan) for i, y in zip(R.iso, R.year)], dtype=float)
            s = np.where(np.isfinite(s), s, world.reindex(R.year).values)
            R["c"] = P["cyc_ref"][k["c"]] * np.minimum(s / P["cyc_anchor"], P["cyc_cap"])
    else:
        R["c"] = 0.0
    # electrification netting: the electrified share phi of the extra demand displaces e_disp t/MWh of direct
    # fossil CO2, against the fill intensity of that row; r_row can turn negative on gas-heavy grids
    R["r"] = (elec_r(k["r"]) * (1 - P["elec_phi"][k["phi"]] * P["e_disp"] / R.t_per_MWh)) if "r" in on else 0.0
    R["net1"] = R.co2 * (1 - R.c) * (1 - R.r)
    R["f"] = 0.0
    if "f" in on:
        for (y, fu), G in R.groupby(["year", "fuel"]):
            if critic:                                  # integrated world market, one buyer group with s = 1
                eta, e = CRITIC[fu]
                Q0 = M.xs((fu, y), level=["fuel", "year"]).sum().sum()
                f, _ = solve(Q0, [(Q0, e)], eta, G.net1.sum())
                R.loc[G.index, "f"] = f
                continue
            delta = G.groupby("segment").net1.sum().to_dict()
            moved = {}
            if fu == "coal":                            # import margin: part of China/India extra coal is seaborne
                for seg in ("China", "India"):
                    m = P["margin"][seg][k["margin"]]
                    moved[seg] = m
                    d = delta.get(seg, 0.0)
                    delta[seg] = d * (1 - m)
                    delta[ROW[fu]] = delta.get(ROW[fu], 0.0) + d * m
            fs = {}
            for seg, d in delta.items():
                if fu == "gas" and P["contract"][k["contract"]] and y < CONTRACT_END.get(seg, 0):
                    fs[seg] = 0.0
                    continue
                row = M.loc[(fu, seg, y)]
                eta = supply_eta(fu, seg, k)
                f, x = solve(row.sum(), buyer_groups(fu, seg, row, k, basis), eta, d, linear)
                fs[seg] = f
                if seg_out is not None and y == 2025:
                    seg_out.append(dict(fuel=fu, segment=seg, Q0_Mt=row.sum(), delta_Mt=d, delta_over_Q0=d / row.sum(),
                                        s_nonpower=1 - row.elec / row.sum(), eta=eta, x=x, f=f))
            for seg, idx in G.groupby("segment").groups.items():
                m = moved.get(seg, 0.0)
                R.loc[idx, "f"] = (1 - m) * fs.get(seg, 0.0) + m * fs.get(ROW[fu], 0.0)
    R["w"] = 0.0
    if "w" in on:
        w1, w2 = P["waterbed"][k["wb"]]
        wy = np.where(R.year >= 2018, w2, np.where(R.year >= 2008, w1, 0.0))   # Phase I (2005-07) not bankable
        R["w"] = np.where(R.iso.isin(ETS), wy, 0.0)
    R["avoided"] = R.net1 * (1 - R.f) * (1 - R.w)
    return R


def summarise(name, R, life, group=""):
    tot = R.groupby("year").avoided.sum() + life
    fill = R.groupby("year").co2.sum()
    wf = lambda col: (R[col] * R.co2).sum() / R.co2.sum()
    fw = {fu: ((G.f * G.net1).sum() / G.net1.sum()) for fu, G in R.groupby("fuel")}
    row = dict(group=group, scenario=name, cum_Gt=tot.sum() / 1000, y2025_Gt=tot[2025] / 1000,
               pct_of_headline=np.nan, c_eff=wf("c"), r=wf("r"), f_coal=fw.get("coal", 0), f_gas=fw.get("gas", 0),
               f_oil=fw.get("oil", 0), f_all=(R.f * R.net1).sum() / R.net1.sum(), w_eff=wf("w"))
    return row, tot, fill


def main():
    F, M, VRE, life = fill_co2(), markets(), vre_share(), lifecycle()
    head = (F.groupby("year").co2.sum() + life).sum() / 1000
    print(f"headline check: {head:.2f} Gt (pipeline 23.05)")

    # ---- validation: reproduce the reviewer's hand solves (Delta/Q0 = 0.27, one buyer group)
    for s, eta, e, want in [(0.38, 1.55, 0.5, 0.096), (0.25, 3.0, 0.3, 0.021), (0.33, 0.8, 0.7, 0.19)]:
        f, x = solve(1.0, [(s, e)], eta, 0.27)
        print(f"  hand-solve check s={s} eta={eta} eps={e}: x={x:.3f} f={f:.3f} (reviewer {want})")

    seg_out = []
    cases = []          # (group, name, kwargs)
    cases += [("named", "Headline", dict(only=set())),
              ("named", "Central (all channels)", dict(seg_out=seg_out)),
              ("named", "All low", dict(case={k: 0 for k in KEYS})),
              ("named", "All high", dict(case={k: 2 for k in KEYS}, basis="aggregate")),   # incl. whole-market coal basis
              ("named", "Critic's construction (integrated markets, s = 1)", dict(critic=True, only={"f"})),
              ("named", "Alternative: whole-market coal elasticity (s = 1 for coal)", dict(basis="aggregate")),
              ("named", "Alternative: linear (small-change) fuel-market formula", dict(linear=True)),
              ("named", "Alternative: flat 7% cycling (no penetration scaling)", dict(cyc_flat=0.07))]
    # waterfall steps (cumulative, central values)
    cases += [("step", "1 cycling", dict(only={"c"})), ("step", "2 + electricity rebound", dict(only={"c", "r"})),
              ("step", "3 + fuel-market rebound", dict(only={"c", "r", "f"})), ("step", "4 + EU ETS waterbed", dict())]
    # waterfall step ranges: channel k at low/high, earlier channels central, later channels off
    fk = ["eta_cn", "eta_coal", "eps_coal", "eta_gas", "eps_gas", "eps_low", "margin", "contract", "oil"]
    chain = [("1 cycling", {"c"}, ["c"]), ("2 + electricity rebound", {"c", "r"}, ["r", "phi"]),
             ("3 + fuel-market rebound", {"c", "r", "f"}, fk), ("4 + EU ETS waterbed", {"c", "r", "f", "w"}, ["wb"])]
    for name, on, ks in chain:
        for j, side in ((0, "low"), (2, "high")):
            cases.append(("steprange", f"{name}|{side}", dict(only=on, case={kk: j for kk in ks})))
    # one-at-a-time low/high from central, by parameter group
    oat = {"Cycling": ["c"], "Electricity-demand rebound": ["r"], "Electrification netting": ["phi"], "China & India coal supply": ["eta_cn"],
           "US & RoW coal supply": ["eta_coal"], "Coal demand elasticity": ["eps_coal"], "Gas supply": ["eta_gas"],
           "Gas demand elasticity": ["eps_gas"], "Steel & heat-plant elasticity": ["eps_low"],
           "Coal import margin": ["margin"], "Gas contract era": ["contract"], "EU ETS waterbed": ["wb"], "Oil market": ["oil"]}
    for lab, ks in oat.items():
        for j, side in ((0, "low"), (2, "high")):
            cases.append(("oat", f"{lab}|{side}", dict(case={kk: j for kk in ks})))
    # each channel alone at low/central/high
    for ch, ks in (("c", ["c"]), ("r", ["r", "phi"]), ("w", ["wb"])):
        for j, side in enumerate(("low", "central", "high")):
            cases.append(("alone", f"{ch}|{side}", dict(only={ch}, case={kk: j for kk in ks})))
    for j, side in enumerate(("low", "central", "high")):
        cases.append(("alone", f"f|{side}", dict(only={"f"}, case={kk: j for kk in fk})))

    rows, annual, scale = [], {}, {}
    for grp, name, kw in cases:
        R = run(F, M, VRE, **kw)
        row, tot, fill = summarise(name, R, life, grp)
        row["pct_of_headline"] = 100 * row["cum_Gt"] / head
        rows.append(row)
        if grp == "named":
            annual[name] = tot / 1000
            # FaIR scale factors: CO2 (and upstream CH4) by the retained fraction; power co-emissions by (1-c)(1-r)
            scale[name] = pd.DataFrame({"k_co2": R.groupby("year").avoided.sum() / fill,
                                        "k_aer": R.groupby("year").net1.sum() / fill})
    S = pd.DataFrame(rows)
    S.to_csv(D / "rebound_scenarios.csv", index=False, float_format="%.5f")
    pd.DataFrame(annual).to_csv(D / "rebound_annual.csv", index_label="year", float_format="%.5f")
    pd.DataFrame(seg_out).to_csv(D / "rebound_segments_2025.csv", index=False, float_format="%.5f")
    pd.concat(scale, names=["scenario", "year"]).to_csv(D / "rebound_delta_scale.csv", float_format="%.6f")
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
    print(S.drop(columns=["group"]).round(3).to_string(index=False))
    print(pd.DataFrame(seg_out).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
