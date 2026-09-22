#!/usr/bin/env python3
import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("gt",ROOT/"scripts"/"google_trends.py")
gt=importlib.util.module_from_spec(spec);spec.loader.exec_module(gt)
class T(unittest.TestCase):
    def test_completed_blocks(self):
        from datetime import datetime,timedelta,timezone
        base=datetime(2026,1,1,tzinfo=timezone.utc)
        rows=[(base+timedelta(hours=i),float(i%9)) for i in range(72)]
        b=gt.completed_24h_blocks(rows); self.assertEqual(len(b),3); self.assertTrue(all(x["sample_count"]==24 for x in b))
    def test_gap_fail_closed(self):
        from datetime import datetime,timedelta,timezone
        base=datetime(2026,1,1,tzinfo=timezone.utc)
        rows=[(base+timedelta(hours=i),1.0) for i in range(72) if i!=60]
        self.assertEqual(gt.completed_24h_blocks(rows),[])
if __name__=="__main__": unittest.main()
