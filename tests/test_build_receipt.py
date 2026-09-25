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
    def test_zero_only_series_unproven(self):
        x=b.analyze_series([
          {"t":"2026-09-20T00:00:00+00:00","value":0},
          {"t":"2026-09-20T01:00:00+00:00","value":0},
          {"t":"2026-09-20T02:00:00+00:00","value":0}])
        self.assertEqual(x["series_state"],"MOMENTUM_UNPROVEN")
    def test_flat_positive_series_stable(self):
        x=b.analyze_series([
          {"t":"2026-09-20T00:00:00+00:00","value":10},
          {"t":"2026-09-20T01:00:00+00:00","value":10},
          {"t":"2026-09-20T02:00:00+00:00","value":10}])
        self.assertEqual(x["series_state"],"STABLE")
    def test_positive_but_decelerating_growth_stays_positive_velocity(self):
        x=b.analyze_series([
          {"t":"2026-09-20T00:00:00+00:00","value":10},
          {"t":"2026-09-20T01:00:00+00:00","value":20},
          {"t":"2026-09-20T02:00:00+00:00","value":25}])
        self.assertEqual(x["series_state"],"POSITIVE_VELOCITY")
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
    def test_temporal_coverage_metrics_are_factual(self):
        entities=[{"entity_key":"x"},{"entity_key":"y"}]
        sets=[{
          "as_of":"2026-09-25T04:00:00+00:00",
          "observations":[
            {"surface":"GOOGLE_TRENDS","entity_key":"x","observed_at":"2026-09-25T03:00:00+00:00"},
            {"surface":"GOOGLE_TRENDS","entity_key":"y","observed_at":"2026-09-24T00:00:00+00:00"}
          ],
          "current_attempts":[
            {"entity_key":"x","attempted_at":"2026-09-25T04:00:00+00:00","result":"SUCCESS"},
            {"entity_key":"y","attempted_at":"2026-09-25T04:00:00+00:00","result":"SENSOR_GAP"}
          ]
        }]
        s=b.attach_temporal_freshness(entities,sets,"2026-09-25T04:00:00+00:00",8)
        self.assertEqual(s["entity_count"],2)
        self.assertEqual(s["fresh_entity_count"],1)
        self.assertEqual(s["stale_entity_count"],1)
        self.assertEqual(s["fresh_entity_ratio"],0.5)
        self.assertEqual(s["current_cycle_success_count"],1)
        self.assertEqual(s["current_cycle_gap_count"],1)
if __name__=="__main__":unittest.main()
