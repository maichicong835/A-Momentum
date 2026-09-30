#!/usr/bin/env python3
import importlib.util, json, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("sticker_proxy",ROOT/"scripts"/"sticker_proxy.py")
s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

class FakeClient:
    RELATED_QUERIES_URL="RELATED"; GET_METHOD="get"; tz=0
    def __init__(self): self.related_queries_widget_list=[]
    def build_payload(self,seeds,cat,timeframe,geo,gprop):
        self.related_queries_widget_list=[
          {"request":{"restriction":{"complexKeywordsRestriction":{"keyword":[{"value":x}]}}},"token":"t-"+x}
          for x in seeds
        ]
    def _get_data(self,url,method,trim_chars,params):
        seed=json.loads(params["req"])["restriction"]["complexKeywordsRestriction"]["keyword"][0]["value"]
        return {"default":{"rankedList":[{"rankedKeyword":[]},{"rankedKeyword":[{"query":seed+" alpha","value":100}]}]}}

class StickerProxy(unittest.TestCase):
    def test_fixed_seed_family(self):
        self.assertEqual(s.DEFAULT_SEEDS,["sticker","stickers","vinyl sticker"])
    def test_independent_radar_semantics(self):
        out=s.collect(s.DEFAULT_SEEDS,client_factory=FakeClient,build_retries=1,between_seed_seconds=0,rate_limit_cooldown_seconds=0,sleep_fn=lambda _:None)
        self.assertTrue(s.validate(out))
        self.assertEqual(out["radar"],"S_STICKER_NATIVE")
        self.assertFalse(out["m_confirmation_authority"])
        self.assertFalse(out["commercial_eligibility_authority"])
        self.assertEqual(out["merch_wave_count"],3)
    def test_rows_are_sticker_native_evidence(self):
        out=s.collect(["sticker"],client_factory=FakeClient,build_retries=1,between_seed_seconds=0,rate_limit_cooldown_seconds=0,sleep_fn=lambda _:None)
        self.assertTrue(all(r["role"]=="STICKER_NATIVE_RISING_QUERY" for r in out["merch_waves"]))

if __name__=="__main__": unittest.main()
