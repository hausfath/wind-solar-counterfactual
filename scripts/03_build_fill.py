"""Counterfactual generation layer: the renewable gap and how fossil fuels fill it.

For each technology set, country and year 2005-2025:
    gap(c,t) = sum over frozen techs of max(RE(c,t) - RE(c,base), 0)
    base = 2005 (or the country's first reported year if later)
The gap is filled with fossil generation under several named rules (see
DESIGN.md). Output is TWh of *additional* fossil generation by fuel.

Rules
  F0      World-average fossil mix applied to the World gap (Ember's method;
          validation only).
  F1      HEADLINE. Country-year dispatchable fossil mix (coal, gas,
          dispatchable oil), Europe pooled, per-fuel capacity caps with spill:
          (i) other in-country (or in-pool) fossil headroom, (iii) new build
          in the fuel of recent net capacity additions.
  F1nat   F1 without European pooling (sensitivity).
  F1nocap F1nat without capacity caps (transparency).
  F1marg  F1 but for OECD countries from 2010 on, lignite (must-run) is
          removed from the coal weight (conservative, gas-heavier margin).
  F2      Build margin: weights from trailing 5-yr net fossil capacity
          additions (coal vs gas), fallback F1nocap. Low-information check.
  F3      Coal only (bound).   F4  Gas only (bound).
  F5      Every source's generation share fixed at 2005 values against
          observed total generation (a different counterfactual; bookend).
          Fill can be negative for a fuel (e.g. US gas).

2025: countries not reporting 2025 carry 2024 forward. Every year a
"ROW_residual" row routes World minus sum-of-countries (gap and fossil) through
the World-average mix so totals reconcile exactly with Ember's World.

Oil: Ember "Other Fossil" mixes oil with waste and manufactured gases, which do
not respond to renewables. Dispatchable oil TWh = min(Other Fossil TWh,
CEDS 1A1a oil CO2 / 0.80 tCO2/MWh); the remainder gets zero weight.

Usage: python3.13 03_build_fill.py
Inputs:  ../data/ember_subset_2000_2025.csv, ../data/ceds_power_fugitive_2000_2023.csv
Output:  ../data/fill_by_country.csv, ../data/fill_diagnostics.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
YEARS = range(2005, 2026)
BASE = 2005
TECHSETS = {
    "wso": ["Wind", "Solar", "Other Renewables"],          # headline
    "ws": ["Wind", "Solar"],
    "wsob": ["Wind", "Solar", "Other Renewables", "Bioenergy"],
}
FOSSIL = ["coal", "gas", "oil"]
CF_CAP = {"coal": 0.80, "gas": 0.85, "oil": 0.60}
OIL_TCO2_PER_MWH = 0.80
NEWBUILD_WINDOW = 5
# Synchronous/interconnected European pool (EU27 minus isolated CYP/MLT, plus
# GBR, NOR, CHE and Western Balkans).
EU27 = ['AUT', 'BEL', 'BGR', 'CZE', 'DEU', 'DNK', 'ESP', 'EST', 'FIN', 'FRA', 'GRC',
        'HRV', 'HUN', 'IRL', 'ITA', 'LTU', 'LUX', 'LVA', 'NLD', 'POL', 'PRT', 'ROU',
        'SVK', 'SVN', 'SWE', 'CYP', 'MLT']
EUROPE_POOL = sorted(set(EU27) - {"CYP", "MLT"} | {"GBR", "NOR", "CHE", "BIH", "MKD", "MNE", "SRB", "XKX", "ALB"})


# ---------------------------------------------------------------- load

def load():
    e = pd.read_csv(D / "ember_subset_2000_2025.csv")
    ctry = e[e["Area type"] == "Country or economy"]
    gen = ctry[(ctry.Category == "Electricity generation") & (ctry.Subcategory == "Fuel")] \
        .pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value", aggfunc="sum", dropna=False)
    cap = ctry[ctry.Category == "Capacity"] \
        .pivot_table(index=["ISO 3 code", "Year"], columns="Variable", values="Value", aggfunc="sum", dropna=False)
    world = e[(e.Area == "World") & (e.Category == "Electricity generation") & (e.Subcategory == "Fuel")] \
        .pivot_table(index="Year", columns="Variable", values="Value", aggfunc="sum")
    meta = ctry.groupby("ISO 3 code")[["OECD", "EU", "Ember region", "Area"]].first()
    # pivot_table drops all-NaN; keep NaN (not 0) where Ember doesn't report
    raw = ctry[(ctry.Category == "Electricity generation") & (ctry.Subcategory == "Fuel")]
    reported = raw.set_index(["ISO 3 code", "Year", "Variable"]).Value.unstack("Variable")
    gen = reported.reindex(gen.index)

    ceds = pd.read_csv(D / "ceds_power_fugitive_2000_2023.csv")
    ceds = ceds[(ceds.em == "CO2") & ceds.sector.str.startswith("1A1a")]
    ceds["iso"] = ceds.country.str.upper()
    oil = ceds[ceds.fuel.isin(["heavy_oil", "light_oil", "diesel_oil"])].groupby(["iso", "year"]).value.sum() / 1e3  # Mt
    coal = ceds[ceds.fuel.isin(["hard_coal", "brown_coal", "coal_coke"])]
    brown_share = (coal[coal.fuel == "brown_coal"].groupby(["iso", "year"]).value.sum()
                   / coal.groupby(["iso", "year"]).value.sum()).fillna(0)
    return gen, cap, world, meta, oil, brown_share


def carry_forward(panel, isos, last_full=2024, year=2025):
    """Countries missing `year` get their `last_full` row, flagged."""
    if year in panel.index.get_level_values("Year"):
        yr = panel.xs(year, level="Year")
        have = set(yr.index[yr.notna().any(axis=1)])
        panel = panel.drop([(i, year) for i in yr.index if i not in have])
    else:
        have = set()
    add = []
    for i in isos:
        if i not in have and (i, last_full) in panel.index:
            r = panel.loc[(i, last_full)].copy()
            r.name = (i, year)
            add.append(r)
    carried = [r.name[0] for r in add]
    if add:
        panel = pd.concat([panel, pd.DataFrame(add)]).sort_index()
        panel.index = pd.MultiIndex.from_tuples(panel.index, names=["ISO 3 code", "Year"])
    return panel, carried


def extend_ceds(s, isos_years):
    """CEDS ends 2023: hold 2023 values for 2024-2025."""
    s = s.copy()
    for y in (2024, 2025):
        last = s.xs(2023, level="year")
        last.index = pd.MultiIndex.from_arrays([last.index, [y] * len(last)], names=["iso", "year"])
        s = pd.concat([s, last])
    return s


# ---------------------------------------------------------------- gap

def compute_gap(gen, techs):
    out, notes = {}, []
    for iso in gen.index.get_level_values(0).unique():
        g = gen.loc[iso]
        yrs = g.index
        base_year = BASE if BASE in yrs else yrs.min()
        if base_year != BASE:
            notes.append((iso, f"base year {base_year}"))
        tot = pd.Series(0.0, index=[y for y in YEARS if y in yrs])
        for tch in techs:
            if tch not in g:
                continue
            col = g[tch]
            b = col.get(base_year, np.nan)
            if np.isnan(b):  # tech first reported later: its first reported value is the base
                first = col.dropna()
                if first.empty:
                    continue
                b = first.iloc[0]
            d = (col.reindex(tot.index) - b)
            tot += d.fillna(0)
        neg = tot[tot < 0]
        if len(neg):
            notes.append((iso, f"negative gap set to 0 in {len(neg)} yrs (min {neg.min():.2f} TWh)"))
        out[iso] = tot.clip(lower=0)
    s = pd.concat(out, names=["iso", "year"])
    return s, notes


# ---------------------------------------------------------------- fill helpers

def fossil_obs(gen, oil_co2):
    """Observed dispatchable fossil generation by fuel (TWh) per country-year."""
    df = pd.DataFrame(index=gen.index)
    df["coal"] = gen["Coal"].fillna(0)
    df["gas"] = gen["Gas"].fillna(0)
    of = gen["Other Fossil"].fillna(0)
    oc = oil_co2.reindex(pd.MultiIndex.from_arrays([gen.index.get_level_values(0), gen.index.get_level_values(1)])).fillna(0).values
    df["oil"] = np.minimum(of.values, oc / OIL_TCO2_PER_MWH)
    df["other_fossil_nondisp"] = of.values - df["oil"].values
    df.index.names = ["iso", "year"]
    return df


def capacity(cap):
    c = pd.DataFrame(index=cap.index)
    c["coal"] = cap.get("Coal")
    c["gas"] = cap.get("Gas")
    c["oil"] = cap.get("Other Fossil")
    c.index.names = ["iso", "year"]
    return c


def headroom(obs, capgw):
    """TWh headroom per fuel = max(cap CF, observed CF) * GW * 8.76 - observed."""
    h = pd.DataFrame(index=obs.index)
    for f in FOSSIL:
        gw = capgw[f].reindex(obs.index)
        maxgen = gw * 8.76
        obs_cf = obs[f] / maxgen.replace(0, np.nan)
        cf = np.maximum(CF_CAP[f], obs_cf.fillna(0))
        hr = cf * maxgen - obs[f]
        h[f] = hr.where(gw.notna(), np.inf).clip(lower=0).fillna(np.inf)  # no capacity data -> uncapped
    return h


def newbuild_mix(capgw, iso, year):
    """Fuel split of trailing net coal/gas capacity additions; gas if none positive."""
    try:
        now, then = capgw.loc[(iso, year)], capgw.loc[(iso, year - NEWBUILD_WINDOW)]
    except KeyError:
        return {"coal": 0.0, "gas": 1.0}
    add = {f: max((now[f] or 0) - (then[f] or 0), 0) if pd.notna(now[f]) and pd.notna(then[f]) else 0 for f in ("coal", "gas")}
    tot = sum(add.values())
    return {f: v / tot for f, v in add.items()} if tot > 0 else {"coal": 0.0, "gas": 1.0}


def fill_group(gap_total, weights, obs, hroom, members, capgw, year, cap_on=True):
    """Fill `gap_total` TWh across `members` (list of iso) for one year.

    weights: dict fuel -> share (sum 1) at group level.
    Allocation of each fuel's fill to members is proportional to their observed
    generation of that fuel. Returns DataFrame members x [coal, gas, oil,
    nb_coal, nb_gas] and spill diagnostics.
    """
    res = pd.DataFrame(0.0, index=members, columns=FOSSIL + ["nb_coal", "nb_gas"])
    if gap_total <= 0:
        return res, 0.0, 0.0
    o = obs.loc[[(m, year) for m in members]].droplevel(1)
    h = hroom.loc[[(m, year) for m in members]].droplevel(1) if cap_on else pd.DataFrame(np.inf, index=members, columns=FOSSIL)
    want = {f: gap_total * weights[f] for f in FOSSIL}
    excess = 0.0
    for f in FOSSIL:
        if want[f] <= 0:
            continue
        share = o[f] / o[f].sum() if o[f].sum() > 0 else pd.Series(1 / len(members), index=members)
        alloc = share * want[f]
        take = np.minimum(alloc, h[f])
        res[f] += take
        h[f] = h[f] - take
        excess += (alloc - take).sum()
    spill_other = 0.0
    if excess > 1e-9:  # (i) remaining fossil headroom anywhere in the group
        room = h[FOSSIL].replace(np.inf, 1e12)
        tot_room = room.values.sum()
        use = min(excess, tot_room)
        if use > 0:
            res[FOSSIL] += room / tot_room * use
            spill_other = use
            excess -= use
    newbuild = 0.0
    if excess > 1e-9:  # (iii) new build, allocated to members by their gap share proxy (fossil size)
        size = o[FOSSIL].sum(1)
        size = size / size.sum() if size.sum() > 0 else pd.Series(1 / len(members), index=members)
        for m in members:
            mix = newbuild_mix(capgw, m, year)
            res.loc[m, "nb_coal"] += excess * size[m] * mix["coal"]
            res.loc[m, "nb_gas"] += excess * size[m] * mix["gas"]
        newbuild = excess
    return res, spill_other, newbuild


def f1_weights(o_row, oecd=False, year=None, brown=0.0, marg=False):
    w = {f: o_row[f] for f in FOSSIL}
    if marg and oecd and year >= 2010:
        w["coal"] *= (1 - brown)
    s = sum(w.values())
    return {f: v / s for f, v in w.items()} if s > 0 else None


# ---------------------------------------------------------------- main

def main():
    gen, cap, world, meta, oil_co2, brown = load()
    isos = sorted(gen.index.get_level_values(0).unique())
    gen, carried = carry_forward(gen, isos)
    cap, _ = carry_forward(cap, isos)
    oil_co2 = extend_ceds(oil_co2, None)
    brown = extend_ceds(brown, None)

    obs = fossil_obs(gen, oil_co2)
    capgw = capacity(cap).reindex(obs.index)
    hroom = headroom(obs, capgw)
    regions = meta["Ember region"]
    rows, diag = [], []

    # world fossil mix (for F0 and the residual bucket)
    wf = pd.DataFrame({"coal": world["Coal"], "gas": world["Gas"], "oil": world["Other Fossil"]})
    wmix = wf.div(wf.sum(1), axis=0)

    for tset, techs in TECHSETS.items():
        gap, notes = compute_gap(gen, techs)
        for iso, n in notes:
            diag.append({"techset": tset, "iso": iso, "note": n})
        # World gap for F0 / residual
        wg = sum((world[t] - world.loc[BASE, t]) for t in techs).loc[list(YEARS)].clip(lower=0)

        for year in YEARS:
            gy = gap.xs(year, level="year").reindex(isos).fillna(0)
            present = [i for i in isos if (i, year) in obs.index]
            # --- residual bucket: World - sum(countries)
            resid_gap = wg[year] - gy.sum()
            resid_fossil = wf.loc[year] - obs.xs(year, level="year")[FOSSIL].sum()
            for rule in ["F0", "F1", "F1nat", "F1nocap", "F1marg", "F2", "F3", "F4", "F5"]:
                if rule == "F0":
                    rows.append(dict(rule=rule, techset=tset, iso="WORLD", year=year, gap=wg[year],
                                     **{f: wg[year] * wmix.loc[year, f] for f in FOSSIL}))
                    continue
                rows.append(dict(rule=rule, techset=tset, iso="ROW_residual", year=year, gap=resid_gap,
                                 **{f: resid_gap * wmix.loc[year, f] for f in FOSSIL}))
            # --- country rules
            pool = [i for i in EUROPE_POOL if i in present]
            singles = [i for i in present if i not in pool]
            for rule in ["F1", "F1nat", "F1nocap", "F1marg"]:
                groups = ([pool] if rule in ("F1", "F1marg") else [[i] for i in pool]) + [[i] for i in singles]
                cap_on = rule != "F1nocap"
                for grp in groups:
                    g_tot = gy[grp].sum()
                    if g_tot <= 0:
                        for m in grp:
                            rows.append(dict(rule=rule, techset=tset, iso=m, year=year, gap=0.0, coal=0.0, gas=0.0, oil=0.0))
                        continue
                    o_grp = obs.loc[[(m, year) for m in grp]][FOSSIL]
                    if rule == "F1marg":
                        adj = o_grp.copy()
                        for m in grp:
                            if meta.loc[m, "OECD"] == 1 and year >= 2010:
                                adj.loc[(m, year), "coal"] *= 1 - brown.get((m, year), 0.0)
                        tot = adj.sum()
                    else:
                        tot = o_grp.sum()
                    w = (tot / tot.sum()).to_dict() if tot.sum() > 0 else None
                    if w is None:  # no dispatchable fossil: regional mix
                        reg = regions.get(grp[0])
                        rm = obs.xs(year, level="year").loc[[i for i in present if regions.get(i) == reg]][FOSSIL].sum()
                        w = (rm / rm.sum()).to_dict()
                        diag.append({"techset": tset, "iso": ",".join(grp), "year": year, "rule": rule,
                                     "note": f"no fossil; regional ({reg}) mix used for {g_tot:.2f} TWh"})
                    res, sp_other, nb = fill_group(g_tot, w, obs, hroom, grp, capgw, year, cap_on)
                    if sp_other > 0 or nb > 0:
                        diag.append({"techset": tset, "iso": ",".join(grp) if len(grp) < 4 else "EUROPE_POOL",
                                     "year": year, "rule": rule, "spill_other_fuel_TWh": sp_other, "newbuild_TWh": nb})
                    for m in grp:
                        r = res.loc[m]
                        rows.append(dict(rule=rule, techset=tset, iso=m, year=year, gap=gy[m] if len(grp) == 1 else gy[m],
                                         coal=r.coal + r.nb_coal, gas=r.gas + r.nb_gas, oil=r.oil,
                                         nb_coal=r.nb_coal, nb_gas=r.nb_gas))
            for m in present:
                gm = gy[m]
                o = obs.loc[(m, year)]
                # F2 build margin (national, no caps)
                mix = None
                try:
                    now, then = capgw.loc[(m, year)], capgw.loc[(m, year - NEWBUILD_WINDOW)]
                    add = {f: max(now[f] - then[f], 0) if pd.notna(now[f]) and pd.notna(then[f]) else 0 for f in ("coal", "gas")}
                    cfs = {f: o[f] / (now[f] * 8.76) if now[f] and now[f] > 0 else 0 for f in ("coal", "gas")}
                    genadd = {f: add[f] * cfs[f] for f in add}
                    if sum(genadd.values()) > 0:
                        mix = {"coal": genadd["coal"] / sum(genadd.values()), "gas": genadd["gas"] / sum(genadd.values()), "oil": 0.0}
                except KeyError:
                    pass
                if mix is None:
                    s = o[FOSSIL].sum()
                    mix = {f: o[f] / s for f in FOSSIL} if s > 0 else {"coal": 0, "gas": 1, "oil": 0}
                rows.append(dict(rule="F2", techset=tset, iso=m, year=year, gap=gm, **{f: gm * mix[f] for f in FOSSIL}))
                rows.append(dict(rule="F3", techset=tset, iso=m, year=year, gap=gm, coal=gm, gas=0.0, oil=0.0))
                rows.append(dict(rule="F4", techset=tset, iso=m, year=year, gap=gm, coal=0.0, gas=gm, oil=0.0))
                # F5 fixed 2005 shares (national; techset-independent, recorded under each)
                try:
                    g05 = gen.loc[(m, BASE)].fillna(0)
                    gt = gen.loc[(m, year)].fillna(0)
                    tot05, tott = g05.sum(), gt.sum()
                    if tot05 > 0:
                        cf5 = g05 / tot05 * tott
                        d = cf5 - gt
                        # dispatchable-oil share of Other Fossil held at observed ratio
                        of_ratio = o["oil"] / gt["Other Fossil"] if gt["Other Fossil"] > 0 else 1.0
                        rows.append(dict(rule="F5", techset=tset, iso=m, year=year,
                                         gap=-(d[techs].sum()), coal=d["Coal"], gas=d["Gas"],
                                         oil=d["Other Fossil"] * of_ratio))
                except KeyError:
                    pass

    out = pd.DataFrame(rows).fillna({"nb_coal": 0.0, "nb_gas": 0.0})
    out.to_csv(D / "fill_by_country.csv", index=False)
    dg = pd.DataFrame(diag)
    dg.to_csv(D / "fill_diagnostics.csv", index=False)
    print(f"wrote {len(out)} rows; carried 2024->2025 for {len(carried)} countries")
    s = out[(out.year.isin([2015, 2024, 2025]))].groupby(["techset", "rule", "year"])[["gap", "coal", "gas", "oil", "nb_coal", "nb_gas"]].sum().round(0)
    print(s.loc["wso"])
    print(s.loc["ws"].xs(2025, level="year"))


if __name__ == "__main__":
    main()
