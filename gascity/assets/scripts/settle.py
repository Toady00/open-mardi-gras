#!/usr/bin/env python3
"""Plan or revision-fenced settlement of verified OMG source tasks."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from verify_execution import metadata, require, validate_execution


class Unsupported(ValueError):
    """The backend cannot safely perform settlement."""


class Transport:
    def __init__(self, city, rig, run=subprocess.run):
        self.context = ["--city", city, "--rig", rig]
        self.run = run

    def context_values(self):
        """Explicit context, exposed separately from the callable bead transport."""
        return self.context[1], self.context[3]

    def bind_context(self, city, rig_name):
        # gc resolves --rig only against registered rig names (rigByName), so
        # the validated registered name is retained; the caller's path form is
        # never forwarded. The name-to-path binding was checked against
        # baseline.repo before this call.
        self.context = ["--city", str(city), "--rig", str(rig_name)]

    def output(self, command):
        result = self.run(command, text=True, capture_output=True)
        if result.returncode:
            raise ValueError(result.stderr.strip() or result.stdout.strip()
                             or f"command failed with exit {result.returncode}")
        return result.stdout

    def call(self, *args, rig=True):
        # rig=False issues a city-scoped command; an unvalidated --rig argument
        # (possibly a path gc cannot resolve) must never reach gc.
        context = self.context if rig else self.context[:2]
        return json.loads(self.output([os.environ.get("GC_BIN", "gc"),
                                       *args, *context, "--json"]))

    def capable(self):
        try:
            help_text = self.output([os.environ.get("GC_BIN", "gc"), "bd", "update",
                                     "--help", *self.context, "--json"])
        except ValueError as exc:
            raise Unsupported(f"revision capability probe failed: {exc}") from exc
        return re.search(r"(?<![\w-])--if-revision(?![\w-])", help_text) is not None

    def quality(self, root):
        result = json.loads(self.output([
            "bash", str(Path(__file__).with_name("verify.sh")), "--stage", "quality",
            "--root", str(root), *self.context, "--json"]))
        require(result == {"outcome": "pass"}, "quality verifier did not pass")


def read_json(root, name):
    value = json.loads((root / f"{name}.json").read_text())
    require(isinstance(value, dict), f"{name}.json must be an object")
    return value


def canonical_directory(value, label):
    require(isinstance(value, str) and Path(value).is_absolute(),
            f"{label} must be an absolute directory path")
    path = Path(value).resolve(strict=True)
    require(path.is_dir(), f"{label} must be a directory")
    return path


def bind_context(baseline, transport):
    """Bind approval and execution stores before quality or any bead access."""
    city_arg, rig_arg = transport.context_values()
    city = canonical_directory(city_arg, "city")
    require(city == canonical_directory(baseline["city"], "baseline.city"),
            "caller city differs from baseline.city")
    repo = canonical_directory(baseline["repo"], "baseline.repo")
    require(isinstance(rig_arg, str) and rig_arg.strip(), "rig must be explicit")
    by_path = Path(rig_arg).is_absolute()
    if by_path:
        rig_path = canonical_directory(rig_arg, "rig")
    else:
        require(re.fullmatch(r"[A-Za-z0-9_-]+", rig_arg),
                "rig must be a registered name or an absolute path")
    # gc RigListJSON contains city_path and rigs[{name,path,...}]. Paths are
    # absolute, resolved by gc from city.toml, never relative to cwd. The
    # listing is read city-scoped: the caller's rig argument is not yet known
    # to be something gc can resolve.
    listing = transport.call("rig", "list", rig=False)
    require(isinstance(listing, dict) and isinstance(listing.get("rigs"), list),
            "invalid gc rig list response")
    require(canonical_directory(listing.get("city_path"), "rig list city_path") == city,
            "rig list belongs to another city")
    registered = [rig for rig in listing["rigs"]
                  if isinstance(rig, dict) and not rig.get("hq")
                  and isinstance(rig.get("name"), str) and rig["name"].strip()]
    if by_path:
        def registered_path(rig):
            value = rig.get("path")
            if not isinstance(value, str) or not Path(value).is_absolute():
                return None
            try:
                return Path(value).resolve(strict=True)
            except OSError:
                return None  # another rig's missing checkout is not this caller's error
        matches = [rig for rig in registered if registered_path(rig) == rig_path]
        require(len(matches) == 1, "rig path must resolve to exactly one registered rig")
    else:
        matches = [rig for rig in registered if rig["name"] == rig_arg]
        require(len(matches) == 1, "rig name must resolve to exactly one registered rig")
        rig_path = canonical_directory(matches[0].get("path"), "registered rig path")
    require(rig_path == repo, "caller rig differs from baseline.repo")
    transport.bind_context(city, matches[0]["name"])


def proof(root, transport):
    # Read on both sides of verification so we do not bind a changed local receipt.
    before = [read_json(root, name) for name in ("baseline", "decomposition", "review")]
    bind_context(before[0], transport)
    transport.quality(root)
    after = [read_json(root, name) for name in ("baseline", "decomposition", "review")]
    require(before == after, "settlement evidence changed during quality verification")
    baseline, decomposition, review = after
    revision = review["revision"]
    require(isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{40,64}", revision),
            "review needs an exact commit revision")
    execution = validate_execution(decomposition, baseline["operation"],
                                   baseline["initiative"], transport.call)
    return {"operation": baseline["operation"], "workflow": decomposition["workflow"],
            "drain": execution["drain_id"], "revision": revision,
            "rows": sorted(execution["rows"], key=lambda row: row["index"])}


def show(transport, identifier):
    bead = transport.call("bd", "show", identifier)
    if isinstance(bead, list) and len(bead) == 1:
        bead = bead[0]
    require(isinstance(bead, dict) and bead.get("id") == identifier,
            f"missing or mismatched source {identifier}")
    return bead


def binding(evidence, row):
    return {"omg.settled_by": evidence["workflow"], "omg.item_root": row["item_root_id"],
            "omg.settled_drain": evidence["drain"]}


def validate_source(bead, root, evidence, row):
    identifier = row["member_id"]
    meta = metadata(bead)
    require((bead.get("issue_type") or bead.get("type")) == "task"
            and all(bead[key] == "task" for key in ("issue_type", "type") if key in bead),
            f"{identifier}: settlement requires a plain task source")
    require(meta.get("omg.artifact_root") == str(root)
            and meta.get("omg.operation") == evidence["operation"]
            and meta.get("gc.kind") is None, f"{identifier}: source ownership conflict")
    require(bead.get("assignee") in (None, ""), f"{identifier}: source is assigned")
    require(meta.get("gc.exclusive_drain_reservation") in (None, ""),
            f"{identifier}: exclusive reservation is not empty")
    expected = binding(evidence, row)
    if bead.get("status") == "closed":
        require(all(meta.get(k) == v for k, v in expected.items()),
                f"{identifier}: closed by another settlement or externally")
        return "already-settled"
    require(bead.get("status") == "open", f"{identifier}: source is not open")
    require(all(meta.get(k) in (None, "") for k in expected),
            f"{identifier}: open source has settlement metadata")
    return "would-close"


def validate_order(rows, sources, transport, closing=False):
    # Native manifest indices are topological. Check actual source edges rather
    # than trusting decomposition prose or silently choosing a different order.
    positions = {row["member_id"]: row["index"] for row in rows}
    for identifier, bead in sources.items():
        dependencies = bead.get("dependencies", [])
        require(isinstance(dependencies, list), f"{identifier}: invalid dependencies")
        for dep in dependencies:
            require(isinstance(dep, dict), f"{identifier}: invalid dependency")
            require(dep.get("issue_id", identifier) == identifier,
                    f"{identifier}: dependency belongs to another source")
            kind = dep.get("dependency_type") or dep.get("type") or "blocks"
            require(not (dep.get("dependency_type") and dep.get("type"))
                    or dep["dependency_type"] == dep["type"],
                    f"{identifier}: conflicting dependency types")
            target = dep.get("depends_on_id") or dep.get("id")
            require(isinstance(target, str) and target, f"{identifier}: missing dependency ID")
            if kind != "blocks":
                raise Unsupported(f"{identifier}: unsupported dependency gate {kind!r}")
            if target in positions:
                require(positions[target] < positions[identifier],
                        f"{identifier}: manifest order violates blocks dependency on {target}")
            # Preflight permits earlier members which this batch will close.
            # At close time all blockers, including earlier members, must be closed.
            # These reads are not a graph-wide fence: CAS only protects the source.
            if target not in positions or closing:
                require(show(transport, target).get("status") == "closed",
                        f"{identifier}: unresolved blocking dependency {target}")


def atomic_receipt(root, receipt):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=root, prefix=".settlement-",
                                         suffix=".json", delete=False) as stream:
            temporary = stream.name
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, root / "settlement.json")
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def settle(root, transport, apply=False):
    require(root.is_absolute() and root.is_dir(), "root must be an existing absolute directory")
    evidence = proof(root, transport)
    rows = evidence["rows"]
    sources = {row["member_id"]: show(transport, row["member_id"]) for row in rows}
    items = [{"source": row["member_id"], "item_root": row["item_root_id"],
              "source_revision": sources[row["member_id"]].get("revision"),
              "status": validate_source(sources[row["member_id"]], root, evidence, row)}
             for row in rows]
    validate_order(rows, sources, transport)
    receipt = {key: value for key, value in evidence.items() if key != "rows"}
    receipt.update(status="planned", items=items)
    if not apply:
        return receipt, 0
    if not transport.capable():
        raise Unsupported("gc bd update does not advertise --if-revision; no sources mutated")
    for item in items:
        # Revision is an opaque signed int64 equality token, not a counter.
        # Explicit zero is valid; absent values and bools are not revision tokens.
        revision = item["source_revision"]
        if type(revision) is not int or not -(2 ** 63) <= revision < 2 ** 63:
            raise Unsupported(f"{item['source']}: signed int64 source revision unavailable; no sources mutated")
    require(proof(root, transport) == evidence, "quality or execution evidence changed before apply")
    # No writes until every source and the entire proof have passed validation.
    receipt["status"] = "applying"
    for item in items:
        if item["status"] == "would-close":
            item["status"] = "pending"
    atomic_receipt(root, receipt)
    for row, item in zip(rows, items):
        try:
            identifier = row["member_id"]
            current = show(transport, identifier)
            status = validate_source(current, root, evidence, row)
            require(type(current.get("revision")) is int
                    and current["revision"] == item["source_revision"],
                    f"{identifier}: source changed since validation")
            # Expanded dependency status may change as earlier sources close.
            # Their IDs and edge direction still must obey the manifest order.
            validate_order(rows, {identifier: current}, transport, closing=True)
            if status != "already-settled":
                flags = [arg for key, value in binding(evidence, row).items()
                         for arg in ("--set-metadata", f"{key}={value}")]
                note = (f"OMG settlement operation={evidence['operation']} workflow={evidence['workflow']} "
                        f"drain={evidence['drain']} item={row['item_root_id']} "
                        f"reviewed_revision={evidence['revision']} evidence={root}/review.json")
                transport.call("bd", "update", identifier, "--status", "closed",
                               "--if-revision", str(item["source_revision"]), *flags,
                               "--append-notes", note)
                require(validate_source(show(transport, identifier), root, evidence, row)
                        == "already-settled", f"{identifier}: closure was not persisted")
                item["status"] = "closed"
            atomic_receipt(root, receipt)
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
            item.update(status="failed", error=str(exc))
            receipt.update(status="failed", error=str(exc))
            if isinstance(exc, Unsupported):
                receipt["failure_kind"] = "unsupported"
            atomic_receipt(root, receipt)
            return receipt, 2 if isinstance(exc, Unsupported) else 1
    receipt["status"] = "settled"
    atomic_receipt(root, receipt)
    return receipt, 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--rig", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true", help="output is always JSON")
    args = parser.parse_args(argv)
    try:
        require(bool(args.city.strip()) and bool(args.rig.strip()), "city and rig must be nonempty")
        result, code = settle(Path(args.root), Transport(args.city, args.rig), args.apply)
    except Unsupported as exc:
        result, code = {"status": "unsupported", "error": str(exc)}, 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        result, code = {"status": "failed", "error": str(exc)}, 1
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
