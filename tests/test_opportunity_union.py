#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("opportunity_union",ROOT/"scripts"/"opportunity_union.py")
u=importlib.util.module_from_spec(spec); spec.loader.exec_module(u)

class OpportunityUnion(unittest.TestCase):
    def dual(self):
        return {
          "schema":"A_MOMENTUM_DUAL_WAVE_SHADOW",
          "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY",
          "raw_wave_capture":{"candidates":[]},
          "opportunity_intake":[
            {"merch_core":"shared","query_variants":["shared shirt"],"seed_evidence":[{"source_seed":"shirt"}],"any_breakout":False},
            {"merch_core":"m only","query_variants":["m only shirt"],"seed_evidence":[{"source_seed":"shirt"}],"any_breakout":False}
          ],
          "couplings":[],
          "credentials_used":False,
          "runtime_latest_mutation":False,
          "production_watchlist_mutation":False
        }
    def sticker(self):
        return {"merch_waves":[
          {"source_seed":"sticker","rank":1,"related_query":"shared sticker","rising_value":100,"is_breakout":False},
          {"source_seed":"stickers","rank":2,"related_query":"s only stickers","rising_value":200,"is_breakout":False}
        ]}
    def test_union_is_m_or_s_not_intersection(self):
        out=u.build(self.dual(),self.sticker())
        self.assertTrue(u.validate(out))
        self.assertEqual(out["opportunity_union_summary"],{"M_ONLY":1,"S_ONLY":1,"M_S_MULTI_RADAR":1,"TOTAL_UNIQUE":3})
        self.assertEqual(out["discovery_model"]["opportunity_union"],"M_OR_S")
        self.assertFalse(out["discovery_model"]["cross_radar_confirmation_required"])
    def test_s_only_enters_without_m(self):
        out=u.build(self.dual(),self.sticker())
        by={x["opportunity_core"]:x for x in out["opportunity_intake"]}
        self.assertEqual(by["s only"]["source_lane"],"S_ONLY")
        self.assertFalse(by["s only"]["requires_cross_radar_confirmation"])
    def test_exact_core_dedupe_preserves_both_origins(self):
        out=u.build(self.dual(),self.sticker())
        by={x["opportunity_core"]:x for x in out["opportunity_intake"]}
        self.assertEqual(by["shared"]["source_lane"],"M_S_MULTI_RADAR")
        self.assertEqual(by["shared"]["source_lanes"],["M","S"])
        self.assertIsNotNone(by["shared"]["m_evidence"])
        self.assertIsNotNone(by["shared"]["s_evidence"])
    def test_format_tokens_strip_only_for_s_core(self):
        self.assertEqual(u.s_core_key("vinyl sticker alpha"),"vinyl sticker alpha")
        self.assertEqual(u.s_core_key("alpha stickers"),"alpha")
        self.assertEqual(u.s_core_key("Sticker Mule"),"sticker mule")
        self.assertEqual(u.s_core_key("stickers for laptops"),"stickers for laptops")

if __name__=="__main__": unittest.main()
