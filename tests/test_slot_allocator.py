#!/usr/bin/env python3
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("slot_allocator",ROOT/"scripts"/"slot_allocator.py")
sa=importlib.util.module_from_spec(spec); spec.loader.exec_module(sa)

class SlotAllocator(unittest.TestCase):
    def test_budget_overflow_is_deferred_not_gap(self):
        out=sa.allocate(sa.synthetic_due(18),15)
        self.assertEqual(out["allocated_count"],15)
        self.assertEqual(out["deferred_count"],3)
        self.assertTrue(all(x["allocation_state"]=="DEFERRED_BY_ALLOCATION" for x in out["deferred"]))
        self.assertFalse(out["semantics"]["deferred_by_allocation_is_sensor_gap"])
        self.assertFalse(out["semantics"]["deferred_by_allocation_is_not_due"])
        self.assertFalse(out["semantics"]["deferred_by_allocation_advances_freshness"])

    def test_input_order_does_not_create_starvation_order(self):
        plan=sa.synthetic_due(18)
        a=sa.allocate(plan,15)
        b=sa.allocate(list(reversed(plan)),15)
        self.assertEqual([x["watch_id"] for x in a["allocated"]],
                         [x["watch_id"] for x in b["allocated"]])

    def test_normalized_overdue_priority(self):
        due=[
          {"watch_id":"warm","mechanism_key":"warm","cadence_hours":8,"elapsed_hours":12},
          {"watch_id":"hot","mechanism_key":"hot","cadence_hours":4,"elapsed_hours":8}
        ]
        self.assertEqual(sa.allocate(due,1)["allocated"][0]["watch_id"],"hot")

    def test_deferred_entries_recover_next_cycle(self):
        proof=sa.two_cycle_fairness_proof()
        self.assertTrue(proof["cycle_1_deferred_are_prioritized_next_cycle"])
        self.assertTrue(proof["all_entries_receive_measurement_by_cycle_2"])
        self.assertEqual(proof["two_cycle_unique_allocated_count"],18)

    def test_unobserved_entries_are_first(self):
        due=[
          {"watch_id":"observed","mechanism_key":"observed","cadence_hours":4,"elapsed_hours":20},
          {"watch_id":"new","mechanism_key":"new","cadence_hours":4,"elapsed_hours":None}
        ]
        self.assertEqual(sa.allocate(due,1)["allocated"][0]["watch_id"],"new")

if __name__=="__main__": unittest.main()
