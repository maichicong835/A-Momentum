#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("adapter", ROOT / "scripts" / "daily7_commerce_adapter.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

bspec = importlib.util.spec_from_file_location("build_receipt", ROOT / "scripts" / "build_receipt.py")
build_receipt = importlib.util.module_from_spec(bspec)
bspec.loader.exec_module(build_receipt)

SHA = "a" * 40
RUN = "2026-09-26-1200-fresh"
WATCHLIST = {
    "entries": [
        {"mechanism_key": "programmer_interruption_boundary"},
        {"mechanism_key": "engineer_coffee_problem_solving"}
    ]
}


def base_export(row):
    return {
        "schema": "DAILY7_COMMERCE_OBSERVATION_EXPORT",
        "schema_version": "1.0",
        "source_repository": "maichicong835/Amazon-Daily7Source",
        "source_commit_sha": SHA,
        "run_key": RUN,
        "exported_at": "2026-09-26T12:10:00+07:00",
        "observations": [row],
    }


def object_row():
    return {
        "observation_id": "etsy-1623087869-favorites",
        "observed_at": "2026-09-26T12:00:00+07:00",
        "entity_type": "MARKET_OBJECT",
        "entity_key": "1623087869",
        "linked_mechanism_key": "programmer_interruption_boundary",
        "surface": "ETSY",
        "proxy": "LISTING_FAVORITES",
        "unit": "count",
        "value": 431,
        "direction": "HIGHER_IS_STRONGER",
        "machine_observed": True,
        "source_ref": f"maichicong835/Amazon-Daily7Source@{SHA}:runs/{RUN}/commerce-observations.json",
        "candidate_key": "purrgrammer-cat-programmer",
    }


class Daily7CommerceAdapterTests(unittest.TestCase):
    def test_valid_market_object_stays_object_level(self):
        out = adapter.convert_export(base_export(object_row()), WATCHLIST)
        self.assertFalse(out["runtime_ingest_authorized"])
        self.assertEqual(out["runtime_ingest_blocker"], "SANITIZED_EXPORT_TRANSPORT_NOT_MACHINE_PROVEN")
        self.assertEqual(len(out["observations"]), 1)
        obs = out["observations"][0]
        self.assertEqual(obs["entity_type"], "MARKET_OBJECT")
        self.assertEqual(obs["entity_key"], "etsy_listing:1623087869")
        self.assertEqual(obs["linked_mechanism_key"], "programmer_interruption_boundary")
        self.assertEqual(obs["surface"], "ETSY")
        self.assertEqual(obs["proxy"], "DAILY7_STRUCTURED::LISTING_FAVORITES::count")
        self.assertFalse(obs["supporting_only"])

    def test_one_structured_snapshot_remains_momentum_unproven(self):
        out = adapter.convert_export(base_export(object_row()), WATCHLIST)
        series = build_receipt.analyze_series(out["observations"][0]["points"])
        self.assertEqual(series["series_state"], "MOMENTUM_UNPROVEN")
        self.assertIsNone(series["velocity"])
        self.assertIsNone(series["acceleration"])

    def test_prose_field_is_rejected_not_parsed(self):
        row = object_row()
        row["observed"] = "431 favorites and 46 reviews"
        with self.assertRaisesRegex(ValueError, "unstructured/unsupported"):
            adapter.convert_export(base_export(row), WATCHLIST)

    def test_commit_bound_source_ref_required(self):
        row = object_row()
        row["source_ref"] = f"maichicong835/Amazon-Daily7Source@{'b'*40}:runs/{RUN}/commerce-observations.json"
        with self.assertRaisesRegex(ValueError, "source_ref must bind exact Daily7 commit"):
            adapter.convert_export(base_export(row), WATCHLIST)

    def test_market_object_cannot_use_mechanism_supply_proxy(self):
        row = object_row()
        row["proxy"] = "INDEPENDENT_LISTING_COUNT"
        with self.assertRaisesRegex(ValueError, "MARKET_OBJECT proxy not allowed"):
            adapter.convert_export(base_export(row), WATCHLIST)

    def test_mechanism_cannot_use_object_engagement_proxy(self):
        row = object_row()
        row.update({
            "observation_id": "programmer-favorites",
            "entity_type": "MECHANISM",
            "entity_key": "programmer_interruption_boundary",
            "proxy": "LISTING_FAVORITES",
        })
        row.pop("linked_mechanism_key")
        with self.assertRaisesRegex(ValueError, "MECHANISM P1 proxy"):
            adapter.convert_export(base_export(row), WATCHLIST)

    def test_mechanism_supply_signal_is_supporting_only(self):
        row = {
            "observation_id": "programmer-independent-listings",
            "observed_at": "2026-09-26T12:00:00+07:00",
            "entity_type": "MECHANISM",
            "entity_key": "programmer_interruption_boundary",
            "surface": "ETSY",
            "proxy": "INDEPENDENT_LISTING_COUNT",
            "unit": "count",
            "value": 18,
            "direction": "HIGHER_IS_STRONGER",
            "machine_observed": True,
            "source_ref": f"maichicong835/Amazon-Daily7Source@{SHA}:runs/{RUN}/commerce-observations.json",
        }
        out = adapter.convert_export(base_export(row), WATCHLIST)
        obs = out["observations"][0]
        self.assertEqual(obs["entity_type"], "MECHANISM")
        self.assertTrue(obs["supporting_only"])
        self.assertEqual(obs["entity_key"], "programmer_interruption_boundary")

    def test_new_mechanism_cannot_expand_watchlist(self):
        row = {
            "observation_id": "new-mechanism-independent-listings",
            "observed_at": "2026-09-26T12:00:00+07:00",
            "entity_type": "MECHANISM",
            "entity_key": "unapproved_new_mechanism",
            "surface": "ETSY",
            "proxy": "INDEPENDENT_LISTING_COUNT",
            "unit": "count",
            "value": 10,
            "direction": "HIGHER_IS_STRONGER",
            "machine_observed": True,
            "source_ref": f"maichicong835/Amazon-Daily7Source@{SHA}:runs/{RUN}/commerce-observations.json",
        }
        with self.assertRaisesRegex(ValueError, "must already exist in current watchlist"):
            adapter.convert_export(base_export(row), WATCHLIST)

    def test_object_link_must_target_existing_watchlist_mechanism(self):
        row = object_row()
        row["linked_mechanism_key"] = "unapproved_new_mechanism"
        with self.assertRaisesRegex(ValueError, "linked_mechanism_key from current watchlist"):
            adapter.convert_export(base_export(row), WATCHLIST)


if __name__ == "__main__":
    unittest.main()
