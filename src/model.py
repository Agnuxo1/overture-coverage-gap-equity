"""Coverage-gap estimator built only from permitted challenge data.

The organiser score is the mean of the *defined* components among
  transport  = 1 - min(1, overture_named_km / tiger_named_km)
  building   = 1 - min(1, overture_buildings / microsoft_buildings)
  poi        = mean(facilities half, establishments half)
The reference denominators were removed from the package, so each one is replaced by
an expectation built from Overture-internal structure, ACS housing units and the strata
spine (population, land area, urban/rural). A small set of global parameters (PARAMS)
controls those expectations; they are documented priors, tuned only by whole-submission
public-leaderboard scores (see experiments/LOG.md).

Usage: python src/model.py [params.json] [out.csv]
"""
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BUCKET = "s3://us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge"
REGIONS = ("eastern-ok", "maricopa-az", "northern-ca", "south-central-tx")
STRATA_COLS = ["GEOID", "pop_total", "ALAND", "pct_urban", "ur_class", "ruca_primary",
               "svi_overall", "cvi_overall", "tribal_any"]

PARAMS = {
    # transport: share of TIGER primary/secondary that Overture files as tertiary
    "road_named_min_km": 0.05,   # below this Overture named length the road term is treated as undefined
    "road_tertiary_leak": 0.15,  # expected TIGER-named km hidden in Overture tertiary, per tertiary km
    "road_floor": 0.0,
    # buildings: Overture conflates Microsoft ML footprints, so the expected deficit is small
    "bld_base": 0.02,
    "bld_osm_only_penalty": 0.05,  # tracts whose footprints come almost only from OSM (MS rows deduplicated away)
    # establishments: expected CBP establishments per housing unit, and per resident
    "estab_per_hu": 0.08,
    "estab_urban_boost": 0.5,
    # facilities
    "fire_prob_km2": 60.0,       # land area at which a tract is expected to hold one reference fire station
    "fire_prob_pop": 9000.0,     # population at which a tract is expected to hold one reference fire station
    "school_per_pop": 1 / 2500,  # reference schools per resident
    # final blend
    "shrink": 0.0,               # shrinkage of each tract toward its region mean
    "scale": 1.0,
}


def load_features():
    feats = pd.concat([pd.read_parquet(ROOT / "data" / "features" / f"{r}.parquet") for r in REGIONS],
                      ignore_index=True)
    strata = []
    c = duckdb.connect()
    c.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    for r in REGIONS:
        cache = ROOT / "data" / "strata" / f"{r}.parquet"
        if not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cols = ", ".join(STRATA_COLS)
            c.execute(f"SELECT {cols} FROM read_parquet('{BUCKET}/strata/{r}/{r}-strata-tract-table.parquet')"
                      ).df().to_parquet(cache, index=False)
        strata.append(pd.read_parquet(cache))
    return feats.merge(pd.concat(strata, ignore_index=True), on="GEOID", how="left")


def ratio_gap(num, den):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.clip(1 - np.where(den > 0, num / den, 1.0), 0, 1)


def predict(f, p):
    out = pd.DataFrame({"GEOID": f.GEOID, "region": f.region})
    pop = f.pop_total.fillna(0).clip(lower=0)
    hu = f.housing_units.fillna(0).clip(lower=0)
    urban = f.pct_urban.fillna(0).clip(0, 1)

    # transport
    t_def = f.ov_named_km > p["road_named_min_km"]
    expected_named = f.ov_named_km + p["road_tertiary_leak"] * f.ov_tertiary_km
    t_gap = np.maximum(ratio_gap(f.ov_named_km, expected_named), p["road_floor"])

    # buildings
    b_def = f.ov_bld > 0
    osm_only = (f.ov_bld_osm / f.ov_bld.clip(lower=1)) > 0.95
    b_gap = p["bld_base"] + p["bld_osm_only_penalty"] * osm_only

    # POI, establishments half
    estab_exp = p["estab_per_hu"] * hu * (1 + p["estab_urban_boost"] * urban)
    cbp_gap = ratio_gap(f.ov_places, estab_exp)
    cbp_def = estab_exp > 0
    # POI, facilities half: expected gap given the reference likely holds the facility
    lam_fire = f.land_km2 / p["fire_prob_km2"] + pop / p["fire_prob_pop"]
    w_fire = 1 - np.exp(-lam_fire)                      # P(reference fire station in tract)
    fire_gap = ratio_gap(f.ov_fire, np.maximum(lam_fire, 1.0))
    school_exp = p["school_per_pop"] * pop
    w_sch = 1 - np.exp(-school_exp)
    sch_gap = ratio_gap(f.ov_schools, np.maximum(school_exp, 1.0))
    w_fac = w_fire + w_sch
    fac_gap = np.where(w_fac > 0, (w_fire * fire_gap + w_sch * sch_gap) / w_fac.where(w_fac > 0, 1), 0)
    fac_def = w_fac > 0.05
    p_gap = np.where(fac_def & cbp_def, (fac_gap + cbp_gap) / 2, np.where(fac_def, fac_gap, cbp_gap))
    p_def = fac_def | cbp_def

    comps = np.vstack([np.where(t_def, t_gap, np.nan), np.where(b_def, b_gap, np.nan),
                       np.where(p_def, p_gap, np.nan)]).T
    score = np.nanmean(np.where(np.isnan(comps).all(axis=1, keepdims=True), 0, comps), axis=1)
    out["transport_gap"] = np.where(t_def, t_gap, 0.0)
    out["building_gap"] = np.where(b_def, b_gap, 0.0)
    out["poi_gap"] = np.where(p_def, p_gap, 0.0)
    region_mean = pd.Series(score).groupby(out.region.values).transform("mean").values
    score = (1 - p["shrink"]) * score + p["shrink"] * region_mean
    out["coverage_gap_score"] = np.clip(p["scale"] * score, 0, 1)
    return out


def write_submission(pred, path):
    cols = ["GEOID", "transport_gap", "building_gap", "poi_gap", "coverage_gap_score"]
    sub = pred[cols].copy()
    assert sub.GEOID.is_unique and len(sub) == 9379 and sub.notna().all().all()
    assert sub.GEOID.str.len().eq(11).all()
    path.parent.mkdir(parents=True, exist_ok=True)
    sub.to_csv(path, index=False, float_format="%.6f")
    return sub


if __name__ == "__main__":
    params = dict(PARAMS)
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        params.update(json.loads(Path(sys.argv[1]).read_text()))
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "submissions" / "sub.csv"
    pred = predict(load_features(), params)
    sub = write_submission(pred, out)
    print(out, len(sub))
    print(pred.groupby("region")[["transport_gap", "building_gap", "poi_gap", "coverage_gap_score"]].mean().round(3))
