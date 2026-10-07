#!/usr/bin/env python3
"""M2a shadow-only fair slot allocator. Not wired to production runtime."""
import argparse, json, math
from pathlib import Path

SCHEMA="A_MOMENTUM_M2A_SLOT_ALLOCATION_SHADOW"
STATE_ALLOCATED="ALLOCATED_FOR_MEASUREMENT"
STATE_DEFERRED="DEFERRED_BY_ALLOCATION"

def _num(value,name):
    try: out=float(value)
    except Exception as e: raise ValueError(f"{name} must be numeric") from e
    if not math.isfinite(out): raise ValueError(f"{name} must be finite")
    return out

def priority_key(item):
    cadence=_num(item.get("cadence_hours"),"cadence_hours")
    if cadence<=0: raise ValueError("cadence_hours must be > 0")
    elapsed=item.get("elapsed_hours")
    unobserved=elapsed is None
    if unobserved:
        overdue_multiple=float("inf"); elapsed_value=float("inf")
    else:
        elapsed_value=_num(elapsed,"elapsed_hours")
        if elapsed_value<0: raise ValueError("elapsed_hours must be >= 0")
        overdue_multiple=elapsed_value/cadence
    stable_id=str(item.get("watch_id") or item.get("mechanism_key") or "")
    if not stable_id: raise ValueError("watch_id or mechanism_key required")
    return (0 if unobserved else 1, -overdue_multiple, -elapsed_value, stable_id)

def allocate(due,budget=15):
    budget=int(budget)
    if budget<0: raise ValueError("budget must be >= 0")
    ranked=sorted(list(due),key=priority_key)
    allocated=ranked[:budget]
    deferred=ranked[budget:]
    def decorate(item,state,rank):
        cadence=float(item["cadence_hours"])
        elapsed=item.get("elapsed_hours")
        return {
          **item,
          "allocation_rank":rank,
          "allocation_state":state,
          "overdue_multiple":None if elapsed is None else round(float(elapsed)/cadence,6)
        }
    a=[decorate(x,STATE_ALLOCATED,i+1) for i,x in enumerate(allocated)]
    d=[decorate(x,STATE_DEFERRED,len(a)+i+1) for i,x in enumerate(deferred)]
    return {
      "schema":SCHEMA,
      "mode":"M2A_SHADOW_SYNTHETIC_ONLY",
      "budget":budget,
      "due_count":len(ranked),
      "allocated_count":len(a),
      "deferred_count":len(d),
      "allocated":a,
      "deferred":d,
      "semantics":{
        "allocation_budget_is_capacity_not_demand":True,
        "deferred_by_allocation_is_sensor_gap":False,
        "deferred_by_allocation_is_not_due":False,
        "deferred_by_allocation_advances_freshness":False,
        "production_runtime_wired":False
      }
    }

def synthetic_due(count=18,elapsed=8.0,cadence=4.0):
    return [{
      "watch_id":f"synthetic-watch-{i:02d}",
      "mechanism_key":f"synthetic-mechanism-{i:02d}",
      "cadence_class":"HOT",
      "cadence_hours":cadence,
      "elapsed_hours":elapsed,
      "last_observed_at":"2026-10-07T00:00:00+00:00"
    } for i in range(1,count+1)]

def two_cycle_fairness_proof():
    first=allocate(synthetic_due(),15)
    first_ids={x["watch_id"] for x in first["allocated"]}
    deferred_ids={x["watch_id"] for x in first["deferred"]}
    cycle2=[]
    for x in synthetic_due():
        y=dict(x)
        y["elapsed_hours"]=12.0 if y["watch_id"] in deferred_ids else 4.0
        cycle2.append(y)
    second=allocate(list(reversed(cycle2)),15)
    second_ids={x["watch_id"] for x in second["allocated"]}
    return {
      "cycle_1_allocated_count":len(first_ids),
      "cycle_1_deferred_count":len(deferred_ids),
      "cycle_2_allocated_count":len(second_ids),
      "two_cycle_unique_allocated_count":len(first_ids|second_ids),
      "universe_count":18,
      "all_entries_receive_measurement_by_cycle_2":len(first_ids|second_ids)==18,
      "cycle_1_deferred_are_prioritized_next_cycle":deferred_ids.issubset(second_ids)
    }

def self_test():
    plan=synthetic_due()
    a=allocate(plan,15)
    b=allocate(list(reversed(plan)),15)
    assert [x["watch_id"] for x in a["allocated"]]==[x["watch_id"] for x in b["allocated"]]
    assert a["allocated_count"]==15 and a["deferred_count"]==3
    proof=two_cycle_fairness_proof()
    assert proof["all_entries_receive_measurement_by_cycle_2"]
    assert proof["cycle_1_deferred_are_prioritized_next_cycle"]
    mixed=[
      {"watch_id":"hot","mechanism_key":"hot","cadence_hours":4,"elapsed_hours":8},
      {"watch_id":"warm","mechanism_key":"warm","cadence_hours":8,"elapsed_hours":12}
    ]
    assert allocate(mixed,1)["allocated"][0]["watch_id"]=="hot"
    assert a["semantics"]["deferred_by_allocation_is_sensor_gap"] is False
    assert a["semantics"]["deferred_by_allocation_advances_freshness"] is False
    print("A_MOMENTUM_M2A_SLOT_ALLOCATOR_SELF_TEST_PASS")
    print(json.dumps(proof,sort_keys=True))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--due-plan")
    ap.add_argument("--budget",type=int,default=15)
    ap.add_argument("--out")
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        self_test(); return
    if not args.due_plan or not args.out:
        raise SystemExit("--due-plan and --out required unless --self-test")
    plan=json.loads(Path(args.due_plan).read_text(encoding="utf-8"))
    out=allocate(plan.get("due",[]),args.budget)
    out["source_due_plan_schema"]=plan.get("schema")
    out["source_as_of"]=plan.get("as_of")
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
