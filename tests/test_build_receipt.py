#!/usr/bin/env python3
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("builder",ROOT/"scripts"/"build_receipt.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class MomentumTests(unittest.TestCase):
    def test_one_point_unproven(self):
        x=m.analyze_points([{"t":"2026-09-20T00:00:00+00:00","value":1}])
        self.assertEqual(x["state"],"MOMENTUM_UNPROVEN")
    def test_two_points_velocity_only(self):
        x=m.analyze_points([
            {"t":"2026-09-20T00:00:00+00:00","value":10},
            {"t":"2026-09-20T01:00:00+00:00","value":12}])
        self.assertEqual(x["state"],"VELOCITY_POSITIVE_ACCELERATION_UNPROVEN")
        self.assertIsNone(x["acceleration"])
    def test_three_points_acceleration_candidate(self):
        x=m.analyze_points([
            {"t":"2026-09-20T00:00:00+00:00","value":10},
            {"t":"2026-09-20T01:00:00+00:00","value":11},
            {"t":"2026-09-20T02:00:00+00:00","value":14}])
        self.assertEqual(x["state"],"ACCELERATING_CANDIDATE")
        self.assertGreater(x["acceleration"],0)

if __name__=="__main__":
    unittest.main()
