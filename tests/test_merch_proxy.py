#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("merch_proxy",ROOT/"scripts"/"merch_proxy.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class MerchProxy(unittest.TestCase):
    def test_seed_family_is_small_and_distinct(self):
        self.assertEqual(m.normalize_seeds(["shirt","shirts","t shirt","shirt"]),["shirt","shirts","t shirt"])
    def test_value_semantics(self):
        self.assertTrue(m.normalize_value("Breakout")["breakout"])
        self.assertEqual(m.normalize_value(250)["numeric"],250.0)
    def test_provider_gap_is_not_zero_demand(self):
        def broken(): raise RuntimeError("provider")
        out=m.collect_once(["shirt"],client_factory=broken,retries=1,sleep_seconds=0)
        self.assertEqual(out["provider_status"],"SENSOR_GAP")
        self.assertFalse(out["provider_failure_is_zero_demand"])
        self.assertTrue(out["cross_seed_score_comparison_forbidden"])
        self.assertTrue(m.validate_output(out))
if __name__=="__main__": unittest.main()
