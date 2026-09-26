#!/usr/bin/env python3
"""Read-only native OMG drain validation, shared by verification and settlement.

validate_execution(decomposition, operation, initiative, call) returns the validated
drain ID and manifest rows. call(*args) must return decoded JSON from read-only gc
commands in the caller's city/rig context. Invalid proof raises ValueError.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def metadata(bead):
    require(isinstance(bead, dict) and isinstance(bead.get("metadata"), dict),
            "invalid bead metadata")
    return bead["metadata"]


def validate_execution(decomposition, operation, initiative, call):
    """Validate execution only; callers retain approval, source and receipt checks."""
    def show(identifier):
        value = call("bd", "show", identifier)
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        require(isinstance(value, dict) and value.get("id") == identifier,
                f"missing or mismatched execution bead {identifier}")
        return value

    def matches(meta, expected, label):
        require(all(meta.get(k) == v for k, v in expected.items()),
                f"{label} bindings or outcome mismatch")

    workflow, convoy = decomposition["workflow"], decomposition["convoy"]
    expected = [item["id"] for item in decomposition["items"]]
    require(expected and len(set(expected)) == len(expected), "invalid expected member inventory")
    run = {"gc.var.operation": operation, "gc.var.initiative": initiative}
    matches(metadata(show(workflow)), {**run, "gc.kind": "workflow",
            "gc.formula_name": "omg-build", "gc.formula_contract": "graph.v2",
            "gc.input_convoy_id": convoy}, "build workflow")
    beads = call("bd", "list", "--all", "--limit", "0", "--long")
    require(isinstance(beads, list), "invalid execution bead inventory")
    candidates = [b for b in beads if isinstance(b, dict)
                  and isinstance(b.get("metadata"), dict)
                  and b["metadata"].get("gc.root_bead_id") == workflow
                  and b["metadata"].get("gc.kind") == "drain"
                  and (b["metadata"].get("gc.step_id") == "omg-build.implement"
                       or b["metadata"].get("gc.step_ref") == "omg-build.implement"
                       or b["metadata"].get("gc.drain_parent_convoy_id") == convoy)]
    require(len(candidates) == 1, "expected exactly one implementation drain")
    drain = show(candidates[0]["id"])
    meta = metadata(drain)
    matches(meta, {"gc.root_bead_id": workflow, "gc.kind": "drain",
                   "gc.step_id": "omg-build.implement", "gc.step_ref": "omg-build.implement",
                   "gc.drain_parent_convoy_id": convoy,
                   "gc.drain_formula": "omg-work", "gc.drain_context": "shared",
                   "gc.drain_state": "succeeded", "gc.outcome": "pass"}, "implementation drain")
    require(drain.get("status") == "closed", "implementation drain is not closed")
    manifest = json.loads(meta.get("gc.drain_manifest.v1", "null"))
    require(isinstance(manifest, dict), "missing drain manifest")
    require(type(manifest.get("version")) is int and manifest["version"] == 1
            and manifest.get("context") == "shared"
            and manifest.get("parent_convoy_id") == convoy
            and manifest.get("formula") == "omg-work", "invalid drain manifest schema or bindings")
    rows = manifest.get("rows")
    require(isinstance(rows, list) and rows, "empty or missing drain manifest rows")
    for row in rows:
        require(isinstance(row, dict), "invalid drain manifest row")
        for key in ("member_id", "unit_key", "unit_convoy_id", "item_root_key", "item_root_id", "outcome_bead_id"):
            require(isinstance(row.get(key), str) and row[key].strip(), f"missing manifest {key}")
        require(type(row.get("index")) is int, "invalid manifest index")
        require(row.get("status") == "succeeded" and row.get("outcome_kind") == "pass",
                "manifest row did not succeed/pass")
    require(sorted(r["member_id"] for r in rows) == sorted(expected),
            "manifest member inventory differs from decomposition")
    require(sorted(r["index"] for r in rows) == list(range(len(rows))), "invalid manifest indices")
    for key in ("item_root_id", "item_root_key", "unit_convoy_id", "unit_key"):
        require(len({r[key] for r in rows}) == len(rows), f"duplicate manifest {key}")
    for row in rows:
        item = show(row["item_root_id"])
        require(item.get("status") == "closed", f"item workflow {item['id']} is not closed")
        require(row["outcome_bead_id"] == (metadata(item).get("gc.outcome_bead_id") or item["id"]),
                "manifest outcome bead differs from item workflow")
        matches(metadata(item), {**run, "gc.kind": "workflow", "gc.formula_name": "omg-work",
                "gc.formula_contract": "graph.v2",
                "gc.outcome": "pass", "gc.drain_control_id": drain["id"],
                "gc.drain_member_id": row["member_id"], "gc.input_convoy_id": row["unit_convoy_id"],
                "gc.item_root_key": row["item_root_key"], "gc.drain_index": str(row["index"]),
                "gc.drain_count": str(len(rows))}, f"item workflow {item['id']}")
        # A root can have been closed manually ahead of controller settlement.
        # Closed failed retry attempts are legitimate; unfinished work is not.
        children = [b for b in beads if isinstance(b, dict)
                    and isinstance(b.get("metadata"), dict)
                    and b["metadata"].get("gc.root_bead_id") == item["id"]]
        finalizers = [b for b in children if b["metadata"].get("gc.kind") == "workflow-finalize"]
        require(len(finalizers) == 1, "expected exactly one item workflow finalizer")
        finalizer = show(finalizers[0]["id"])
        matches(metadata(finalizer), {"gc.root_bead_id": item["id"],
                "gc.kind": "workflow-finalize", "gc.step_id": "omg-work.workflow-finalize",
                "gc.step_ref": "omg-work.workflow-finalize", "gc.outcome": "pass"}, "item finalizer")
        require(finalizer.get("status") == "closed", "item workflow finalizer is unfinished")
        require(all(b.get("status") == "closed" for b in children
                    if b["metadata"].get("gc.kind") != "spec"),
                "item workflow has unfinished execution")
        unit = call("convoy", "status", row["unit_convoy_id"])
        require(isinstance(unit, dict) and isinstance(unit.get("convoy"), dict)
                and unit["convoy"].get("id") == row["unit_convoy_id"],
                "unit convoy identity differs from manifest")
        require(isinstance(unit, dict) and isinstance(unit.get("children"), list)
                and len(unit["children"]) == 1
                and unit["children"][0].get("id") == row["member_id"],
                "unit convoy membership differs from manifest")
    return {"drain_id": drain["id"], "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--city")
    parser.add_argument("--rig")
    args = parser.parse_args()
    context = [arg for key in ("city", "rig") if getattr(args, key)
               for arg in ("--" + key, getattr(args, key))]

    def call(*command):
        return json.loads(subprocess.check_output(
            [os.environ.get("GC_BIN", "gc"), *command, *context, "--json"], text=True))

    try:
        root = Path(args.root)
        baseline = json.loads((root / "baseline.json").read_text())
        result = validate_execution(json.loads((root / "decomposition.json").read_text()),
                                    baseline["operation"], baseline["initiative"], call)
        print(json.dumps(result))
    except (ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"omg verify execution: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
