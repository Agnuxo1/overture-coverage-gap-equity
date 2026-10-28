"""Cache simplified tract polygons (from the permitted ACS housing layer) for figures."""
from pathlib import Path
import duckdb, geopandas as gpd, shapely

ROOT = Path(__file__).resolve().parents[1]
BUCKET = "s3://us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge"
REGIONS = ("eastern-ok", "maricopa-az", "northern-ca", "south-central-tx")

if __name__ == "__main__":
    c = duckdb.connect(); c.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    out = ROOT / "data" / "geo"; out.mkdir(parents=True, exist_ok=True)
    for r in REGIONS:
        d = c.execute(f"SELECT GEOID, geometry FROM read_parquet('{BUCKET}/reference/{r}/{r}-census-acs-housing.parquet')").df()
        g = gpd.GeoDataFrame({"GEOID": d.GEOID}, geometry=shapely.from_wkb(d.geometry.map(bytes)), crs="OGC:CRS84")
        g = g.to_crs("EPSG:5070"); g["geometry"] = g.simplify(60)
        g.to_parquet(out / f"{r}.parquet"); print(r, len(g))
