"""Regression tests: high-ML provenance is not equivalent to low OSM provenance."""
import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discovery import tract_flags

class ProvenanceTests(unittest.TestCase):
    def test_true_ml_fraction(self):
        f = pd.DataFrame({
            "GEOID": ["1","2","3","4"],
            "region": ["test"] * 4,
            "ov_bld": [1000] * 4,
            "ov_bld_osm": [0,0,10,0],
            "ov_bld_msft": [980,100,950,980],
            "ov_bld_esri": [20,900,40,20],
            "ov_fire": [0,0,0,1],
            "ov_places": [4] * 4,
            "ov_ems": [0] * 4,
            "ov_named_km": [1.] * 4,
            "pop_total": [2000] * 4,
            "land_km2": [100.] * 4,
        })
        s = pd.DataFrame({"tribal":["tribal"]*4,"urban_rural":["Rural"]*4})
        result=tract_flags(f,s)
        self.assertEqual(set(result.GEOID), {"1","3"})
        self.assertTrue(result.ml_share.ge(.95).all())

if __name__ == "__main__":
    unittest.main()
