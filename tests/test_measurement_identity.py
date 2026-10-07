#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
gt=load_module("gt_m1",ROOT/"scripts"/"google_trends.py"); br=load_module("br_m1",ROOT/"scripts"/"build_receipt.py")
class MeasurementIdentity(unittest.TestCase):
    def test_primary_and_fallback_identity(self):
        a=gt.stable_query_proxy_id("accountant sticker"); item={"query_family":["accountant sticker","spreadsheet sticker"],"measurement_identity":{"anchor_query":"accountant sticker","anchor_proxy_id":a}}
        s=gt.query_specs(item,3); self.assertEqual(s[0]["measurement_basis"],"PRIMARY_ANCHOR"); self.assertEqual(s[0]["query_proxy_id"],a); self.assertEqual(s[1]["measurement_basis"],"FALLBACK_PROXY"); self.assertNotEqual(s[1]["query_proxy_id"],a)
    def test_shared_anchor_visible(self):
        a=gt.stable_query_proxy_id("engineer sticker"); w={"entries":[
          {"watch_id":"a","mechanism_key":"m1","query_family":["engineer sticker"],"measurement_identity":{"anchor_query":"engineer sticker","anchor_proxy_id":a}},
          {"watch_id":"b","mechanism_key":"m2","query_family":["engineer sticker"],"measurement_identity":{"anchor_query":"engineer sticker","anchor_proxy_id":a}}]}
        _,g=br.measurement_contract(w); self.assertEqual(len(g),1); self.assertEqual(g[0]["mechanism_keys"],["m1","m2"])
    def test_truth_fallback_vs_gap(self):
        a1=gt.stable_query_proxy_id("engineer sticker"); a2=gt.stable_query_proxy_id("teacher sticker"); f=gt.stable_query_proxy_id("engineering humor sticker")
        w={"entries":[{"watch_id":"a","mechanism_key":"m1","query_family":["engineer sticker","engineering humor sticker"],"measurement_identity":{"anchor_query":"engineer sticker","anchor_proxy_id":a1}},
                      {"watch_id":"b","mechanism_key":"m2","query_family":["teacher sticker"],"measurement_identity":{"anchor_query":"teacher sticker","anchor_proxy_id":a2}}]}
        o={"observation_id":"o1","observed_at":"2026-10-07T05:00:00+00:00","entity_type":"MECHANISM","entity_key":"m1","surface":"GOOGLE_TRENDS","proxy":f,"points":[{"t":"2026-10-07T05:00:00+00:00","value":1}],
           "measurement_identity":{"anchor_query":"engineer sticker","anchor_proxy_id":a1,"query_used":"engineering humor sticker","query_proxy_id":f,"signal_basis":"FALLBACK_PROXY","native_window":{"window_start":"2026-10-01T00:00:00+00:00","window_end":"2026-10-07T05:00:00+00:00"}},
           "provenance":{"source_ref":"X","machine_observed":True,"query_used":"engineering humor sticker","query_ordinal":2,"measurement_basis":"FALLBACK_PROXY"}}
        sets=[{"as_of":"2026-10-07T06:00:00+00:00","observations":[o],"current_attempts":[
          {"entity_key":"m1","attempted_at":"2026-10-07T06:00:00+00:00","result":"SUCCESS","measurement_basis":"FALLBACK_PROXY","anchor_query":"engineer sticker","anchor_proxy_id":a1,"query_proxy_id":f},
          {"entity_key":"m2","attempted_at":"2026-10-07T06:00:00+00:00","result":"SENSOR_GAP","measurement_basis":"ANCHOR_GAP","anchor_query":"teacher sticker","anchor_proxy_id":a2}],"not_due":[]}]
        e=[{"entity_key":"m1"},{"entity_key":"m2"}]; br.attach_temporal_freshness(e,sets,"2026-10-07T06:00:00+00:00",8,w); by={x["entity_key"]:x for x in e}
        self.assertEqual(by["m1"]["measurement_truth_state"],"FALLBACK_PROXY"); self.assertEqual(by["m2"]["measurement_truth_state"],"ANCHOR_GAP")
if __name__=="__main__": unittest.main()
