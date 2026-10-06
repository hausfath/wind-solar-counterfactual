---
title: "How much do rebound effects reduce the emissions avoided by wind and solar?"
subtitle: "Allowing for less efficient backup plants, cheaper electricity and lower fossil fuel prices, wind and solar still avoided around {{cen_r}} billion tonnes of CO2 between 2006 and 2025"
author: "Zeke Hausfather · The Climate Brink · October 2026"
---

In a recent post I estimated that the wind and solar built since 2005 avoided around {{head_r}} billion tonnes of CO2 from the global power sector through 2025. That analysis held electricity demand at its real-world level. It also assumed that every MWh of wind and solar replaced a MWh of fossil generation at the average emission rate of that country's coal, gas and oil plants.

Roger Pielke Jr. argued that this overstates the benefit. He pointed to two things. First, published estimates of how much fossil generation each unit of non-fossil generation displaces range from {{dr_lo}} to {{dr_hi}}. Second, he applied a fossil fuel price rebound of {{crit_f}}% (with a range of {{crit_f_lo}}% to {{crit_f_hi}}%), and combined the two into a range of {{crit_lo}} to {{crit_hi}} billion tonnes. He is right that the original analysis left out rebound effects, and the main one he identifies (lower fossil fuel prices leading other buyers to burn more) is a well-established mechanism. So I went through the literature on each type of rebound and built them into the model.

Taken together, three rebound effects reduce the CO2 avoided by wind and solar by around {{cut_pct}}%, from {{head}} to {{cen}} billion tonnes over 2006-2025. Under every scenario I tested, the total stays between {{hi}} and {{lo}} billion tonnes.[^range] Avoided warming by 2050 falls from {{t_head}}C to {{t_cen}}C.

### Three ways the original estimate could be too high

