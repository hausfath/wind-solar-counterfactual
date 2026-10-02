"""Checks and summary statistics for the FaIR runs (07_fair.py output).

Checks (-> ../data/fair/checks.csv):
  C1 zero perturbation: max |dT| == 0.
  C2 stochastic_run=False vs default for F1_full: max |ddT| (target <= 1e-6 degC).
  C3 linearity: per member, max_t |dT(2x) - 2 dT(1x)| / max_t |2 dT(1x)|,
     likewise 0.5x; accept if the 95th percentile across members < 2%.
  C4 additivity: sum of single-species runs vs joint F1_full, same metric < 2%.
  C5 CO2-only dT(2050) per 1000 GtCO2 cumulative dCO2 (quasi-TCRE, since dCO2
     = 0 after 2025 and zero-emissions commitment is small), compared with the
     AR6 likely TCRE range 0.27-0.63 degC per 1000 GtCO2 (reported, not asserted).

Emission-factor uncertainty (headline F1, joint with the 841 members, only
valid if C3/C4 pass): dT_i = sum_s m_{s,i} dT_{s,i} with per-member
multipliers drawn 20 times per member (seed 20260927):
  CO2   normal, sd 0.05/1.645 (90% range +/-5%)
  SO2, BC, OC, NOx   lognormal, sigma ln(1.5)/1.645 (90% range x/÷1.5), independent
  CH4   lognormal, sigma ln(2)/1.645 (90% range x/÷2)
Fill-rule (structural) uncertainty is never folded in: rules are reported
as separate scenarios.

Outputs: ../data/fair/checks.csv, ../data/fair/summary.csv,
         ../data/fair/headline_with_ef_uncertainty.csv, printed report.
Temperatures are differences (counterfactual minus observed world), so no baseline period applies.
"""
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
F = D / "fair"
z = dict(np.load(F / "dT_members.npz"))
years = z.pop("years")
yi = {y: i for i, y in enumerate(years)}
PCT = [5, 50, 95]
checks = []


def chk(name, value, target, ok, note=""):
    checks.append(dict(check=name, value=value, target=target, passed=bool(ok), note=note))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {value:.3g} (target {target}) {note}")


def rel_dev(a, b):
    """per-member max_t |a-b| / max_t |b| over 2006-2050"""
    sl = slice(yi[2006], yi[2050] + 1)
    return np.abs(a[sl] - b[sl]).max(0) / np.abs(b[sl]).max(0)


# ---- checks
chk("C1 zero perturbation max|dT| (degC)", np.abs(z["zero"]).max(), "0", np.abs(z["zero"]).max() == 0)
dd = np.abs(z["F1_full_nostoch"] - z["F1_full"])
d = dd.max()
chk("C2 stochastic vs non-stochastic max|ddT| (degC)", d, "<=1e-6", d <= 1e-6,
    f"(median member {np.median(dd[yi[2050]]):.1e}; worst member = "
    f"{d / abs(np.median(z['F1_full'][yi[2050]])):.1%} of median dT2050; ensemble medians "
    f"{np.median(z['F1_full'][yi[2050]]):.5f} vs {np.median(z['F1_full_nostoch'][yi[2050]]):.5f})")
for k, s in [("F1_full_x2", 2.0), ("F1_full_x05", 0.5)]:
    r = rel_dev(z[k], s * z["F1_full"])
    chk(f"C3 linearity {k}: p95 member rel. deviation", np.percentile(r, 95), "<0.02", np.percentile(r, 95) < 0.02,
        f"(median {np.median(r):.4f})")
singles = ["F1_CO2", "F1_SO2", "F1_BC", "F1_OC", "F1_NOx", "F1_CH4"]
ssum = sum(z[s] for s in singles)
r = rel_dev(ssum, z["F1_full"])
chk("C4 additivity sum(singles) vs joint: p95 rel. deviation", np.percentile(r, 95), "<0.02", np.percentile(r, 95) < 0.02,
    f"(median {np.median(r):.4f})")
de = pd.read_csv(D / "delta_emissions.csv")
cum = {}
for rule, ts, comps in [("F1", "wso", ["fill", "lifecycle_amortized"])]:
    cum["F1"] = de[(de.rule == rule) & (de.techset == ts) & de.component.isin(comps)].CO2.sum()
q = z["F1_CO2"][yi[2050]] / cum["F1"] * 1000
p = np.percentile(q, PCT)
chk("C5 quasi-TCRE from CO2-only run (degC/1000 GtCO2), median", p[1], "AR6 likely 0.27-0.63",
    0.27 <= p[1] <= 0.63, f"(5-95%: {p[0]:.3f}-{p[2]:.3f}; cum dCO2 {cum['F1']:.1f} Gt)")
pd.DataFrame(checks).to_csv(F / "checks.csv", index=False)

