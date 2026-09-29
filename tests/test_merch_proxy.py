#!/usr/bin/env python3
import importlib.util, json, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("merch_proxy",ROOT/"scripts"/"merch_proxy.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class FakeClient:
    RELATED_QUERIES_URL="RELATED"; GET_METHOD="get"; tz=0
    def __init__(self,fail_seed=None,build_error=None):
        self.fail_seed=fail_seed; self.build_error=build_error
        self.related_queries_widget_list=[]; self.build_calls=0
    def build_payload(self,seeds,cat,timeframe,geo,gprop):
        self.build_calls+=1
        if self.build_error: raise self.build_error
        self.related_queries_widget_list=[
            {"request":{"restriction":{"complexKeywordsRestriction":{"keyword":[{"value":s}]}}},"token":"t-"+s}
            for s in seeds
        ]
    def _get_data(self,url,method,trim_chars,params):
        seed=json.loads(params["req"])["restriction"]["complexKeywordsRestriction"]["keyword"][0]["value"]
        if seed==self.fail_seed:
            class TooManyRequestsError(Exception): pass
            raise TooManyRequestsError("Google returned 429")
        return {"default":{"rankedList":[{"rankedKeyword":[]},{"rankedKeyword":[{"query":seed+" rising","value":250}]}]}}

class MerchProxy(unittest.TestCase):
    def test_seed_family_is_small_and_distinct(self):
        self.assertEqual(m.normalize_seeds(["shirt","shirts","t shirt","shirt"]),["shirt","shirts","t shirt"])

    def test_value_semantics(self):
        self.assertTrue(m.normalize_value("Breakout")["breakout"])
        self.assertEqual(m.normalize_value(250)["numeric"],250.0)

    def test_batch_payload_reduces_builds_and_keeps_all_seeds(self):
        c=FakeClient()
        out=m.collect_once(["shirt","shirts","t shirt"],client_factory=lambda:c,build_retries=1,between_seed_seconds=0,rate_limit_cooldown_seconds=0,sleep_fn=lambda _:None)
        self.assertTrue(m.validate_output(out))
        self.assertEqual(c.build_calls,1)
        self.assertEqual(out["transport"]["related_query_attempt_count"],3)
        self.assertEqual(out["merch_wave_count"],3)
        self.assertEqual(out["provider_status"],"PASS_WITH_DATA")

    def test_rate_limit_preserves_prior_success_and_opens_circuit(self):
        c=FakeClient(fail_seed="shirts")
        out=m.collect_once(["shirt","shirts","t shirt"],client_factory=lambda:c,build_retries=1,between_seed_seconds=0,rate_limit_cooldown_seconds=0,sleep_fn=lambda _:None)
        self.assertEqual(out["provider_status"],"PARTIAL_WITH_DATA")
        self.assertEqual(out["merch_wave_count"],1)
        self.assertEqual(out["transport"]["related_query_attempt_count"],2)
        self.assertEqual(out["transport"]["rate_limit_event_count"],1)
        self.assertTrue(out["transport"]["rate_limit_circuit_open"])
        self.assertEqual(out["seed_results"][0]["result"],"SUCCESS")
        self.assertEqual(out["seed_results"][1]["gap_state"],"RATE_LIMITED_RELATED_QUERY")
        self.assertEqual(out["seed_results"][2]["gap_state"],"RATE_LIMIT_CIRCUIT_OPEN")

    def test_batch_build_gap_is_not_zero_demand(self):
        class TooManyRequestsError(Exception): pass
        c=FakeClient(build_error=TooManyRequestsError("429"))
        out=m.collect_once(["shirt"],client_factory=lambda:c,build_retries=1,between_seed_seconds=0,rate_limit_cooldown_seconds=0,sleep_fn=lambda _:None)
        self.assertEqual(out["provider_status"],"SENSOR_GAP")
        self.assertFalse(out["provider_failure_is_zero_demand"])
        self.assertFalse(out["provider_gap_is_no_rising_queries"])
        self.assertTrue(out["transport"]["rate_limit_circuit_open"])
        self.assertTrue(m.validate_output(out))

if __name__=="__main__":
    unittest.main()
