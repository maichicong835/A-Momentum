#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("wave_capture",ROOT/"scripts"/"wave_capture.py")
w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

class WaveCapture(unittest.TestCase):
    def test_query_roles_remain_separate(self):
        xml=b"""<rss xmlns:ht="https://trends.google.com/trending/rss"><channel>
        <item><title>Alpha Wave</title><ht:approx_traffic>50K+</ht:approx_traffic></item>
        </channel></rss>"""
        c=w.parse_rss(xml,"TEST",5)[0]
        self.assertEqual(c["discovery_query"]["role"],"DISCOVERY_QUERY")
        self.assertEqual(c["commercial_bridge_status"],"UNSCREENED_RAW_WAVE")
        self.assertFalse(c["commercial_bridge_eligible"])
        self.assertEqual(c["bridge_queries"],[])
        self.assertEqual(c["bridge_query_templates"],["{trend} shirt","{trend} sticker"])
        self.assertIsNone(c["anchor_query"])
        self.assertFalse(c["automatic_watchlist_promotion"])

    def test_traffic_floor(self):
        self.assertEqual(w.traffic_floor("200K+"),200000)
        self.assertEqual(w.traffic_floor("1M+"),1000000)
        self.assertEqual(w.traffic_floor("500+"),500)
        self.assertIsNone(w.traffic_floor("unknown"))

    def test_shadow_output_cannot_claim_production_mutation(self):
        out=w.build_output([],"US","TEST","2026-09-29T00:00:00+00:00")
        self.assertTrue(w.validate_output(out))
        self.assertFalse(out["runtime_latest_mutation"])
        self.assertFalse(out["production_watchlist_mutation"])

if __name__=="__main__":
    unittest.main()
