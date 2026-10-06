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
| `11_china.py` | China actual vs counterfactual + annual generation-change breakdown (social figure) | `data/china.csv`, `figures/fig5_china.png` |
| `12_china_mix.py` | China generation mix (%), 1985–2025, from the OWID share data (social figure) | `figures/fig6_china_mix.png` |
| `01b_extract_ceds_sectors.py` | CEDS combustion CO2 by country, fuel and sector group (1A1bc has no fossil rows) | `data/ceds_co2_sector_groups.csv` |
| `13_rebound.py` | Rebound adjustments: cycling, electricity demand, fuel markets, EU ETS waterbed | `data/rebound_*.csv` |
| `14_rebound_fair.py` | Paired FaIR runs on the rebound-adjusted emissions | `data/fair/rebound_dT.csv` |
| `15_rebound_figures.py` | Waterfall, comparison and tornado figures | `figures/fig7–fig9_rebound_*.png` |

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

## China (11_china.py)

China's counterfactual is rule F1 (China is not pooled, so F1 = F1nat). Its fill is 94.7% coal cumulatively,
and coal was 93–98% of China's fossil generation in every year. A gas-only bound is therefore not shown.
- Power CO2: 2.05 Gt (2005) → 5.06 Gt (2025), +147%; −0.9% in 2025 vs 2024.
- Without wind and solar growth: 6.95 Gt in 2025 (+37%). Cumulative avoided 2006–2025: 9.3 Gt (fill net of
  amortized lifecycle).
- Demand grew 4.2-fold (2005–2025).
- 2025 vs 2024: demand +488 TWh. Wind + solar +474 TWh (97% of demand growth). Hydro, nuclear and bio +75 TWh.
  Fossil generation −58 TWh (−0.9%).
- Ember reports no 'Other Renewables' for China (treated as 0).

## Rebound adjustments (13_rebound.py, 14_rebound_fair.py, 15_rebound_figures.py)

Added in October 2026 after a published critique (Pielke Jr.) argued for displacement ratios below 1 and a
fossil-fuel price rebound of 29% (11–50%). A literature review and two reviews (statistics; energy economics) shaped
the design. Every number below is written by the scripts to `data/rebound_scenarios.csv`,
`data/rebound_segments_2025.csv` and `data/fair/rebound_dT.csv`.

**No displacement ratio is applied.** The counterfactual holds electricity demand at observed levels, so each MWh of
wind and solar is replaced 1:1 by construction. Cross-country panel coefficients (York 2012, Hu & Cheng 2017, Rather &
Mahalik 2023) regress fossil on non-fossil generation, mostly hydro and nuclear, with demand free to vary. They measure
a different quantity, and stacking one on a separate price rebound counts the demand response twice. Demand response
is modelled explicitly as channel 2 instead.

Three channels are applied in the central case, row by row (country, year, fuel), to the F1 fill. A fourth, the
EU ETS waterbed, enters the high case only. Lifecycle emissions are unchanged.
avoided = fill × (1 − c) × (1 − r) × (1 − f) × (1 − w).

1. **Cycling penalty c.** Backup fossil units ramp and run at part load, so the fuel saved per MWh of wind and solar is
   below the average-intensity value.
   - Kaffine, McBee & Ericson (2020, Energy J. 41(5)), Southwest Power Pool 2012–14 at about 10% wind share: static
     3.8%, dynamic 6.5% reduction in marginal CO2 savings.
   - c scales linearly with each country's actual wind+solar share, anchored at 10% and capped at 1.5× the anchor
     value. Low / central / high anchor value: 3.8 / 6.5 / 9%.
   - Fill-CO2-weighted c is 4.2 / 7.2 / 10.0%. A flat 7% (no scaling) is a sensitivity.
   - Suri, de Chalendar & Azevedo (arXiv:2408.05209, preprint) find 91–95% of expected displacement in CAISO and
     ERCOT at higher shares, so the scaled values near the cap are consistent with them.
