# FaIR calibration inputs

Used by `scripts/07_fair.py`.

| File | What |
|---|---|
| `calibrated_constrained_parameters_1.4.5.csv` | fair-calibrate v1.4.5 observationally constrained parameter ensemble (841 members) |
| `species_configs_properties_1.4.5.csv` | species configuration for that calibration |
| `historical_1750-2025.csv` | historical emissions 1750–2025 (2024–2025 values are the file's own extension) |
| `extensions_1750-2500.csv` | scenario extensions; `medium-extension` is used after 2025, offset-harmonised to the 2025 historical values |
| `volcanic_solar.csv` | prescribed volcanic and solar forcing |

These files are redistributed as packaged in Chris Smith's `temperature-attribution` workflow, which uses
fair-calibrate (https://github.com/chrisroadmap/fair-calibrate, MIT). The MIT license of that workflow is included
as `LICENSE_temperature-attribution_MIT.txt`. Please cite the fair-calibrate papers (Smith et al.) when using them.
FaIR itself is Apache-2.0 (https://github.com/OMS-NetZero/FAIR).
