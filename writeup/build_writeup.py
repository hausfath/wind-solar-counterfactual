"""Build the rebound write-up PDF. Every number in the text is filled from the pipeline outputs in the repo
(wind-solar-counterfactual/data); {{key}} placeholders in writeup_template.md are replaced below.

Usage: python3.13 build_writeup.py   ->  rebound_writeup.html, rebound_writeup.pdf
Requires pandoc and Google Chrome (headless print to PDF) in addition to the Python requirements.
"""
import re
import subprocess
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
# works both inside the repo (writeup/) and in the working copy (power_mix/counterfactual/rebound/writeup/)
REPO = HERE.parent if (HERE.parent / "data" / "rebound_scenarios.csv").exists() else HERE.parents[3] / "wind-solar-counterfactual"
D = REPO / "data"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# The critique's stated numbers (as posted; not computed here). Confirm against the original before sharing.
CRITIC_STATED = dict(dr_lo="0.09", dr_hi="1.0", crit_f="29", crit_f_lo="11", crit_f_hi="50", crit_lo="4", crit_hi="17", crit_c="16")
# China coal 2024, physical tonnes (news reports of NBS and customs releases)
CN_OUTPUT_MT, CN_IMPORT_MT = 4760.0, 542.7


def values():
    S = pd.read_csv(D / "rebound_scenarios.csv").set_index("scenario")
    T = pd.read_csv(D / "fair" / "rebound_dT.csv")
    seg = pd.read_csv(D / "rebound_segments_2025.csv").set_index(["fuel", "segment"])
    hn = pd.read_csv(D / "headline_numbers.csv", index_col=0).value
    fill = pd.read_csv(D / "fill_by_country.csv")
    fill = fill[(fill.rule == "F1") & (fill.techset == "wso")]
    ef = pd.read_csv(D / "emission_factors.csv")
    t = lambda n, y=2050, c="p50": T[(T.scenario == n) & (T.year == y)][c].iloc[0]
    g = lambda n: S.loc[n].cum_Gt
    C, H = "Central (all channels)", "Headline"
    AGG = "Alternative: whole-market coal elasticity (s = 1 for coal)"
    head, cen = g(H), g(C)
    steps = [g(H), g("1 cycling"), g("2 + electricity rebound"), g("3 + fuel-market rebound")]
    obs25 = hn["obs2025"]
    # fill intensity in 2025 (t/MWh), from 13_rebound fill rows
    import importlib, sys
    sys.path.insert(0, str(REPO / "scripts"))
    rb = importlib.import_module("13_rebound")
    F = rb.fill_co2()
    f25 = F[F.year == 2025]
    # electrification netting (r only) at central and high r
    M, V, life = rb.markets(), rb.vre_share(), rb.lifecycle()
    cum = lambda **kw: (rb.run(F, M, V, **kw).groupby("year").avoided.sum() + life).sum() / 1000
    phi_cen = cum(only={"r"}, case={"phi": 0}) - cum(only={"r"})
    phi_hi = cum(only={"r"}, case={"r": 2, "phi": 0}) - cum(only={"r"}, case={"r": 2})
    gap25 = fill[fill.year == 2025]
    v = dict(
        head=f"{head:.1f}", head_r=f"{head:.0f}", cen=f"{cen:.1f}", cen_r=f"{cen:.0f}",
        cut_pct=f"{100 * (1 - cen / head):.0f}", lo=f"{g('All low'):.1f}", hi=f"{g('All high'):.1f}",
        alt=f"{g(AGG):.1f}", crit=f"{g(chr(67) + 'ritic' + chr(39) + 's construction (integrated markets, s = 1)'):.1f}",
        s_c=f"{steps[0] - steps[1]:.1f}", s_r=f"{steps[1] - steps[2]:.1f}", s_f=f"{steps[2] - steps[3]:.1f}",
        y25_head=f"{S.loc[H].y2025_Gt:.1f}", y25_cen=f"{S.loc[C].y2025_Gt:.1f}",
        pct25_head=f"{100 * S.loc[H].y2025_Gt / obs25:.0f}", pct25_cen=f"{100 * S.loc[C].y2025_Gt / obs25:.0f}",
        c_cen=f"{100 * S.loc[C].c_eff:.0f}", c_lo=f"{100 * S.loc['c|low'].c_eff:.0f}", c_hi=f"{100 * S.loc['c|high'].c_eff:.0f}",
        r_cen=f"{100 * S.loc['r|central'].r:.1f}", r_lo=f"{100 * rb.elec_r(0):.1f}", r_hi=f"{100 * S.loc['r|high'].r:.1f}",
        kaff=f"{100 * rb.P['cyc_ref'][1]:.1f}", kaff_static=f"{100 * rb.P['cyc_ref'][0]:.1f}",
        ef_fill=f"{f25.co2.sum() / f25.twh.sum():.2f}", phi_cen=f"{phi_cen:.2f}", phi_hi=f"{phi_hi:.1f}",
        f_coal=f"{100 * S.loc[C].f_coal:.0f}", f_gas=f"{100 * S.loc[C].f_gas:.0f}", f_oil=f"{100 * S.loc[C].f_oil:.0f}",
        f_all=f"{100 * S.loc[C].f_all:.0f}", f_coal_agg=f"{100 * S.loc[AGG].f_coal:.0f}",
        oat_agg=f"{g(AGG) - cen:.1f}".replace("-", "−"),
        oat_r_hi=f"{g('Electricity-demand rebound|high'):.1f}", oat_r_lo=f"{g('Electricity-demand rebound|low'):.1f}",
        wb=f"{cen - g('EU ETS waterbed|high'):.1f}",
        t_head=f"{t(H):.4f}", t_head_lo=f"{t(H, c='p5'):.4f}", t_head_hi=f"{t(H, c='p95'):.4f}",
        t_cen=f"{t(C):.4f}", t_cen_lo=f"{t(C, c='p5'):.4f}", t_cen_hi=f"{t(C, c='p95'):.4f}",
        t25_cen=f"{t(C, 2025):+.4f}",
        cn_import=f"{100 * CN_IMPORT_MT / (CN_OUTPUT_MT + CN_IMPORT_MT):.0f}",
        cn_dq=f"{100 * seg.loc[('coal', 'China')].delta_over_Q0:.0f}",
        cn_gap=f"{100 * gap25[gap25.iso == 'CHN'].gap.sum() / gap25.gap.sum():.0f}",
        **CRITIC_STATED,
    )
    # sanity checks on claims worded in the text
    assert 15 <= float(v["cut_pct"]) <= 19, "text says 'around a sixth'"
    assert g("All high") / head < 0.5, "text says 'more than half' in the most pessimistic case"
    assert abs(g(AGG) - float(CRITIC_STATED["crit_c"])) < 1.5, "text says the whole-market case is close to the critique"
    assert S.loc[C].f_coal < S.loc[C].f_gas < S.loc[C].f_oil, "text orders coal < gas < oil"
    return v


def main():
    v = values()
    md = (HERE / "writeup_template.md").read_text()
    md = md.replace("will matter more, not less, as", "will matter more over time as")
    md = md.replace("FIG/", str(REPO / "figures") + "/")
    keys = set(re.findall(r"\{\{(\w+)\}\}", md))
    missing = keys - set(v)
    assert not missing, missing
    for k in keys:
        md = md.replace("{{" + k + "}}", v[k])
    (HERE / "_filled.md").write_text(md)
    html = HERE / "rebound_writeup.html"
    subprocess.run(["pandoc", str(HERE / "_filled.md"), "-s", "-o", str(html), "--css", "style.css",
                    "--metadata", "pagetitle=Rebound effects and wind and solar", "--embed-resources",
                    "--resource-path", str(HERE)], check=True)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={HERE / 'rebound_writeup.pdf'}", html.as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (HERE / "_filled.md").unlink()
    print("wrote", HERE / "rebound_writeup.pdf")
    for k in sorted(v):
        print(f"  {k} = {v[k]}")


if __name__ == "__main__":
    main()