# ---- summary per scenario
comp_map = {"F1_full_frontlife": ("F1", "wso", ["fill", "lifecycle_frontloaded"]),
            "F1_full_nolife": ("F1", "wso", ["fill"]),
            "F1_full_lowaer": ("F1", "wso", ["fill_lowaer", "lifecycle_amortized"]),
            "ws_F1_full": ("F1", "ws", ["fill", "lifecycle_amortized"]),
            "wsob_F1_full": ("F1", "wsob", ["fill", "lifecycle_amortized", "bio_coemis"]),
            "wsob_F1_full_nobiocoemis": ("F1", "wsob", ["fill", "lifecycle_amortized"])}
rows = []
for n, a in z.items():
    if n in ("zero", "F1_full_nostoch"):
        continue
    if n in comp_map:
        r, ts, comps = comp_map[n]
    else:
        r, ts, comps = n.split("_")[0], "wso", ["fill", "lifecycle_amortized"]
    c = de[(de.rule == r) & (de.techset == ts) & de.component.isin(comps)].CO2.sum() if n.endswith("full") or n in comp_map else np.nan
    row = dict(scenario=n, cum_dCO2_Gt=c)
    for y in (2025, 2035, 2050):
        p = np.percentile(a[yi[y]], PCT)
        row.update({f"dT{y}_p5": p[0], f"dT{y}_p50": p[1], f"dT{y}_p95": p[2]})
    row["P_pos_2025"] = (a[yi[2025]] > 0).mean()
    rows.append(row)
S = pd.DataFrame(rows).set_index("scenario")
S.to_csv(F / "summary.csv")
pd.set_option("display.width", 200)
fmt = S.copy()
for c in fmt.columns:
    if c.startswith("dT"):
        fmt[c] = (fmt[c] * 1000).round(1)   # millikelvin for display
print("\nSummary (dT in 0.001 degC; cumulative dCO2 2006-2025 in Gt):")
print(fmt.round(2).to_string())

# ---- layers (median contributions) headline
print("\nHeadline layers F1 wso, median dT (0.001 degC):")
for n in ["F1_CO2", "F1_CO2aer", "F1_CO2aerNOx", "F1_full"]:
    print(f"  {n:14s} 2025 {1000*np.median(z[n][yi[2025]]):+.2f}  2035 {1000*np.median(z[n][yi[2035]]):+.2f}  2050 {1000*np.median(z[n][yi[2050]]):+.2f}")
print("Single-species median dT (0.001 degC):")
for n in singles:
    print(f"  {n:8s} 2025 {1000*np.median(z[n][yi[2025]]):+.2f}  2050 {1000*np.median(z[n][yi[2050]]):+.2f}")

# ---- EF uncertainty sampled jointly with members
rng = np.random.default_rng(20260927)
ND = 20
nm = z["F1_full"].shape[1]
sig_aer, sig_ch4 = np.log(1.5) / 1.645, np.log(2.0) / 1.645
mult = {"F1_CO2": rng.normal(1, 0.05 / 1.645, (ND, nm)),
        "F1_SO2": rng.lognormal(0, sig_aer, (ND, nm)), "F1_BC": rng.lognormal(0, sig_aer, (ND, nm)),
        "F1_OC": rng.lognormal(0, sig_aer, (ND, nm)), "F1_NOx": rng.lognormal(0, sig_aer, (ND, nm)),
        "F1_CH4": rng.lognormal(0, sig_ch4, (ND, nm))}
samp = sum(mult[s][:, None, :] * z[s][None, :, :] for s in singles)  # (ND, years, members)
samp = samp.transpose(1, 0, 2).reshape(len(years), -1)
out = []
for y in range(2006, 2051):
    a = samp[yi[y]]
    b = z["F1_full"][yi[y]]
    out.append(dict(year=y, **{f"p{q}": v for q, v in zip(PCT, np.percentile(a, PCT))},
                    **{f"climate_only_p{q}": v for q, v in zip(PCT, np.percentile(b, PCT))},
                    P_pos=(a > 0).mean(), P_pos_climate_only=(b > 0).mean()))
H = pd.DataFrame(out)
H.to_csv(F / "headline_with_ef_uncertainty.csv", index=False)
print("\nHeadline F1 full, climate + emission-factor uncertainty (0.001 degC):")
print((H.set_index("year").loc[[2010, 2015, 2020, 2025, 2030, 2035, 2040, 2050]]
       .assign(**{c: lambda d, c=c: d[c] * 1000 for c in H.columns if c.startswith(("p", "climate")) and "P_pos" not in c})).round(2).to_string())

# ---- ERF headline 2025
E = dict(np.load(F / "erf_members.npz"))
print("\nF1_full dERF 2025 by group, median (5-95%) mW/m2:")
for k, v in E.items():
    n, g = k.split("|")
    if n == "F1_full":
        p = np.percentile(v[yi[2025]], PCT) * 1000
        print(f"  {g:12s} {p[1]:+.2f} ({p[0]:+.2f} to {p[2]:+.2f})")