2. **Electricity-demand rebound r.** If wind and solar lowered retail prices, demand in the actual world is higher than
   it would have been, so the counterfactual fill is too large.
   - r = |ε_e| × (−Δp) × D₂₀₂₅ / gap₂₀₂₅, held constant in time because the price effect scales with penetration.
   - Δp (net retail price change at 2025 penetration): +1% / −1% / −3%. Its sign is uncertain: renewable-support
     levies and US RPS raised retail prices (Greenstone & Nath: 11–17%), the merit-order effect lowered wholesale
     prices, and China's tariffs are regulated.
   - |ε_e|: 0.3 / 0.3 / 0.5. This gives r = −1.8% / +1.8% / +8.8%. With Δp > 0, r < 0, and the fill grows.
   - **Electrification netting** (sensitivity). Part of any price-induced demand is EVs or heat pumps displacing
     direct fossil use. A share φ of the extra demand displaces e = 0.7 t CO2/MWh: EV about 0.8 (0.20 kWh/km against
     0.16 kg CO2/km for petrol); heat pump about 0.67 (COP 3 against a 90% gas boiler at 0.20 t/MWh). Then
     r_row = r × (1 − φ e / EF_row).
   - φ is 0 in the central and high cases, because there is no direct estimate, and 0.4 in the low case. At the
     2025 fill intensity (0.72 t/MWh), φ = 0.4 removes about 40% of r. That recovers 0.16 Gt cumulative at central r
     and 0.82 Gt at high r.
3. **Fuel-market rebound f.** Less coal and gas burned for power lowers fuel prices, so other buyers burn more.
   - Solved per market from the actual-world market (CEDS 1A combustion CO2 as the fuel-quantity proxy, from
     `ceds_co2_sector_groups.csv`, 2023 held for 2024–25). The counterfactual adds price-inelastic power demand Δ.
   - Constant-elasticity equilibrium for the price ratio x: Q₀x^η = P₀ + Δ + Σ_k O_k x^(−ε_k), and
     f = Σ_k O_k(1 − x^(−ε_k))/Δ. Δ/Q₀ reaches 0.19 for China coal and 0.25–0.30 for rest-of-world and US coal in
     2025, so the exact solve is used. The linear limit S/(η + S) is a sensitivity, with S = Σ s_k|ε_k|.
   - The solver reproduces the reviewer's hand solutions: s 0.38, η 1.55, ε −0.5, Δ/Q₀ 0.27 gives x 1.151, f 0.096;
     s 0.25, η 3, ε −0.3 gives f 0.021.
   - **Markets.**
     - Coal: China, India, US, rest of world (seaborne-linked). 10 / 15 / 20% of China's extra coal and
       10 / 20 / 30% of India's is imported and enters the rest-of-world market.
     - Gas: North America; Europe (EU27 + UK, Norway, Switzerland); Asian LNG importers (JPN, KOR, TWN, IND); China;
       administered-price producers (Russia, Belarus, Iran, Iraq, Gulf states, Algeria, Libya, Egypt, Central Asia,
       Azerbaijan, Venezuela), where f = 0 except in the high case; rest of world, market- or LNG-priced (Brazil,
       Turkey, Australia, Chile, Argentina, ...).
     - Gas in oil-indexed contract eras has f = 0: Europe before 2012, Asian LNG before 2015. The high case ignores
       this.
     - Oil: one world market.
   - **Coal demand, central basis = elasticity by buyer group** (CEDS sectors):
     - Thermal non-power coal (industry, buildings, other): −0.2 / −0.3 / −0.5 in China and India, where non-power
       demand is capped by policy (steel output caps, cement capacity controls, residential coal bans), and
       −0.3 / −0.5 / −0.7 elsewhere.
     - Iron and steel (including coke) and heat plants: 0 / −0.1 / −0.1. These are regulated, must-run uses with
       no short-run substitute.
   - **Alternative: whole-market elasticity** (in the all-high case). Burke & Liao (2015, China Econ. Rev.
     36:309–322) estimate −0.3 to −0.7 (two-year response, 2012).
     - Their dependent variable is total provincial coal consumption *including power* (verified in the paper's
       appendix: "total primary coal consumption"). Power was about half of China's coal use.
     - Read literally, s × ε_nonpower = ε_agg, so the elastic share is s = 1 with ε = −0.3 / −0.5 / −0.7. This is
       the conservative reading (larger rebound).
     - It is not the central case, for two reasons. First, it is a provincial elasticity, so it includes
       reallocation between provinces, which does not change national use. Second, applied to the US (non-power
       share 6%) and the rest of world, it treats power-sector coal-to-gas switching as a full rebound, when gas
       emits about half as much.
   - **Coal supply η.**
     - China and India: ∞ / 3 / 1.55. Output is state-managed; NDRC's 2022 contract-price corridor is 570–770
       yuan/t (seen only in reports of the circular). Coal India sells at notified prices.
     - US and rest of world: 3 / 1.55 / 0.8.
     - No econometric thermal-coal supply elasticity was found. Richter, Mendelevitch & Jotzo (2018) use the
       COALMOD model and report none. These ranges are judgment.
   - **Gas.** Supply η 1.5 / 0.81 / 0.5 (Hausman & Kellogg 2015, long-run 0.81). Demand elasticities: industry,
     iron & steel and other at −0.3 / −0.45 / −0.6; buildings at −0.1 / −0.2 / −0.3; heat plants at
     0 / −0.1 / −0.1.
   - **Oil.** η 1.0 / 0.42 / 0.42, with OPEC+ management implying a higher effective η in the low case. ε −0.33
     (Prest et al. 2024). The oil fill is small.
   - Δ is our fill CO2 while Q₀ comes from CEDS, two different sources. The ratio is what matters.
