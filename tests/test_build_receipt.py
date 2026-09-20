#!/usr/bin/env python3
import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("b",ROOT/"scripts"/"build_receipt.py")
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class T(unittest.TestCase):
    def test_one_point(self):
        self.assertEqual(b.analyze_series([{"t":"2026-09-20T00:00:00+00:00","value":1}])["series_state"],"MOMENTUM_UNPROVEN")
    def test_two_points(self):
        x=b.analyze_series([{"t":"2026-09-20T00:00:00+00:00","value":10},{"t":"2026-09-20T01:00:00+00:00","value":12}])
        self.assertEqual(x["series_state"],"POSITIVE_VELOCITY");self.assertIsNone(x["acceleration"])
    def test_three_points_accel(self):
        x=b.analyze_series([{"t":"2026-09-20T00:00:00+00:00","value":10},{"t":"2026-09-20T01:00:00+00:00","value":11},{"t":"2026-09-20T02:00:00+00:00","value":14}])
        self.assertEqual(x["series_state"],"POSITIVE_ACCELERATION")
    def test_cross_surface_confirmation(self):
        ss=[
          {"entity_key":"x","surface":"GOOGLE_TRENDS","series_state":"POSITIVE_ACCELERATION"},
          {"entity_key":"x","surface":"PINTEREST_TRENDS","series_state":"POSITIVE_ACCELERATION"}]
        x=b.aggregate_entities(ss,{},{"x":set()})[0]
        self.assertEqual(x["state"],"ACCELERATING_CONFIRMED")
    def test_single_noncommerce_accel_not_confirmed(self):
        ss=[{"entity_key":"x","surface":"GOOGLE_TRENDS","series_state":"POSITIVE_ACCELERATION"}]
        x=b.aggregate_entities(ss,{},{"x":set()})[0]
        self.assertEqual(x["state"],"VELOCITY_POSITIVE_ACCELERATION_UNPROVEN")
if __name__=="__main__":unittest.main()
