#!/usr/bin/env python3
"""Google Trends open-wave capture for A-Momentum SHADOW mode only.

This collector never writes runtime/latest or runtime/watchlist. It captures
Google Trends Trending Now RSS items and emits non-authoritative shadow
candidates with three explicitly separated query roles:
DISCOVERY, BRIDGE, and unassigned ANCHOR.
"""
import argparse
import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ENGINE_VERSION = "0.2.0"
DEFAULT_URL = "https://trends.google.com/trending/rss?geo={geo}"
HT_NS = "https://trends.google.com/trending/rss"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def normalize_text(value):
    return " ".join(str(value or "").split()).strip()

def traffic_floor(value):
    s = normalize_text(value).upper().replace(",", "")
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([KMB]?)\+?", s)
    if not m:
        return None
    n = float(m.group(1))
    mult = {"":1, "K":1000, "M":1000000, "B":1000000000}[m.group(2)]
    return int(n * mult)

def canonical_pubdate(value):
    value = normalize_text(value)
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except Exception:
        return value

def read_source(source_file=None, url=None, timeout=20):
    if source_file:
        return Path(source_file).read_bytes(), "FILE_FIXTURE"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":"Mozilla/5.0 A-Momentum-Wave-Shadow/0.2.0",
            "Accept":"application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.1"
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), url

def find_text(item, local_name):
    # Namespace-tolerant because Google has changed RSS namespace declarations before.
    for child in item.iter():
        tag = child.tag.split("}")[-1]
        if tag == local_name:
            text = normalize_text(child.text)
            if text:
                return text
    return None

def find_all_text(item, local_name, limit=5):
    out=[]
    for child in item.iter():
        if child.tag.split("}")[-1] == local_name:
            value=normalize_text(child.text)
            if value and value not in out:
                out.append(value)
            if len(out) >= limit:
                break
    return out

def build_candidate(item, source_ref):
    title=normalize_text(find_text(item,"title"))
    if not title:
        return None
    digest=hashlib.sha256(title.casefold().encode("utf-8")).hexdigest()[:16]
    traffic=normalize_text(find_text(item,"approx_traffic"))
    discovery=title
    bridges=[
        {"role":"BRIDGE_QUERY","query":f"{title} shirt","intent":"MERCH_EXPRESSION_PROBE"},
        {"role":"BRIDGE_QUERY","query":f"{title} sticker","intent":"STICKER_EXPRESSION_PROBE"},
    ]
    return {
        "wave_id":f"gt-wave-{digest}",
        "raw_trend_title":title,
        "discovery_query":{"role":"DISCOVERY_QUERY","query":discovery},
        "bridge_queries":bridges,
        "anchor_query":None,
        "anchor_status":"UNASSIGNED_REQUIRES_SHADOW_EVIDENCE_AND_EXPLICIT_PROMOTION",
        "promotion_state":"SHADOW_UNPROVEN",
        "automatic_watchlist_promotion":False,
        "production_eligible":False,
        "downstream_commercial_refresh_required":True,
        "downstream_property_trademark_safety_recheck_required":True,
        "approx_search_traffic":traffic or None,
        "approx_search_traffic_floor":traffic_floor(traffic),
        "published_at":canonical_pubdate(find_text(item,"pubDate")),
        "news_context_titles":find_all_text(item,"news_item_title",5),
        "source_ref":source_ref,
    }

def parse_rss(payload, source_ref, limit=50):
    root=ET.fromstring(payload)
    candidates=[]
    seen=set()
    for item in root.findall(".//item"):
        candidate=build_candidate(item,source_ref)
        if not candidate or candidate["wave_id"] in seen:
            continue
        seen.add(candidate["wave_id"])
        candidates.append(candidate)
        if len(candidates) >= max(1,int(limit)):
            break
    return candidates

def build_output(candidates, geo, source_ref, captured_at=None):
    return {
        "schema":"A_MOMENTUM_WAVE_SHADOW",
        "schema_version":"1.0",
        "engine_version":ENGINE_VERSION,
        "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY",
        "captured_at":captured_at or now_iso(),
        "geo":geo,
        "source":"GOOGLE_TRENDS_TRENDING_NOW_RSS",
        "source_ref":source_ref,
        "candidate_count":len(candidates),
        "credentials_used":False,
        "runtime_latest_mutation":False,
        "production_watchlist_mutation":False,
        "anchor_assignment_automatic":False,
        "candidates":candidates,
    }

def validate_output(out):
    assert out["schema"]=="A_MOMENTUM_WAVE_SHADOW"
    assert out["mode"]=="SHADOW_ONLY_NO_PRODUCTION_AUTHORITY"
    assert out["credentials_used"] is False
    assert out["runtime_latest_mutation"] is False
    assert out["production_watchlist_mutation"] is False
    assert out["candidate_count"]==len(out["candidates"])
    for c in out["candidates"]:
        assert c["discovery_query"]["role"]=="DISCOVERY_QUERY"
        assert c["anchor_query"] is None
        assert c["automatic_watchlist_promotion"] is False
        assert all(x["role"]=="BRIDGE_QUERY" for x in c["bridge_queries"])
    return True

def self_test():
    xml=b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
      <item><title>Example Wave</title><ht:approx_traffic>200K+</ht:approx_traffic>
      <pubDate>Tue, 29 Sep 2026 00:00:00 GMT</pubDate>
      <ht:news_item><ht:news_item_title>Context A</ht:news_item_title></ht:news_item></item>
      <item><title>Second Wave</title><ht:approx_traffic>1M+</ht:approx_traffic></item>
    </channel></rss>"""
    c=parse_rss(xml,"SELF_TEST",10)
    assert len(c)==2
    assert c[0]["approx_search_traffic_floor"]==200000
    assert c[1]["approx_search_traffic_floor"]==1000000
    assert c[0]["bridge_queries"][0]["query"]=="Example Wave shirt"
    assert c[0]["bridge_queries"][1]["query"]=="Example Wave sticker"
    assert c[0]["anchor_query"] is None
    out=build_output(c,"US","SELF_TEST","2026-09-29T00:00:00+00:00")
    validate_output(out)
    print("A_MOMENTUM_WAVE_SHADOW_SELF_TEST_PASS",len(c))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--geo",default="US")
    ap.add_argument("--url")
    ap.add_argument("--source-file")
    ap.add_argument("--limit",type=int,default=50)
    ap.add_argument("--timeout",type=int,default=20)
    ap.add_argument("--out")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test()
        return
    if not a.out:
        raise SystemExit("--out required")
    url=a.url or DEFAULT_URL.format(geo=a.geo)
    payload,source_ref=read_source(a.source_file,url,a.timeout)
    candidates=parse_rss(payload,source_ref,a.limit)
    if not candidates:
        raise RuntimeError("NO_TRENDING_NOW_WAVES_PARSED")
    out=build_output(candidates,a.geo,source_ref)
    validate_output(out)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A_MOMENTUM_WAVE_SHADOW_CAPTURE_PASS",len(candidates))
    print("A_MOMENTUM_WAVE_SHADOW_PRODUCTION_MUTATION",False)

if __name__=="__main__":
    main()
