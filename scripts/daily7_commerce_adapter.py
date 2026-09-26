#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ENGINE_VERSION = "0.2.0"
EXPORT_SCHEMA = "DAILY7_COMMERCE_OBSERVATION_EXPORT"
EXPORT_SCHEMA_VERSION = "1.0"
SOURCE_REPOSITORY = "maichicong835/Amazon-Daily7Source"
ALLOWED_SURFACES = {"ETSY", "AMAZON"}
ALLOWED_ENTITY_TYPES = {"MARKET_OBJECT", "MECHANISM"}
OBJECT_PROXIES = {"LISTING_FAVORITES", "LISTING_REVIEW_COUNT"}
MECHANISM_PROXIES = {"INDEPENDENT_LISTING_COUNT"}
ALLOWED_RECORD_FIELDS = {
    "observation_id", "observed_at", "entity_type", "entity_key",
    "linked_mechanism_key", "surface", "proxy", "unit", "value",
    "direction", "machine_observed", "source_ref", "candidate_key",
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
ASIN10 = re.compile(r"^[A-Z0-9]{10}$")
ETSY_LISTING = re.compile(r"^[0-9]+$")


def parse_dt(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def watchlist_mechanism_keys(watchlist):
    entries = watchlist.get("entries") or []
    return {str(x.get("mechanism_key", "")).strip() for x in entries if str(x.get("mechanism_key", "")).strip()}


def canonical_object_key(surface, raw_key):
    key = str(raw_key).strip()
    if surface == "ETSY":
        listing_id = key.split(":", 1)[-1] if key.startswith("etsy_listing:") else key
        if not ETSY_LISTING.fullmatch(listing_id):
            raise ValueError("ETSY MARKET_OBJECT entity_key must be numeric listing id or etsy_listing:<id>")
        return f"etsy_listing:{listing_id}"
    asin = key.split(":", 1)[-1].upper() if key.startswith("amazon_asin:") else key.upper()
    if not ASIN10.fullmatch(asin):
        raise ValueError("AMAZON MARKET_OBJECT entity_key must be ASIN or amazon_asin:<ASIN>")
    return f"amazon_asin:{asin}"


def validate_export(payload, allowed_mechanisms):
    if payload.get("schema") != EXPORT_SCHEMA:
        raise ValueError("invalid Daily7 commerce export schema")
    if payload.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise ValueError("unsupported Daily7 commerce export schema_version")
    if payload.get("source_repository") != SOURCE_REPOSITORY:
        raise ValueError("source repository drift")
    commit = str(payload.get("source_commit_sha", "")).strip()
    if not SHA40.fullmatch(commit):
        raise ValueError("source_commit_sha must be exact 40-char lowercase hex")
    run_key = str(payload.get("run_key", "")).strip()
    if not run_key:
        raise ValueError("run_key required")
    exported_at = parse_dt(payload.get("exported_at"))
    rows = payload.get("observations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("observations must be a non-empty list")

    seen_ids = set()
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("observation must be an object")
        extra = set(row) - ALLOWED_RECORD_FIELDS
        if extra:
            raise ValueError(f"unstructured/unsupported observation fields forbidden: {sorted(extra)}")
        required = {
            "observation_id", "observed_at", "entity_type", "entity_key",
            "surface", "proxy", "unit", "value", "direction",
            "machine_observed", "source_ref",
        }
        missing = required - set(row)
        if missing:
            raise ValueError(f"observation missing fields: {sorted(missing)}")
        oid = str(row["observation_id"]).strip()
        if not oid or oid in seen_ids:
            raise ValueError("observation_id must be non-empty and unique")
        seen_ids.add(oid)
        observed_at = parse_dt(row["observed_at"])
        if observed_at > exported_at:
            raise ValueError("observed_at may not be later than exported_at")
        entity_type = row["entity_type"]
        surface = row["surface"]
        proxy = row["proxy"]
        unit = str(row["unit"]).strip()
        if entity_type not in ALLOWED_ENTITY_TYPES:
            raise ValueError("P1 accepts MARKET_OBJECT or MECHANISM only")
        if surface not in ALLOWED_SURFACES:
            raise ValueError("P1 accepts ETSY or AMAZON only")
        if row["direction"] != "HIGHER_IS_STRONGER":
            raise ValueError("P1 accepts only HIGHER_IS_STRONGER proxies")
        if row["machine_observed"] is not True:
            raise ValueError("machine_observed must be true")
        if not unit:
            raise ValueError("unit required")
        if isinstance(row["value"], bool) or not isinstance(row["value"], (int, float)):
            raise ValueError("value must be numeric, not prose or boolean")
        source_ref = str(row["source_ref"]).strip()
        expected_prefix = f"{SOURCE_REPOSITORY}@{commit}:runs/{run_key}/"
        if not source_ref.startswith(expected_prefix):
            raise ValueError("source_ref must bind exact Daily7 commit and run path")

        out = dict(row)
        if entity_type == "MARKET_OBJECT":
            if proxy not in OBJECT_PROXIES:
                raise ValueError("MARKET_OBJECT proxy not allowed in P1")
            linked = str(row.get("linked_mechanism_key", "")).strip()
            if not linked or linked not in allowed_mechanisms:
                raise ValueError("MARKET_OBJECT requires linked_mechanism_key from current watchlist")
            out["entity_key"] = canonical_object_key(surface, row["entity_key"])
            out["linked_mechanism_key"] = linked
            out["supporting_only"] = False
        else:
            if proxy not in MECHANISM_PROXIES:
                raise ValueError("MECHANISM P1 proxy must be INDEPENDENT_LISTING_COUNT")
            entity_key = str(row["entity_key"]).strip()
            if entity_key not in allowed_mechanisms:
                raise ValueError("MECHANISM key must already exist in current watchlist")
            if row.get("linked_mechanism_key") not in (None, "", entity_key):
                raise ValueError("MECHANISM linked_mechanism_key may not point elsewhere")
            out["entity_key"] = entity_key
            out["supporting_only"] = True
        normalized.append(out)
    return commit, run_key, exported_at, normalized


def convert_export(payload, watchlist):
    mechanisms = watchlist_mechanism_keys(watchlist)
    commit, run_key, exported_at, rows = validate_export(payload, mechanisms)
    observations = []
    for row in rows:
        proxy = f"DAILY7_STRUCTURED::{row['proxy']}::{row['unit']}"
        note = (
            "Structured sanitized Daily7 commerce observation; no prose parsing. "
            f"evidence_role={'OBJECT_COMMERCE' if row['entity_type']=='MARKET_OBJECT' else 'MECHANISM_SUPPLY_SUPPORTING'}"
        )
        obs = {
            "observation_id": f"daily7-commerce::{run_key}::{row['observation_id']}",
            "observed_at": row["observed_at"],
            "entity_type": row["entity_type"],
            "entity_key": row["entity_key"],
            "surface": row["surface"],
            "proxy": proxy,
            "points": [{"t": row["observed_at"], "value": float(row["value"])}],
            "unit": row["unit"],
            "native_series": False,
            "supporting_only": row["supporting_only"],
            "provenance": {
                "source_ref": row["source_ref"],
                "machine_observed": True,
                "note": note,
            },
        }
        if row.get("candidate_key"):
            obs["candidate_key"] = row["candidate_key"]
        if row.get("linked_mechanism_key"):
            obs["linked_mechanism_key"] = row["linked_mechanism_key"]
        observations.append(obs)
    as_of = max(parse_dt(o["observed_at"]) for o in observations).isoformat()
    return {
        "schema": "A_MOMENTUM_OBSERVATION_SET",
        "engine_version": ENGINE_VERSION,
        "as_of": as_of,
        "source": f"{SOURCE_REPOSITORY}@{commit}:runs/{run_key}",
        "source_kind": "DAILY7_STRUCTURED_COMMERCE_EXPORT",
        "runtime_ingest_authorized": False,
        "runtime_ingest_blocker": "SANITIZED_EXPORT_TRANSPORT_NOT_MACHINE_PROVEN",
        "observations": observations,
        "anti_drift": {
            "legacy_prose_parsed": False,
            "daily7_credentials_used": False,
            "market_object_signal_auto_promotes_mechanism": False,
            "mechanism_supply_proxy_supporting_only": True,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--watchlist", default="runtime/watchlist.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = convert_export(load_json(args.input), load_json(args.watchlist))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("A_MOMENTUM_DAILY7_COMMERCE_ADAPTER_PASS", len(result["observations"]))
    print("A_MOMENTUM_DAILY7_COMMERCE_RUNTIME_INGEST_AUTHORIZED", result["runtime_ingest_authorized"])


if __name__ == "__main__":
    main()
