# Zindi Bias Bounty Mapping Equity Challenge — Special Prize Methodology

**Entrant:** Francisco Angulo de Lafuente · **Zindi username:** Francisco_Angulo_Lafuente  
**Team/project:** Overture Coverage-Gap Equity · **Competition:** [Bias Bounty Mapping Equity Challenge](https://zindi.world/competitions/bias-bounty-mapping-equity-challenge)  
**Categories sought:** **Best Bias Discovery** and **Best Documentation**  
**Reproducible code and figures:** https://github.com/Agnuxo1/overture-coverage-gap-equity  
**Independent correction and audit:** [PR #1](https://github.com/Agnuxo1/overture-coverage-gap-equity/pull/1) (merged, 31 October 2026)

## 1. Executive finding: the map's source composition matters

The challenge's automated equity scorecard measures representation and coverage gaps, but it does not explicitly distinguish **building footprints whose primary upstream source is volunteer-mapped OpenStreetMap** from footprints primarily attributed to **Microsoft machine-learning extraction**. In Overture, a high building count does not necessarily mean that the same number of records include usable names, addresses or building uses.

Across the *provided* Eastern Oklahoma study region, the share of building records attributed to Microsoft ML is **81.998% in 805 tribal-associated tracts**, compared with **35.214% in 387 non-tribal tracts**: an observational disparity of **46.78 percentage points**, or **2.33 times** the non-tribal share. The corresponding OSM-first shares are **14.289%** and **23.125%**. Shares are **weighted by building count**, not simple averages of tract percentages.

The underlying region-stratum totals are:

| Eastern Oklahoma stratum | Tracts | Overture buildings | Microsoft ML-first | OSM-first | Microsoft ML share |
|---|---:|---:|---:|---:|---:|
| Tribal-associated | 805 | 1,862,424 | 1,527,142 | 266,127 | 81.998% |
| Non-tribal | 387 | 689,270 | 242,722 | 159,396 | 35.214% |

This is **not** a causal claim about tribal status or an assertion that ML-sourced buildings are incorrectly mapped. It is a measurable difference in source provenance which a purely count-based coverage indicator can conceal. The `tribal` group is based on the competition's own tribal-overlap field; a tract may contain non-tribal land and mixed communities.

## 2. New intersectional discovery: the high-ML/no-mapped-fire-POI group

Our final, independently corrected discovery applies four pre-specified tract filters to the supplied Overture/ACS/strata data:

1. Census tract population **greater than 1,000**;
2. Land area **greater than 50 km²**;
3. **No Overture fire-station place record** in the extracted challenge inventory;
4. **At least 95%** of its Overture building records attributed to Microsoft ML, as calculated directly from `ov_bld_msft / ov_bld` (requiring `ov_bld > 0`).

**Result: 244 tracts encompassing 823,716 residents**, across the four described competition regions.

| Region and stratum | Flagged tracts | Population represented |
|---|---:|---:|
| Eastern Oklahoma, tribal-associated | **67** | **203,784** |
| Eastern Oklahoma, non-tribal | 1 | 2,059 |
| Maricopa, non-tribal | 2 | 6,988 |
| Northern California, tribal-associated | 1 | 2,554 |
| Northern California, non-tribal | 12 | 42,066 |
| South-Central Texas, non-tribal | 161 | 566,265 |
| **Total** | **244** | **823,716** |

**Important interpretation:** “No fire-station place recorded in the extracted Overture inventory” is not “no real fire station exists.” It identifies a visibility gap in one mapping dataset, not the state of the physical emergency infrastructure. Similarly, a Microsoft ML first-source marker is not sufficient to establish missing address metadata; that must be tested record by record with an attribute-completeness audit.

The pattern is operationally relevant because emergency planning depends on locating specific buildings and facilities, not just counting footprints. These tracts should therefore be prioritised for an **independent addressability/facility-data validation**, rather than presumed underserved without ground truth.

## 3. Why the finding is outside the automated bias scorecard

The automatic metrics compare coverage, places and road access across pre-defined demographic/vulnerability strata. Our discovery conditions on the **upstream provenance of individual Overture building records**, jointly with tract area, population, and lack of mapped fire-station POIs. A community can have many polygon geometries but little information about the provenance or addressability of those records.

The measurable research question is: *How does the provenance mix differ between contexts that conventional count-based map coverage would treat as equivalent?* The finding remains useful even when no leaderboard RMSE is known.

## 4. Technical method and allowed sources

- **Geographic units:** 11-character Census GEOIDs preserved as text. The submitted regional feature files cover the four published focus regions (9,379 tract rows).
- **Permitted datasets:** the competition's Overture Maps extract (`2026-08-19.0`), provided Census ACS B25001 housing-unit data, tract geometry/area, population and supplied vulnerability/tribal strata. Only the package's permitted sources are used.
- **Source provenance:** `sources[0].dataset` for the first-listed upstream dataset, counted as OSM/Microsoft ML/Esri; the first source is not necessarily the only origin.
- **Stratification:** `tribal_any`, `ur_class`, and the competition's supplied population and geographic attributes.
- **Aggregation:** group by region and the supplied stratum; sum building-record counts first, then calculate upstream shares. This avoids unequal-weight tract-average artefacts.
- **Spatial and edge cases:** tract joins use textual GEOIDs; projected area/distance handling uses EPSG:5070; zero-building tracts cannot satisfy a “95% ML” criterion. Missing mapped POIs are not automatically imputed as absent physical facilities.

**Prohibited scored-input sources were not used:** TIGER roads, external Microsoft footprints, HIFLD, CBP, or copies of withdrawn evaluation denominators. No organizer evaluation labels were reconstructed, inferred or released.

## 5. Reproduction and independent correction

Run from the public repository after obtaining the challenge's permitted package:

```bash
python -m pip install -r requirements.txt
python src/features.py eastern-ok maricopa-az northern-ca south-central-tx
python src/discovery.py
python -m unittest discover -s tests -p "test_discovery_flags.py"
```

The outputs include:

- `results/discovery_provenance_by_tribal.csv`: 805/387 tract comparison and primary-source shares;
- `results/discovery_provenance_by_urban_rural.csv` and `results/discovery_provenance_by_svi_q.csv`: alternative stratifications;
- `results/discovery_flagged_tracts.csv`: **244** flagged GEOIDs, their populations, primary-source shares, area and mapped facility counts;
- `assets/building_provenance.gif` and `assets/tribal_strata_bars.gif`: explanatory figures.

An independent review on **31 October 2026** reproduced the strict 244-tract / 823,716-person total, including the Eastern Oklahoma 67-tract / 203,784-person subset, from the cached regional feature and strata files. The code includes a regression test designed to catch a crucial previous error: *a low OSM fraction is not equivalent to a high Microsoft ML fraction if another upstream source (e.g. Esri) dominates.*

The earlier exploratory proxy `OSM share < 5%` identified **276 tracts / 955,406 residents**, but **32** of those did **not** satisfy the stated `Microsoft ML share >= 95%` requirement. The stricter result supersedes that earlier claim. We retain this correction explicitly for reproducibility.

## 6. Coverage-gap score model (documentation track)

The prediction model is separate from this descriptive provenance discovery. It follows the organizer's three-part score grammar:

- **Transport gap:** named highway kilometres in Overture compared with a permitted-data-based expectation derived from Overture road class mix.
- **Building gap:** expected missing coverage estimated entirely from Overture's own source composition; withdrawn Microsoft denominators are **not** reused.
- **Places/facilities gap:** expected establishment count from supplied housing/urbanisation and expected facilities from population/area, compared with Overture places.
- **Composite:** mean of defined components only; undefined components are omitted from the mean and output with a filled zero in the optional component columns. All predictions are clipped to [0,1] with no missing values.

The model uses documented global parameters; it has **no access to a legitimate labelled local hold-out** because reconstructing the organiser's historical reference layers would use withdrawn data. The official platform's processed RMSE, if and when available, is the only externally comparable score. Negative outcomes are retained in the experiment log rather than presented as improvements.

A platform validation complication is documented in the README: a previous 9,379-row submission was rejected by the processor for missing 415 GEOIDs associated with Eastern Washington, even though the public challenge description lists four scored regions. A corrected 9,794-row candidate has been generated without altering any original 9,379 predictions; **its Zindi processing result must be checked before treating it as an eligible leaderboard entry**. This discrepancy does not enter the four-region special-prize analysis above.

## 7. Explicit limits and responsible interpretation

This is an observational map-data quality finding. The supplied source inventory does not directly measure real-world fire-station availability, dispatch time, error in machine-generated footprints, actual geocoding success, or the completeness of address attributes for each provenance group. The group comparison is not an intervention or causal estimate. The flags define candidates for targeted validation, not proven harms.

## 8. Source attribution, licensing and availability

- Competition: Zindi × Humane Intelligence × Radiant Earth Bias Bounty Mapping Equity Challenge.
- Challenge data: [Source Cooperative official package](https://source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge), subject to its published licence and attribution.
- Overture Maps source provenance under its applicable open-data terms.
- Methods and reproducible code: [Agnuxo1/overture-coverage-gap-equity](https://github.com/Agnuxo1/overture-coverage-gap-equity), MIT-licensed code.
- Independent technical correction: [PR #1](https://github.com/Agnuxo1/overture-coverage-gap-equity/pull/1), merged into `main`.

**Submission note:** This writeup is the final technical narrative for the two special-prize categories. It should be associated with a **successfully processed** Zindi submission in the organizer's form when available; the existence of a file on disk does not establish acceptance.