4. **EU ETS waterbed w (high case only).** Under a fixed, binding cap, extra abatement in power frees allowances that
   are used elsewhere in the ETS.
   - **0 in the central case.** Treating the cap as fixed is circular for this counterfactual. The EU set its caps
     with expected renewables growth built in, so a world without wind and solar would have had a looser cap, or
     politically implausible carbon prices. The market was also heavily oversupplied in 2008–17, and much of that
     surplus was later cancelled through the Market Stability Reserve.
   - **High case:** share of EU-ETS countries' net avoided CO2 re-emitted is 0 in 2006–07 (Phase I allowances could
     not be banked), 20% in 2008–17 and 60% in 2018–25.
   - The 2018–25 value is near the top of Bruninx & Ovaere (2022, Nat. Commun. 13,
     [doi:10.1038/s41467-022-28398-2](https://doi.org/10.1038/s41467-022-28398-2)). For 1 Mt abated in 2020, they
     find invalidation of "≈ 0.42 MtCO2" if the waterbed is sealed by 2023 and "≈ 0.79 MtCO2" if sealed by 2030.
   - Perino (2018, NCC 8:262) describes the temporary puncture, but its numbers were not read (paywalled) and are
     UNVERIFIED.
   - Applied to the European countries in the pooled-Europe list. The UK ETS (2021+) and the Swiss link are treated
     like the EU ETS.

**Results, cumulative 2006–2025 (scenarios, not a probability interval).**

| Case | Avoided CO2 | % of headline | 2025 |
|---|---|---|---|
| Headline | 23.05 Gt | 100% | 3.73 Gt |
| Cycling only (central) | 21.33 | 93% | 3.37 |
| Electricity rebound only (central) | 22.63 | 98% | 3.66 |
| Fuel-market rebound only (central) | 21.10 | 92% | 3.44 |
| Waterbed only (high case) | 20.88 | 91% | 3.42 |
| **All channels, central** | **19.16** | **83%** | **3.04** |
| All low | 21.66 | 94% | 3.47 |
| All high (incl. waterbed and whole-market coal) | 10.45 | 45% | 1.69 |
| Alternative: whole-market coal elasticity | 16.75 | 73% | 2.69 |
| Linear small-change formula | 19.08 | 83% | 3.02 |
| Flat 7% cycling | 19.20 | 83% | 3.13 |
| Critic's construction (one world market per fuel, s = 1, η/ε coal 1.55/0.5, gas 0.81/0.5, oil 0.42/0.33, no other channels) | 16.56 | 72% | 2.71 |

- **Waterfall** (sequential, central): 23.05 → cycling −1.72 → electricity rebound −0.39 → fuel market −1.78 → 19.16.
- **Central f by fuel** (net-fill weighted): coal 3.6%, gas 17.5%, oil 42.5%; all fuels 8.2%.
- **2025 market detail** (central):
  - China coal: Δ/Q₀ 0.19, x 1.06, f 2.6%.
  - India coal: f 1.3%.
  - Rest-of-world coal: f 5.3%.
  - US coal: f 1.2%.
  - Gas: Europe 19.2%, North America 17.0%, rest of world 15.9%. Administered-price markets: 0.
- **One-at-a-time ranges** (figure 9) are largest for:
  - the whole-market coal reading (16.75, −2.4 Gt);
  - the electricity rebound (17.7–19.9);
  - the waterbed (17.4, high only);
  - cycling (18.6–19.8);
  - gas supply (18.8–19.5).
  Coal supply and demand elasticities each move the total by less than 0.5 Gt under the buyer-group basis.

The critic's integrated-market construction reproduces his numbers: 16.6 Gt cumulative against his ~16 Gt, and
2.71 Gt in 2025 against his ~2.6 Gt. Its f is 27% (net-fill-weighted, 2006–2025), against his 29%.

Our central fuel-market rebound is 8% (net-fill-weighted, 2006–2025). It is lower for four reasons:
- only non-power buyers rebound, and in China and India their demand is capped by policy;
- supply in China and India is managed;
- administered and oil-indexed gas markets have f = 0;
- the market changes are solved exactly.

Gas carries most of it, at 17.5%. Reading the coal elasticity as whole-market raises the total f to 19% and gives
16.75 Gt, close to the critic's ~16 Gt.

**Warming** (14_rebound_fair.py; paired FaIR runs, 841 members).
- **Scaling.** The fill's CO2 and upstream CH4 are scaled year by year by the retained fraction. SO2, NOx, BC and OC
  are scaled by (1 − c)(1 − r) only.
- **Avoided warming by 2050** (median, 5–95%):
  - headline +0.0091 °C (0.0069–0.0125);
  - central +0.0075 °C (0.0056–0.0101);
  - all low +0.0085;
  - all high +0.0036;
  - whole-market coal basis +0.0064;
  - critic's construction +0.0062.
- **2025:** central +0.0007 °C (P>0 58%), compared with the headline's +0.0016 °C (65%).
- **Bias in the 2025 values.** Co-emissions of the non-power fuel use that rebounds are not modelled. Extra industrial
  coal in the actual world also emits SO2, so its omission biases the 2025 values toward cooling (small in the
  central case, where coal f is 3.6%).

**Not modelled.**
- Power-sector fuel switching in response to counterfactual fuel prices. Fell & Kaffine (2018) find strong gas-price ×
  wind interactions in US coal dispatch. Higher counterfactual gas prices would shift the US/EU fill toward coal, so
  avoided CO2 would likely be higher.
- Counterfactual substitution of nuclear, hydro or biomass toward non-fossil targets (avoided CO2 lower).
- Gas-market integration through LNG after about 2016. Pooling markets with similar η changes f little.
- Learning spillovers. These do not affect 2006–2025 in a frozen-deployment counterfactual.

**Verification status.**
- Burke & Liao, Kaffine et al. and Fell & Kaffine (abstract) were checked against primary text.
- Perino 2018 numbers: UNVERIFIED. Bruninx & Ovaere 2022: quoted from the PMC full text.
- NDRC corridor: secondary reports only.
- China coal balance: customs imports 542.7 Mt and NBS output 4.76 Gt in 2024 (news reports of official releases,
  physical tonnes). The 4,666 / 4,952 Mt pair in an earlier draft could not be traced and should not be cited.

## Comparing to Ember's 4,065 Mt

Our 2025 F1 3.73 Gt differs from Ember's GER 2026 figure on three axes: base
year (2005 vs 2000), CO2 combustion vs lifecycle CO2e, and country fossil mix
vs World average. V1 reproduces Ember on Ember's terms. Never put the two
numbers side by side without saying so.

## Caveats

- Coal-to-gas switching and RE growth were jointly determined (Fell &
  Kaffine 2018); F1 treats observed switching as exogenous.
- Demand held at observed levels in the headline. The demand response, fuel-market rebound, cycling and EU ETS
  waterbed are quantified in "Rebound adjustments" above. Nuclear retirements are held at observed levels.
- fair-calibrate v1.4.5 history is very likely CEDS v_2024_07_08 (inferred
  from repo folders, not stated); our factors use v_2025_03_18. Our Δ is a
  perturbation on top of that history, so the version mismatch affects only
  the baseline state, not the Δ.
- China gross vs net generation basis (MEE factor vs Ember China TWh) not
  yet confirmed: ±5% on China CO2 (39% of the total).
- 1,521 country-fuel-years with fill but no factor (fuel absent in Ember)
  use the World-average factor (small: ~100 TWh per rule over 20 years).