The first effect is cycling. When wind and solar output rises and falls, coal and gas plants ramp up and down and spend more time running at part load, where they burn more fuel per MWh. [Kaffine et al (2020)](https://doi.org/10.5547/01956574.41.5.dkaf) studied the Southwest Power Pool in 2012-14, when wind supplied around 10% of its electricity. They found intermittency reduced the CO2 savings from wind by {{kaff}}%.[^kaffine] A [recent preprint](https://arxiv.org/abs/2408.05209) by Suri et al. finds that wind and solar deliver 91% to 95% of their expected emissions savings in California and Texas, where their shares are higher. I scale the penalty with each country's wind and solar share, anchored to the Kaffine et al. estimate, which gives an average penalty of {{c_cen}}% ({{c_lo}}% to {{c_hi}}%).

The second is an electricity demand rebound. If wind and solar make electricity cheaper, people and businesses use more of it, so some of the demand I held fixed would not exist without them. The sign of this effect is less obvious than it sounds. Wind and solar reliably push down wholesale prices ([Mills et al 2020](https://doi.org/10.1016/j.apenergy.2020.116266)), but the cost of supporting them has often pushed retail prices up. [Greenstone and Nath (2019)](https://epic.uchicago.edu/research/do-renewable-portfolio-standards-deliver) find retail prices were 11% higher seven years after US states adopted renewable portfolio standards, and 17% higher after twelve. Retail prices in China, which built {{cn_gap}}% of the world's wind and solar added since 2005, are set by regulators. I assume wind and solar lowered retail prices by around 1% at 2025 levels of deployment (with a range from a 1% increase to a 3% decrease), with a long-run demand elasticity of -0.3 (-0.5 in the high case). That gives a rebound of {{r_cen}}% ({{r_lo}}% to {{r_hi}}%).

Some of that extra demand could be electric vehicles and heat pumps, which replace oil and gas burned directly rather than adding new energy use. Each MWh used by an electric car displaces roughly 0.8 tonnes of CO2 from petrol, and each MWh used by a heat pump displaces around 0.67 tonnes from a gas boiler.[^elec] The fossil power that would have met that demand emits around {{ef_fill}} tonnes per MWh, so electrification largely cancels out its own rebound. I don't include it in the central estimate, as I couldn't find any estimate of what share of price-driven demand is electrification. But if it were 40%, it would add back {{phi_cen}} billion tonnes ({{phi_hi}} billion tonnes in the high rebound case). Most electrification today is driven by policy and falling battery and heat pump costs rather than electricity prices, so this is likely a small effect either way.

The third, and by far the most uncertain, is a fossil fuel market rebound. In a world without wind and solar, power plants would have burned more coal and gas, pushing up fuel prices. Other buyers of those fuels (steel mills, cement kilns, chemical plants and home heating) would then have burned less. In the real world, they burn correspondingly more. This is the same fuel-price channel that drives carbon leakage in climate policy analysis, and Roger's {{crit_f}}% comes from the standard formula for it, applied to one global market per fuel where the whole market responds to price.

### Fuel markets are regional

Three features of real fuel markets shrink this rebound a lot.

Coal and gas markets are mostly regional. China burns more than half of the world's coal and mines most of it at home ({{cn_import}}% of its 2024 supply was imported, by [official figures](https://www.mysteel.net/news/5074522-nbs-chinas-2024-coal-output-hits-record-high)). Gas trades in regional markets connected only partly by LNG shipping. So I model coal markets for China, India, the US and the rest of the world, and gas markets for North America, Europe, Asian LNG importers, China, the administered-price producers (Russia, the Middle East and Central Asia) and the rest of the world. Oil is one global market.

Supply responds to demand. China's coal output is state-managed, with a government price corridor for long-term contracts ([China Daily](https://global.chinadaily.com.cn/a/202202/25/WS621816a3a310cdd39bc88c80.html)). Extra demand there mostly shows up as extra output rather than higher prices. I treat Chinese and Indian coal supply as very price-responsive. For gas I use the long-run US supply elasticity of 0.81 from [Hausman and Kellogg (2015)](https://www.nber.org/papers/w21115).

Only buyers outside the power sector can rebound, since the counterfactual fixes electricity demand. Using sector-level emissions data from [CEDS](https://zenodo.org/records/15059443), I split each market into power plants (which don't respond), industry and buildings (which do), and steel mills and district heating plants (which barely do). Much of China's non-power coal use is also governed by output and capacity controls, so I assume a low elasticity of -0.3 there (-0.2 to -0.5).[^solve]

With those features, the rebound is small for coal ({{f_coal}}%), larger for gas ({{f_gas}}%) and large for oil ({{f_oil}}%), though very little oil is burned for power. Averaged across fuels, it is {{f_all}}%.

The most important judgment call is the coal demand elasticity. The estimate most often cited for China, -0.3 to -0.7 from [Burke and Liao (2015)](https://doi.org/10.1016/j.chieco.2015.10.004), is for total provincial coal use, including power plants. If it is applied to the whole coal market, the coal rebound rises to {{f_coal_agg}}% and avoided emissions fall to {{alt}} billion tonnes, close to Roger's estimate. I don't use it as my central case for two reasons. It is estimated across provinces, so it partly captures coal use shifting from one province to another, which doesn't change China's total. And outside China, applying it to the whole market treats power plants switching from coal to gas as a full rebound, when gas emits about half as much CO2. It is included in the high case, though.

### Putting it all together

The figure below shows how each adjustment changes the CO2 avoided by wind and solar over 2006-2025. The error bars show the range for each adjustment between its low and high case, with the other adjustments at their central values.

![](FIG/fig7_rebound_waterfall.png)

The cycling penalty removes {{s_c}} billion tonnes, the electricity demand rebound {{s_r}} billion and the fuel market rebound {{s_f}} billion, leaving {{cen}} billion tonnes. In 2025 alone, wind and solar avoided {{y25_cen}} billion tonnes rather than {{y25_head}} billion. Without them, global power sector emissions would have been {{pct25_cen}}% higher than they actually were, compared with {{pct25_head}}% in the original estimate.

To see which assumptions matter most, the figure below varies them one at a time while holding the others at their central values.

![](FIG/fig9_rebound_tornado.png)

Reading the Chinese coal elasticity as applying to the whole market has the largest effect, at {{oat_agg}} billion tonnes. The electricity demand rebound is next ({{oat_r_hi}} to {{oat_r_lo}} billion tonnes), because its sign is uncertain. Once the market is split into buyer groups, the coal supply and demand elasticities barely matter. In China and India, the coal rebound is small under any reasonable choice.

### What about displacement ratios?

The ratios Roger cites come mostly from cross-country studies such as [York (2012)](https://doi.org/10.1038/nclimate1451), [Hu and Cheng (2017)](https://doi.org/10.1038/ncomms14590) and [Rather and Mahalik (2023)](https://doi.org/10.1007/s10098-023-02689-8). They find that fossil fuel use does not fall one-for-one as non-fossil generation grows, and Hu and Cheng describe the shortfall as a rebound of 10% to 50%. These studies compare countries and decades in which demand was free to grow, and in which most non-fossil generation was hydro and nuclear. Fast-growing economies build more of everything, so fossil and non-fossil generation rise together even when each clean MWh displaces a fossil one.

My counterfactual holds demand at its observed level and models the demand response separately, so applying one of these ratios on top would count the same effect twice. The two estimates in Roger's set that are specific to wind and solar are also his highest. [Liddle (2024)](https://doi.org/10.3390/su16135319) finds that wind and solar have a "unitary displacement effect". [Wiskich (2023)](https://ideas.repec.org/p/een/camaaa/2023-27.html) finds substitution between wind and solar and fossil generation that is close to perfect.[^wiskich]

### What about Europe's carbon market?

A fourth possible effect is the EU's emissions trading system. Under a fixed cap, cutting emissions in the power sector frees up permits that can be used elsewhere, the so-called waterbed effect. However, applying it here is circular. The EU set its caps knowing renewables would grow, so in a world without wind and solar the cap would have been looser, or carbon prices would have had to rise to levels that would have been politically very difficult. The market also built up a large surplus of permits in 2008-17, much of which was later cancelled. I leave it out of the central estimate. The high case assumes that 20% of avoided EU emissions in 2008-17, and 60% in 2018-25, were re-emitted elsewhere under the cap.[^ets] On its own, that would reduce the total by {{wb}} billion tonnes.

### How this compares to the critique

The figure below compares these estimates with Roger's.

![](FIG/fig8_rebound_comparison.png)

Applying his formula and elasticities to our counterfactual gives {{crit}} billion tonnes, close to his roughly {{crit_c}} billion. So the difference between us comes from how fuel markets are represented. The low end of his range ({{crit_lo}} billion tonnes) comes from the displacement ratios, which don't apply to a counterfactual that already holds demand fixed.

### What it means for temperatures

The adjustments reduce avoided warming by 2050 from {{t_head}}C ({{t_head_lo}}C to {{t_head_hi}}C) to {{t_cen}}C ({{t_cen_lo}}C to {{t_cen_hi}}C).[^fair] As in the original analysis, the effect in 2025 itself is close to zero ({{t25_cen}}C), because the extra sulphur pollution from coal in the counterfactual world masks most of the avoided CO2 warming for now. That masking fades within a few years once the pollution stops, while the CO2 stays in the atmosphere.

There are also things this analysis doesn't capture. Higher gas prices in a world without wind and solar would have pushed some power plants from gas back to coal. [Fell and Kaffine (2018)](https://doi.org/10.1257/pol.20150321) find strong interactions between gas prices and wind output in US coal generation, and this would make avoided emissions larger. In the other direction, countries with clean energy targets might have built more nuclear, hydro or biomass without wind and solar, which would make them smaller. I haven't modelled the sulphur and other pollutants from the extra fuel burned by other buyers either.

### So what are the takeaways here?

Rebound effects are real, and the original analysis left them out. In my central estimate they cut the emissions avoided by wind and solar by around a sixth, and by more than half if every assumption is set to its most pessimistic value at once. But the size of the fuel market rebound depends on how integrated markets are and how readily supply responds. Neither favours a large rebound for Chinese coal, which is where most of the avoided emissions are.

The rebound question will matter more, not less, as wind and solar start pushing fossil generation down rather than just covering demand growth. If that drives coal and gas prices down, keeping the cheaper fuel from being burned elsewhere will depend on climate policy in industry, buildings and transport.
In case its helpful, I've put the code and data to reproduce this analysis on my GitHub [here](https://github.com/hausfath/wind-solar-counterfactual).

[^range]: These are scenarios rather than a probability range. The low end combines the high case for every adjustment, including the whole-market reading of the coal elasticity and Europe's carbon market (both discussed below). The high end combines the low case for every adjustment.

[^kaffine]: This is their estimate including the dynamic effects of ramping. Their static estimate is {{kaff_static}}%.

[^elec]: An electric car using around 0.2 kWh per km, against roughly 0.16 kg of CO2 per km for a petrol car. A heat pump with a coefficient of performance of 3, against a 90% efficient gas boiler.

[^solve]: For each market and year I solve for the fuel price at which supply equals power demand plus other buyers' demand, using constant elasticities. The shifts are not small. China's extra coal burn in the counterfactual equals around {{cn_dq}}% of its actual 2025 coal use, so I solve the market exactly rather than using the usual small-change formula. With one global market where every buyer responds, the same calculation reproduces Roger's {{crit_f}}%.

[^wiskich]: Wiskich's 0.57 is a share parameter in a production function, not a displacement ratio. The paper finds substitutability between wind and solar and fossil generation that is close to "perfect", while noting its method probably overstates it.

[^ets]: The 2018-25 value is at the top of the range implied by [Bruninx and Ovaere (2022)](https://doi.org/10.1038/s41467-022-28398-2). They find that each tonne cut in 2020 leads the market reforms to cancel around 0.42 to 0.79 permits, depending on how long it takes the permit surplus to clear.

[^fair]: From the FaIR climate model, using an ensemble of 841 parameter sets constrained to observed warming (median, with 5th to 95th percentile ranges). These are differences between the counterfactual and the real world, so no baseline period applies.
