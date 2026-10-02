# METHODS: electricity without renewable growth after 2005

All numbers below come from the pipeline in `scripts/` and are written to `data/headline_numbers.csv`,
`data/fair/summary.csv` and `data/regional_decomp.csv`. The SO2/NOx central case uses the CEDS inventory
(higher co-emissions, so conservative toward the avoided-warming claim). Official lower China/India values are
run as a sensitivity.

## Question and counterfactual

What would power-sector fossil generation and emissions have been had
**wind, solar and geothermal/other renewables** (Ember `Wind`, `Solar`,
`Other Renewables`) stayed at their 2005 generation in every country, with
electricity demand, nuclear, hydro and bioenergy as observed? Frozen at 2005
TWh implies repowering of the 2005 fleet. Bioenergy frozen too is a
sensitivity (`wsob`); wind + solar only is another (`ws`).

## Pipeline

| Script | Does | Output |
|---|---|---|
| `00_power_mix.py` | Global generation-share charts and the IEA-growth-based 2026 estimate | `figures/power_mix_*.png` |
| `01_extract_ceds.py` | Streams CEDS v_2025_03_18 detailed zip, keeps 1A1a / 1B1 / 1B2, 2000–2023 | `data/ceds_*.csv` |
| `02_extract_ember.py` | Ember yearly release subset | `data/ember_subset_2000_2025.csv` |
| `03_build_fill.py` | Gap per country-year and fill by rule | `data/fill_by_country.csv`, `fill_diagnostics.csv` |
| `04_emission_factors.py` | Country-year-fuel factors per MWh | `data/emission_factors.csv` |
| `05_emissions.py` | Δ emissions by rule/techset/year/species | `data/delta_emissions.csv`, `delta_by_country.csv` |
| `06_validate.py` | Checks V1–V6 | `data/validation_summary.csv` |
| `07_fair.py` | Paired FaIR runs, 28 scenarios | `data/fair/dT_members.npz`, `erf_members.npz`, `dT_percentiles.csv` |
| `08_analyze.py` | Checks C1–C5, EF-uncertainty sampling, summary | `data/fair/checks.csv`, `summary.csv`, `headline_with_ef_uncertainty.csv`, `analysis_report.txt` |
| `09_figures.py` | Three figures | `figures/*.png`, `data/headline_numbers.csv` |
| `10_regional.py` | US/UK/EU decomposition + counterfactual, fig4 | `data/regional*.csv`, `figures/fig4_regional.png` |

Python 3.13 with pandas 2.2, numpy 2.2, matplotlib 3.10 and FaIR 2.2.2 (see `requirements.txt`).

## Data sources

- **Ember yearly electricity data**, full release long format (downloaded
  2026-09-27, last-modified 2026-06-23). CC-BY-4.0. Generation, capacity by
  fuel per country 2000–2025; 2025 reported for 91 countries.
  https://ember-energy.org/data/yearly-electricity-data/
- **CEDS v_2025_03_18**, emissions by country, sector and fuel, 2000–2023
  (latest CEDS emissions release at download; CC-BY-4.0).
  https://zenodo.org/records/15059443
- **US EIA** Monthly Energy Review (Aug 2026) Table 11.6 (electric power CO2
  by fuel) and Table 7.2b (electric power net generation).
  https://www.eia.gov/totalenergy/data/monthly/
- **China**: MEE 《2023年电力二氧化碳排放因子》 national fossil power EF 0.8273
  kgCO2/kWh; NDRC/NEA 《全国煤电机组改造升级实施方案》 (2021): net coal
  consumption for power supply 305.5 gce/kWh (2020), −64.5/−27.5/−9.9 vs
  2005/2010/2015; CEC 《中国电力行业年度发展报告2025》: 302.4 gce/kWh (2024), +0.51 y/y.
- **India** CEA CO2 Baseline Database v21.0: coal 0.969 tCO2/MWh (FY2024-25),
  used as a cross-check only.

## Gap

