#!/usr/bin/env python3
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

gt=load_module("gt_continuity",ROOT/"scripts"/"google_trends.py")
br=load_module("br_continuity",ROOT/"scripts"/"build_receipt.py")

def obs(key,t,value=1):
    return {
      "observation_id":"o-"+key+"-"+t,
      "observed_at":t,
      "entity_type":"MECHANISM",
      "entity_key":key,
      "surface":"GOOGLE_TRENDS",
      "proxy":"P",
      "points":[{"t":t,"value":value}],
      "provenance":{"machine_observed":True}
    }

class Continuity(unittest.TestCase):
    def test_gap_preserves_last_good(self):
        old=obs("a","2026-09-23T00:00:00+00:00")
        merged=gt.merge_last_good([old],[])
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]["observed_at"],old["observed_at"])

    def test_new_success_replaces_same_mechanism(self):
        old=obs("a","2026-09-23T00:00:00+00:00")
        new=obs("a","2026-09-23T04:00:00+00:00",2)
        merged=gt.merge_last_good([old],[new])
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]["observed_at"],new["observed_at"])

    def test_gap_does_not_refresh_evidence_clock(self):
        old=obs("a","2026-09-23T00:00:00+00:00")
        sets=[{
          "as_of":"2026-09-23T09:00:00+00:00",
          "observations":[old],
          "current_attempts":[{
            "entity_key":"a","attempted_at":"2026-09-23T09:00:00+00:00",
            "result":"SENSOR_GAP","error_class":"TooManyRequestsError"
          }],
          "not_due":[]
        }]
        entities=[{"entity_key":"a"}]
        summary=br.attach_temporal_freshness(entities,sets,"2026-09-23T09:00:00+00:00",8)
        self.assertEqual(entities[0]["last_successful_observed_at"],old["observed_at"])
        self.assertEqual(entities[0]["latest_attempt_state"],"SENSOR_GAP")
        self.assertEqual(entities[0]["temporal_evidence_freshness_at_generation"],"STALE_OVER_THRESHOLD")
        self.assertEqual(summary["fresh_entity_count"],0)

    def test_not_due_preserves_without_refresh(self):
        old=obs("a","2026-09-23T04:00:00+00:00")
        sets=[{
          "as_of":"2026-09-23T06:00:00+00:00",
          "observations":[old],
          "current_attempts":[],
          "not_due":[{"entity_key":"a","last_observed_at":old["observed_at"]}]
        }]
        entities=[{"entity_key":"a"}]
        br.attach_temporal_freshness(entities,sets,"2026-09-23T06:00:00+00:00",8)
        self.assertEqual(entities[0]["latest_attempt_state"],"NOT_DUE")
        self.assertEqual(entities[0]["last_successful_observed_at"],old["observed_at"])
        self.assertEqual(entities[0]["temporal_evidence_freshness_at_generation"],"FRESH_WITHIN_THRESHOLD")

if __name__=="__main__": unittest.main()
