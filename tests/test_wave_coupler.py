#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("wave_coupler",ROOT/"scripts"/"wave_coupler.py")
w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

class Coupler(unittest.TestCase):
    def test_conservative_matching(self):
        self.assertTrue(w.conservative_match("Alpha Wave","alpha wave shirt"))
        self.assertTrue(w.conservative_match("Delta","delta shirts"))
        self.assertFalse(w.conservative_match("Delta","delta airlines shirt sale"))
    def test_states_and_boundaries(self):
        raw={"candidates":[{"wave_id":"r1","raw_trend_title":"Alpha Wave"},{"wave_id":"r2","raw_trend_title":"Beta Event"}]}
        merch={"provider_status":"PASS_WITH_DATA","merch_waves":[
            {"source_seed":"shirt","rank":1,"related_query":"Alpha Wave shirt","rising_value":"Breakout","is_breakout":True},
            {"source_seed":"shirts","rank":2,"related_query":"Crochet gifts shirts","rising_value":200,"is_breakout":False}
        ]}
        out=w.build(raw,merch)
        self.assertTrue(w.validate_output(out))
        self.assertEqual(out["coupling_summary"]["COUPLED_WAVE"],1)
        self.assertEqual(out["coupling_summary"]["RAW_ONLY_WAVE"],1)
        self.assertEqual(out["coupling_summary"]["MERCH_NATIVE_WAVE"],1)
        self.assertFalse(out["commercial_eligibility_automatic"])
        self.assertTrue(all(x["bridge_queries"]==[] and x["anchor_query"] is None for x in out["couplings"]))
if __name__=="__main__": unittest.main()
