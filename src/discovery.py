"""Bias discovery: provenance of Overture buildings and facility visibility across strata.

Everything here uses only Overture attributes, ACS housing and the provided strata tables, so a
judge can reproduce it from the challenge package.  Outputs: results/discovery_*.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from model import ROOT, load_features  # noqa: E402

OUT = ROOT / "results"


def stratify(f):
    s = pd.DataFrame({"GEOID": f.GEOID, "region": f.region})
    s["tribal"] = np.where(f.tribal_any.fillna(False).astype(bool), "tribal", "non-tribal")
    s["urban_rural"] = f.ur_class.fillna("unknown")
    s["svi_q"] = pd.qcut(f.svi_overall.where(f.svi_overall >= 0), 5, labels=[f"SVI Q{i}" for i in range(1, 6)])
    return s


def provenance_table(f, s, by):
    g = f.assign(**{by: s[by]}).groupby(["region", by], observed=True)
    t = g.agg(tracts=("GEOID", "size"), buildings=("ov_bld", "sum"), osm=("ov_bld_osm", "sum"),
              msft=("ov_bld_msft", "sum"), esri=("ov_bld_esri", "sum"), with_height=("ov_bld_height", "sum"),
              housing_units=("housing_units", "sum"), places=("ov_places", "sum"), fire=("ov_fire", "sum"),
              pop=("pop_total", "sum"), land_km2=("land_km2", "sum"))
    t["osm_share"] = t.osm / t.buildings
    t["ml_share"] = t.msft / t.buildings
    t["height_share"] = t.with_height / t.buildings
    t["buildings_per_hu"] = t.buildings / t.housing_units
    t["places_per_1k_pop"] = 1000 * t.places / t["pop"]
    t["fire_per_100k_pop"] = 1e5 * t.fire / t["pop"]
    t["fire_per_1k_km2"] = 1e3 * t.fire / t.land_km2
    return t.reset_index()


def tract_flags(f, s):
    """Flag populous, large tracts dominated by ML footprints with no mapped fire station.

    This describes Overture's *observed* dataset, not real-world station absence.
    ML provenance is tested directly; a low OSM share is NOT a reliable proxy
    because Esri and other source families may account for the remaining rows.
    """
    d = f.assign(tribal=s.tribal, urban_rural=s.urban_rural).copy()
    count = d.ov_bld.clip(lower=1)
    d["osm_share"] = d.ov_bld_osm / count
    d["ml_share"] = d.ov_bld_msft / count
    d["esri_share"] = d.ov_bld_esri / count
    flag = (
        (d.ov_bld > 0)
        & (d.ov_fire == 0)
        & (d.ml_share >= 0.95)
        & (d.pop_total > 1000)
        & (d.land_km2 > 50)
    )
    cols = [
        "GEOID", "region", "tribal", "urban_rural", "pop_total",
        "land_km2", "ov_bld", "osm_share", "ml_share", "esri_share",
        "ov_places", "ov_fire", "ov_ems", "ov_named_km",
    ]
    return d.loc[flag, cols].sort_values("pop_total", ascending=False)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    f = load_features()
    s = stratify(f)
    for by in ("tribal", "urban_rural", "svi_q"):
        t = provenance_table(f, s, by)
        t.to_csv(OUT / f"discovery_provenance_by_{by}.csv", index=False)
        print(t[["region", by, "tracts", "osm_share", "ml_share", "height_share",
                 "places_per_1k_pop", "fire_per_1k_km2"]].round(3).to_string(index=False))
    flags = tract_flags(f, s)
    flags.to_csv(OUT / "discovery_flagged_tracts.csv", index=False)
    print(len(flags), "flagged tracts;", int(flags.pop_total.sum()), "residents")
    print(flags.groupby(["region", "tribal"]).agg(n=("GEOID", "size"), pop=("pop_total", "sum")))
