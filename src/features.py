"""Per-tract feature extraction from the PERMITTED challenge layers only.

Inputs (Source Cooperative, release pinned by the organisers to Overture 2026-08-19.0):
  reference/<region>/<region>-overture-{buildings,roads,pois,infrastructure}.parquet
  reference/<region>/<region>-census-acs-housing.parquet   (tract polygons + ACS B25001)
  reference/<region>/<region>-sample-submission.csv        (scored tract list)

Removed reference layers (TIGER roads, Microsoft footprints, HIFLD, CBP) are never read.

Usage:  python src/features.py <region> [<region> ...]
Output: data/features/<region>.parquet
"""
import sys
import time
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

BUCKET = "s3://us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge"
OUT = Path(__file__).resolve().parents[1] / "data" / "features"
NAMED = ("motorway", "trunk", "primary", "secondary")
FIRE = ("fire_department",)
EMS = ("ambulance_and_ems_services",)
SCHOOLS = ("elementary_school", "middle_school", "high_school", "school",
           "private_school", "public_school")
EQUAL_AREA = "EPSG:5070"


def con():
    c = duckdb.connect()
    c.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    return c


def layer(region, name):
    return f"{BUCKET}/reference/{region}/{region}-{name}.parquet"


def tracts(c, region):
    df = c.execute(f"SELECT GEOID, housing_units, geometry FROM read_parquet('{layer(region, 'census-acs-housing')}')").df()
    g = gpd.GeoDataFrame(df.drop(columns="geometry"),
                         geometry=shapely.from_wkb(df["geometry"].map(bytes)), crs="OGC:CRS84")
    sample = c.execute(f"SELECT * FROM read_csv('{BUCKET}/reference/{region}/{region}-sample-submission.csv', "
                       "types={'GEOID': 'VARCHAR'})").df()
    g = g[g.GEOID.isin(sample.GEOID)].reset_index(drop=True)
    g["land_km2"] = g.to_crs(EQUAL_AREA).area / 1e6
    return g, sample


def assign_points(g, x, y):
    """Index of the tract containing each point (-1 if none)."""
    pts = shapely.points(x, y)
    tree = shapely.STRtree(g.geometry.values)
    pi, ti = tree.query(pts, predicate="within")
    out = np.full(len(pts), -1, dtype=np.int64)
    out[pi] = ti
    return out


def count_by(idx, n, mask=None):
    keep = idx >= 0 if mask is None else (idx >= 0) & mask
    return np.bincount(idx[keep], minlength=n)


def buildings(c, g, region):
    q = f"""SELECT (bbox.xmin+bbox.xmax)/2 x, (bbox.ymin+bbox.ymax)/2 y,
                   sources[1].dataset src, height IS NOT NULL has_h
            FROM read_parquet('{layer(region, 'overture-buildings')}')"""
    d = c.execute(q).df()
    idx = assign_points(g, d.x.values, d.y.values)
    n = len(g)
    src = d.src.fillna("unknown").str.lower()
    f = {"ov_bld": count_by(idx, n),
         "ov_bld_osm": count_by(idx, n, src.str.contains("openstreetmap").values),
         "ov_bld_msft": count_by(idx, n, src.str.contains("microsoft").values),
         "ov_bld_esri": count_by(idx, n, src.str.contains("esri").values),
         "ov_bld_google": count_by(idx, n, src.str.contains("google").values),
         "ov_bld_height": count_by(idx, n, d.has_h.values)}
    return pd.DataFrame(f)


def roads(c, g, region):
    q = f"""SELECT class, geometry FROM read_parquet('{layer(region, 'overture-roads')}')
            WHERE class IN {NAMED + ('tertiary', 'residential', 'unclassified')}"""
    d = c.execute(q).df()
    lines = gpd.GeoDataFrame({"cls": d["class"]}, geometry=shapely.from_wkb(d["geometry"].map(bytes)),
                             crs="OGC:CRS84").to_crs(EQUAL_AREA)
    tp = g[["geometry"]].to_crs(EQUAL_AREA).reset_index(names="t")
    inter = gpd.overlay(lines, tp, how="intersection", keep_geom_type=True)
    inter["km"] = inter.length / 1000
    piv = inter.pivot_table(index="t", columns="cls", values="km", aggfunc="sum").reindex(range(len(g))).fillna(0)
    out = pd.DataFrame(index=range(len(g)))
    out["ov_named_km"] = piv[[k for k in NAMED if k in piv]].sum(axis=1)
    for k in NAMED + ("tertiary", "residential", "unclassified"):
        out[f"ov_{k}_km"] = piv[k] if k in piv else 0.0
    return out


def pois(c, g, region):
    q = f"""SELECT (bbox.xmin+bbox.xmax)/2 x, (bbox.ymin+bbox.ymax)/2 y,
                   categories.primary cat, confidence
            FROM read_parquet('{layer(region, 'overture-pois')}')"""
    d = c.execute(q).df()
    idx = assign_points(g, d.x.values, d.y.values)
    n = len(g)
    cat = d.cat.fillna("")
    return pd.DataFrame({
        "ov_places": count_by(idx, n),
        "ov_places_hiconf": count_by(idx, n, (d.confidence.fillna(0) >= 0.7).values),
        "ov_fire": count_by(idx, n, cat.isin(FIRE).values),
        "ov_ems": count_by(idx, n, cat.isin(EMS).values),
        "ov_schools": count_by(idx, n, cat.isin(SCHOOLS).values),
        "ov_hospital": count_by(idx, n, (cat == "hospital").values),
    })


def infrastructure(c, g, region):
    q = f"""SELECT (bbox.xmin+bbox.xmax)/2 x, (bbox.ymin+bbox.ymax)/2 y
            FROM read_parquet('{layer(region, 'overture-infrastructure')}')"""
    d = c.execute(q).df()
    return pd.DataFrame({"ov_infra": count_by(assign_points(g, d.x.values, d.y.values), len(g))})


def run(region):
    t0 = time.time()
    c = con()
    g, sample = tracts(c, region)
    parts = [g[["GEOID", "housing_units", "land_km2"]].reset_index(drop=True)]
    for fn in (buildings, roads, pois, infrastructure):
        t = time.time()
        parts.append(fn(c, g, region))
        print(f"  {region} {fn.__name__}: {time.time() - t:.0f}s", flush=True)
    feat = pd.concat(parts, axis=1)
    feat.insert(1, "region", region)
    assert len(feat) == len(sample) and feat.GEOID.is_unique
    OUT.mkdir(parents=True, exist_ok=True)
    feat.to_parquet(OUT / f"{region}.parquet", index=False)
    print(f"{region}: {len(feat)} tracts in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    for r in sys.argv[1:]:
        run(r)