`gap(c,t) = Σ_tech max(RE_tech(c,t) − RE_tech(c,base), 0)` with base 2005 (or
a country's first reported year), computed per technology only where
reported (Ember `Other Renewables` is NaN for some countries; never filled
with 0). Negative gaps are set to 0 (12 countries, all < 0.6 TWh).
2025: 123 non-reporting countries carry 2024 forward; a `ROW_residual`
bucket routes World − Σ countries through the World-average mix so totals
equal Ember World exactly (residual 0–17 TWh/yr).

## Fill rules

Fill is by **dispatchable** fossil only. Ember `Other Fossil` mixes oil
with waste and manufactured gases. Dispatchable oil TWh = min(Other Fossil,
CEDS 1A1a oil CO2 / 0.80 t/MWh); the rest gets zero weight.

- **F1 (headline)**: country-year dispatchable fossil mix; **Europe pooled**
  (EU27 excl. CYP/MLT + GBR, NOR, CHE, Western Balkans). Pooled fill of each
  fuel is allocated to members in proportion to their generation of that fuel.
  Per-fuel capacity caps (CF coal 0.80, gas 0.85, oil 0.60, or the observed
  CF if higher). Excess goes (i) to other fossil headroom in the same
  country or pool, then (iii) to new build in the fuel of trailing 5-yr net
  coal/gas capacity additions (gas if none).
- **F1nat**: F1 without pooling. **F1nocap**: F1nat without caps.
- **F1marg**: F1 with lignite (CEDS brown-coal share of 1A1a coal CO2)
  removed from the coal weight in OECD countries from 2010 (must-run
  lignite is not marginal); gas-heavier.
- **F2**: build margin (trailing 5-yr net additions × CF); low information
  (GEM excludes plants retired before 2020; pre-2010 capacity biased).
- **F3/F4**: coal-only / gas-only bounds. **F5**: all shares fixed at 2005
  (a different counterfactual that also undoes coal-to-gas switching,
  nuclear and hydro changes). **F0**: World-average mix (Ember's method).

Diagnostics (2024, F1): new build only material in Brazil (56 TWh gas); the
implied coal capacity factor in China rises from 0.57 to 0.74, in India from 0.72 to 0.80, in Germany (pooled)
0.38→0.74.

## Emission factors

**Why not Ember's**: its methodology says it aims "to include full lifecycle
emissions including upstream methane, supply chain and manufacturing
emissions … converted into CO2 equivalent", with CH4 at GWP 21. Gas factors
are constant in time (Jordaan et al. 2022, 2017 values). Using them would double
count CH4 and miss fleet efficiency changes.

**Why not raw CEDS CO2 / TWh**: CEDS 1A1a totals are right (14.74 Gt in 2023,
electricity and heat), but its split of electricity vs heat is inconsistent
across countries. China books 2.74 of 5.64 Gt of power-sector coal CO2 as
"Heat-production", which would give an impossible 503 g/kWh for electricity
alone. Poland and Russia book nearly all as heat, and Japan/Korea come out
at ~0.71 t/MWh. **Allocation, not the total, forced the approach below.**

CO2 per MWh (combustion):
- USA: EIA electric-power CO2 / net generation (coal 0.996→1.038, gas
  0.467→0.416 t/MWh, 2005→2024), interpolated.
- China coal: MEE 2023 fossil power EF (0.8273) × gce(t)/gce(2023),
  interpolated between 370 (2005), 333 (2010), 315.4 (2015), 305.5 (2020),
  301.9 (2023), 302.4 (2024): 1.014 → 0.829 t/MWh. Caveat: the gce series
  covers all ≥6 MW thermal plants (coal ~ 90%+); MEE basis (net vs gross)
  not confirmed, ±5%.
- Others: CEDS 1A1a electricity subsectors / Ember TWh if inside plausibility
  band (coal 0.75–1.25, gas 0.33–0.65, oil 0.60–1.00); else
  **Ember-scaled** = k_f × Ember's country intensity, with k_f the generation-
  weighted median of accepted/Ember (coal 1.02, IQR 0.93–1.06; gas 0.81,
  IQR 0.77–0.87, consistent with Ember gas including ~20% upstream CH4;
  oil 1.20). 2024–25 hold 2023.
- Share of F1 cumulative fill CO2 by factor source: MEE/CEC 38%, EIA 17%,
  CEDS 29%, Ember-scaled 16%.

SO2, NOx, BC, OC: per-fuel ratio to CO2 within CEDS 1A1a (electricity
subsectors if they hold ≥30% of the fuel's 1A1a CO2, else all 1A1a), times
the CO2 factor. The ratio carries the control-technology time trend and is
robust to heat/electricity booking. Ratios are capped at the 99th percentile. Examples
(g/kWh coal, 2005/2015/2023): China SO2 7.1/0.81/0.20; USA 4.4/1.6/1.1;
India 6.5/5.7/4.3; China NOx 4.4/1.1/0.49.

Upstream CH4: coal = CEDS 1B1 / all-sector coal CO2 (country-specific for
CHN, IND, USA; global elsewhere) × coal CO2 factor. Gas = global CEDS 1B2b
(production + distribution) / global gas CO2. Oil = global 1B2. Gas ≈ 1.6–2.5
kg CH4/MWh (≈1% leakage, CEDS basis; IEA Methane Tracker is higher, so a
high-leakage case is represented here only by a round-number ×2 bound, `F1_full_CH4x2`). Caveat: CEDS 1B1 includes
abandoned-mine CH4, which does not scale with extra coal burned (US coal
CH4/MWh rises over time for this reason).

RE lifecycle: frozen techs' Ember lifecycle intensity × gap, subtracted as
CO2 (amortized, central): −0.85 Gt cumulative. Front-loaded at installation (25-yr
life): −4.1 Gt (sensitivity). Bioenergy (wsob only): its own SO2/NOx/BC/OC are
subtracted using global CEDS 1A1a biomass per Ember bio TWh. Biogenic CO2 is
treated as neutral.

## Validation (06_validate.py)

| Check | Result |
|---|---|
| V1 Ember GER 2026 p.27 "4,065 MtCO2e" (W+S since 2000, 2025) | 4,067 Mt (+0.04%) with World-average fossil intensity net of W+S lifecycle. PASS |
| V2 Σ countries vs World per fuel 2005–2024 | coal 0.22%, gas 0.12%, wind 0.04%, solar 0.36%, other fossil 0.66% (2024; residual bucket absorbs). PASS except other fossil (tol 0.5%) |
| V3 observed power CO2 within [CEDS elec-only, CEDS 1A1a incl heat] | 2005 9.82 ∈ [7.87, 10.95]; 2023 13.11 ∈ [10.22, 14.74] Gt. PASS all years, but the band is wide (weak test). Stronger statement: our combustion total is 6% below Ember's lifecycle CO2e (13.95 Gt, 2023), the right direction and roughly the right size given Ember's upstream-CH4 content |
| V4a USA power SO2/NOx vs EPA NEI "Fuel Comb – Electric Generation" (national_state_sector_2002_2025_04sep2026_tons.xlsx, short tons ×0.907) | SO2 +1% (2005), +4% (2015), +12% (2020), +19% (2023); NOx within ±4% all years. PASS to 2015, drifting high after |
| V4b China power vs CEC 《电力行业年度发展报告2023》 (2022: SO2 0.476 Mt, NOx 0.762 Mt; coal units 83 mg SO2 and 133 mg NOx/kWh) | ours (CEDS-based) 2022: SO2 1.16 Mt (2.4×), NOx 3.10 Mt (4.1×); coal 0.207 g SO2 and 0.517 g NOx/kWh. **FAIL: CEDS well above CEC official (CEMS-based) figures** |
| V4c India coal power SO2 vs CREA bottom-up from CEA data (Jun 2022–May 2023: 4.33 Mt) | ours 6.2–6.3 Mt (+45%). **FAIL (high)**; CREA is not an official total |
| V4d EU27 | ours 4.1 (2005) → 0.40 Mt (2023); not compared with an independent EU total |

V4 interpretation: where our SO2/NOx factors are wrong they are too **high**
(China after ~2015, India). Higher co-emissions mean more aerosol cooling in
the counterfactual and therefore *less* net avoided warming, so the CEDS-based
central case is conservative toward the claim. A **low-aerosol sensitivity**
(China coal SO2/NOx per kWh scaled to CEC from 2015; India SO2 scaled to CREA)
is required before publishing. Largest 2025 ΔSO2 contributors (F1): India
1.22, Turkey 0.51 (lignite, 19–28 g SO2/kWh in CEDS), China 0.44, South Africa
0.31, USA 0.26 Mt. China is 1.17 of 3.56 Mt ΔNOx in 2025.
Turkey, Serbia and Bosnia lignite (19–28 g SO2/kWh in CEDS, under the 99th-
percentile ratio cap) supply 0.83 of 4.48 Mt 2025 ΔSO2 from a small gap:
disproportionate to their share of the gap.

Low-aerosol case (`fill_lowaer` in 05_emissions.py, F1 wso): China coal SO2/NOx per kWh ramped
from CEDS (2014) to CEC 2022 per-kWh values (×0.40 SO2, ×0.26 NOx) by 2022
and held after; India SO2 ×0.69 (CREA). 2025 ΔSO2 4.48 → 3.84 Mt (−14%),
ΔNOx 3.56 → 2.69 Mt (−24%); cumulative ΔSO2 37.1 → 33.7 Mt (−9%), ΔNOx
25.8 → 22.1 Mt (−14%).
| V5 fill = gap for all rules except F5 | max error 0.000 TWh. PASS |

## Emission results (techset wso)

Cumulative 2006–2025 CO2 (Gt; fill + amortized lifecycle):

| Rule | ws | **wso** | wsob |
|---|---|---|---|
| F0 (World avg) | 23.3 | 23.7 | 27.6 |
| **F1 (headline)** | 22.7 | **23.1** | 26.8 |
| F1marg | 22.2 | 22.6 | 26.2 |
| F1nat | 22.3 | 22.6 | 26.2 |
| F2 | 19.6 | 19.9 | 23.2 |
| F3 coal | 29.3 | 29.7 | 34.4 |
| F4 gas | 14.9 | 15.1 | 17.5 |
| F5 fixed 2005 | 30.3 | 30.3 | 30.3 |

F1 2025 annual changes: CO2 +3.73 Gt, SO2 +4.5 Mt, NOx +3.6 Mt, CH4 upstream +13.2 Mt.
F1 cumulative by country: China 39%, USA 17%, India 6.5% (but 19% of ΔSO2),
Germany 4.9%, Poland 3.2%.


## FaIR setup

- FaIR v2.2.2, fair-calibrate v1.4.5 calibrated constrained ensemble (841
  members), emissions-driven, `ch4_method="Thornhill2021"`, 1750–2051, with the
  paired-run recipe (including a restore of FaIR's unit tables between runs, which FaIR 2.2.2 mutates when reading CSVs).
- Baseline emissions: `historical_1750-2025.csv`, then `medium-extension`
  offset-harmonised to 2025 (E_hist(2025) + E_ext(t) − E_ext(2025), floored at
  0; the raw extension steps, e.g. OC 36→25 Mt, SO2 71→77 Mt). Solar/volcanic
  forcing is `medium-extension` in every scenario.
- Perturbation: Δ from `delta_emissions.csv` is added to CO2 FFI (Gt), Sulfur (Mt
  SO2), NOx (Mt NO2), BC, OC (Mt, C mass as in CEDS) and CH4 (Mt) for
  2006–2025, and is zero after. Every scenario is differenced member-by-member
  against a base run in the same batch. ΔT is the counterfactual world
  minus the actual world, a difference, so **no baseline period** applies.
- After 2025 both worlds have identical emissions, so ΔT(2035/2050) is the
  *legacy* of 2006–2025 deployment only, not the effect of the renewables
  still running after 2025 (which would be much larger).

## FaIR checks (08_analyze.py)

| Check | Result |
|---|---|
| C1 zero perturbation | max \|ΔT\| = 0 exactly. PASS |
| C2 stochastic vs `stochastic_run=False` | max \|ΔΔT\| 1.1e-4 °C in the worst member (1.2% of median ΔT2050); median member 5e-6 °C; ensemble medians identical to 5 d.p. **FAIL against the strict 1e-6 target** set before the run; immaterial to results. The stochastic runs are kept as central (the calibrated configuration) |
| C3 linearity 2× / 0.5× | p95 member relative deviation 0.8% / 0.4%. PASS (<2%) |
| C4 additivity (sum of single-species runs vs joint) | p95 0.19%. PASS. Layer order does not matter |
| C5 quasi-TCRE, CO2-only ΔT(2050) per 1000 GtCO2 | median 0.38 (5–95%: 0.28–0.52) °C; inside AR6 likely range 0.27–0.63. PASS |

Because C3/C4 pass, emission-factor uncertainty is sampled by rescaling
each member's single-species responses: 20 draws per member (16,820
samples), with CO2 normal ±5% (90%), SO2/NOx/BC/OC independent lognormal
×/÷1.5 (90%), CH4 lognormal ×/÷2 (90%), seed 20260927. Fill rules (structural)
are never folded into this range.

## Temperature results

Headline (F1, wind+solar+geothermal, CEDS co-emissions), climate +
emission-factor uncertainty, median (5–95%):

| Year | All effects | CO2 only | P(all effects > 0) |
|---|---|---|---|
| 2025 | +0.0020 (−0.0080 to +0.0085) °C | +0.0074 (+0.0058 to +0.0091) °C | 66% |
| 2035 | +0.0098 (+0.0066 to +0.0147) °C | +0.0094 °C | 100% |
| 2050 | +0.0092 (+0.0066 to +0.0132) °C | +0.0088 (+0.0064 to +0.0119) °C | 100% |

All-effects values: `data/fair/headline_with_ef_uncertainty.csv`; CO2-only
values (climate-response range only): `data/fair/summary.csv`.

Median contributions (°C, 2025 → 2050, single-species runs): CO2 +0.0074 →
+0.0088; SO2 −0.0082 → −0.0005; CH4 (upstream) +0.0035 → +0.0018; NOx −0.0007
→ −0.0009 (via CH4 lifetime and ozone); BC +0.0001; OC ~0. ΔERF in 2025: CO2
+25, CH4 +3.4, ozone +6.3, aerosol-radiation −12.7, aerosol-cloud −11.2
mW/m² (medians).

Interpretation: under the headline
assumptions the median net effect is slightly negative through ~2022 (2010
−0.0005, 2015 −0.0011, 2020 −0.0009 °C; P>0 4%, 15%, 34%). In other words,
the extra coal's SO2 cooling would have outweighed its CO2 and CH4 warming.
This holds with official-low China/India SO2 (2015 −0.0010, 2020 −0.0006 °C)
but **not** with doubled upstream methane (2020 +0.0004 °C, P>0 56%) or with
gas-only fill (positive every year). So the sign before ~2023 is
uncertain and the magnitude (~±0.001 °C) is negligible. By 2025 the net effect is small
and positive in 66% of samples. Once the extra aerosols wash out (within a few
years after 2025) the CO2 legacy dominates at about +0.009 °C. The aerosol-cloud
spread across members dominates the near-term uncertainty.

Scope note: the frozen set is wind + solar + geothermal/other. Geothermal/other is 0.75%
of the 2025 gap and 1.5% of the cumulative gap, so figures say "wind and solar".
Hydro (+~1,500 TWh since 2005) and bioenergy (+~500 TWh) are held at observed.

Sensitivities (ΔT 2050 median, °C; cumulative ΔCO2 Gt): coal-only 0.0114
(29.7); gas-only 0.0067 (15.1); World-average 0.0090 (23.7); build margin
0.0080 (19.9); no pooling 0.0090 (22.6); lignite excluded 0.0090 (22.6); wind+solar
only 0.0090 (22.7); +bioenergy 0.0106 (26.8, bio co-emissions excluded; with
them 0.0110 and a 2025 upper tail of +0.027, driven by CEDS biomass BC/OC
of ~2.5 g OC/kWh in China, which looks implausible, and the fat BC
aerosol-cloud tail); official-low SO2/NOx 0.0093 (2025: +0.0026, P>0 75%);
front-loaded manufacturing emissions 0.0079 (19.8); CH4 ×2 0.0109; fixed 2005
shares 0.0114 (30.3, a different counterfactual).

## Regional declines (10_regional.py)

Observed power-sector combustion CO2, which is Ember TWh × our country-year factors, for the US, UK and EU27. It
is decomposed 2005→2025 with an exact two-factor midpoint split. CO2 = F × I, where F is fossil generation and I
is fossil intensity. F = D − WS − O, where D is total generation (so it includes net imports), WS is wind + solar
+ geothermal/other RE, and O is nuclear + hydro + bio. That gives
ΔCO2 = Ī·ΔD − Ī·ΔWS − Ī·ΔO + F̄·ΔI. The counterfactual column uses rule F1nat (national fill, so each region's
counterfactual stays inside it), with fill plus amortized lifecycle, for 2025.

| Region | Power CO2 2005 → 2025 (Mt) | Demand | Wind+solar | Nuclear/hydro/bio | Coal→gas & efficiency | Without W+S growth, 2025 |
|---|---|---|---|---|---|---|
| United States | 2,465 → 1,548 (-37%) | +352 | -606 | +20 | -682 | 2,050 (-17%) |
| United Kingdom | 191 → 48 (-75%) | -58 | -56 | +7 | -36 | 90 (-53%) |
| European Union | 1,087 → 486 (-55%) | -61 | -512 | +97 | -126 | 916 (-16%) |

Notes:
- UK generation fell 27% and demand 21%; the difference is higher net imports.
- EU nuclear output fell 264 TWh (Germany's went from 163 TWh to 0). Bioenergy rose 97 TWh and hydro 20 TWh.
- US emissions rose from 2024 to 2025 (coal generation rose); with 2024 as the endpoint the decline is 40%.
- Validation of observed totals: US 2005 2,465 / 2024 1,485 Mt against the EIA electric power sector at about 2,400 /
  1,421 Mt (−41% vs our −40%). UK −76% (2005–24). EU27 −55% against −50% in Ember's lifecycle series.
- The decomposition's wind + solar term uses average fossil intensity, while the counterfactual uses each
  country's fill mix and nets manufacturing emissions, so the two differ somewhat. EU: 512 Mt in the
  decomposition vs 430 Mt in the counterfactual.
- Global fossil generation 2025 vs 2024: −0.3% (Ember).

## Comparing to Ember's 4,065 Mt

Our 2025 F1 3.73 Gt differs from Ember's GER 2026 figure on three axes: base
year (2005 vs 2000), CO2 combustion vs lifecycle CO2e, and country fossil mix
vs World average. V1 reproduces Ember on Ember's terms. Never put the two
numbers side by side without saying so.

## Caveats

- Coal-to-gas switching and RE growth were jointly determined (Fell &
  Kaffine 2018); F1 treats observed switching as exogenous.
- Demand held at observed levels. Without RE, prices would be higher and demand lower, so
  holding demand fixed errs toward overstating avoided emissions (not quantified).
- EU ETS waterbed pre-2018 (not modelled); nuclear retirements held at observed levels.
- fair-calibrate v1.4.5 history is very likely CEDS v_2024_07_08 (inferred
  from repo folders, not stated); our factors use v_2025_03_18. Our Δ is a
  perturbation on top of that history, so the version mismatch affects only
  the baseline state, not the Δ.
- China gross vs net generation basis (MEE factor vs Ember China TWh) not
  yet confirmed: ±5% on China CO2 (39% of the total).
- 1,521 country-fuel-years with fill but no factor (fuel absent in Ember)
  use the World-average factor (small: ~100 TWh per rule over 20 years).
