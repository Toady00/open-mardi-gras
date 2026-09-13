#!/usr/bin/env python3
"""Revision records and launch receipts for conversational OMG initiatives.

Gas City owns dispatch and retries. This command performs bounded state changes
using the native metadata CAS, and records intent before invoking any workflow.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import uuid


KEY = "omg.state"
KINDS = {"discussion", "prd", "hld", "adr", "spec", "build-report"}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def now():
    return datetime.now(timezone.utc).isoformat()


def run(*args, cwd=None, data=None):
    result = subprocess.run(args, cwd=cwd, input=data, capture_output=True)
    if result.returncode:
        raise ValueError(f"{args[0]} failed: {result.stderr.decode().strip()}")
    return result.stdout


def gc(*args):
    return json.loads(run(os.environ.get("GC_BIN", "gc"), *args, "--json"))


def one(value):
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, dict) or not value.get("id"):
        raise ValueError("expected one bead")
    return value


def safe_relative(value):
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or str(path) != value
            or any(p in {".", "..", ".git"} for p in path.parts)
            or "\n" in value or "\r" in value):
        raise ValueError(f"unsafe relative path: {value}")
    return value


def git(repo, *args):
    return run("git", "-C", str(repo), *args)


def frontmatter(content):
    # Use the same YAML reader as the Hindsight pack, without introducing a
    # second frontmatter dialect or Python dependency.
    if not content.startswith(b"---\n"):
        raise ValueError("document requires YAML frontmatter")
    return json.loads(run("yq", "--front-matter=extract", "-o=json", ".", data=content))


def snapshot(repo, directory, revision, kind, paths=None):
    safe_relative(directory)
    if not re.fullmatch(r"[0-9a-f]{40,64}", revision):
        raise ValueError("revision must be an exact Git commit SHA")
    if git(repo, "rev-parse", f"{revision}^{{commit}}").decode().strip() != revision:
        raise ValueError("revision is not a commit")
    rows = git(repo, "ls-tree", "-r", "-z", revision, "--", directory).split(b"\0")
    files = {}
    ids = set()
    types = set()
    requested = set(paths or [])
    for row in filter(None, rows):
        entry, raw_path = row.split(b"\t", 1)
        mode, typ, _ = entry.decode().split()
        path = safe_relative(raw_path.decode())
        if kind == "direction":
            if path not in requested:
                continue
        elif not path.endswith(".md") or "/reports/" in path:
            continue
        if typ != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"snapshot cannot include symlink or submodule: {path}")
        content = git(repo, "show", f"{revision}:{path}")
        item = {"sha256": hashlib.sha256(content).hexdigest()}
        if kind == "direction":
            if path.endswith(".json"):
                ir = json.loads(content)
                if not isinstance(ir, dict) or not ir.get("diagram_type"):
                    raise ValueError(f"not Archify IR: {path}")
            elif not path.endswith(".html"):
                raise ValueError("direction evidence must be JSON IR or rendered HTML")
        else:
            fm = frontmatter(content)
            if fm.get("type") not in KINDS - {"build-report"}:
                raise ValueError(f"unexpected authored document type: {path}")
            if fm.get("schema_version") != 2 or fm.get("status") not in {"draft", "accepted"}:
                raise ValueError(f"expected Hindsight schema 2 draft/accepted document: {path}")
            identity = fm.get("id", "")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", identity) or identity in ids:
                raise ValueError(f"missing or duplicate stable document ID: {path}")
            ids.add(identity)
            types.add(fm["type"])
            item.update(id=identity, type=fm["type"], status=fm["status"])
        files[path] = item
    if kind == "direction":
        if requested != set(files) or not requested:
            raise ValueError("all requested direction files must exist inside the initiative")
        jsons = {p[:-5] for p in files if p.endswith(".json")}
        htmls = {p[:-5] for p in files if p.endswith(".html")}
        if not jsons or jsons != htmls:
            raise ValueError("each IR requires its adjacent same-stem HTML rendering")
    elif not {"discussion", "prd", "hld", "spec"} <= types:
        raise ValueError("document set requires discussion, PRD, HLD, and at least one spec")
    result = dict(revision=revision, files=files)
    result["digest"] = hashlib.sha256(encoded(files).encode()).hexdigest()
    return result


def assert_current(state, snap):
    """Conservatively invalidate readiness on any tracked or untracked doc edit."""
    dirty = git(state["repo"], "status", "--porcelain", "--untracked-files=all", "--", state["directory"])
    if dirty.strip():
        raise ValueError("initiative has uncommitted edits; commit and refine the changed set")
    head = git(state["repo"], "rev-parse", "HEAD").decode().strip()
    current = snapshot(state["repo"], state["directory"], head, "docs")
    if current["digest"] != snap["digest"]:
        raise ValueError("document revision changed; shared refinement is required")


def assert_accepted_current(state):
    """Acceptance permits only status/timestamp publication, not hidden edits."""
    snap = state["accepted"]["snapshot"]
    dirty = git(state["repo"], "status", "--porcelain", "--untracked-files=all", "--", state["directory"])
    if dirty.strip():
        raise ValueError("commit the accepted document revisions before starting")
    head = git(state["repo"], "rev-parse", "HEAD").decode().strip()
    current = snapshot(state["repo"], state["directory"], head, "docs")
    if set(current["files"]) != set(snap["files"]):
        raise ValueError("document inventory changed after approval; refine again")
    for path in snap["files"]:
        before = git(state["repo"], "show", f"{snap['revision']}:{path}")
        after = git(state["repo"], "show", f"{head}:{path}")
        old_fm, new_fm = frontmatter(before), frontmatter(after)
        for fm in (old_fm, new_fm):
            fm.pop("status", None)
            fm.pop("updated_at", None)
        old_body = before.split(b"\n---\n", 1)[1]
        new_body = after.split(b"\n---\n", 1)[1]
        if old_fm != new_fm or old_body != new_body:
            raise ValueError(f"{path} changed substantively after approval; refine again")


class Ledger:
    def __init__(self):
        info = gc("rig", "list")
        self.city = info["city_path"]
        self.store = "city:" + info["city_name"]
        self.rigs = {r["name"]: r["path"] for r in info["rigs"] if not r.get("hq")}

    def bd(self, *args):
        return gc("bd", "--city", self.city, *args)

    def load(self, bead):
        raw = one(self.bd("show", bead))["metadata"].get(KEY)
        if not isinstance(raw, str):
            raise ValueError("not an OMG initiative record")
        state = json.loads(raw)
        if state.get("schema") != 1:
            raise ValueError("unsupported initiative record")
        return state, raw

    def save(self, bead, previous, state):
        value = encoded(state)
        answer = gc("beads", "metadata-cas", bead, "--city", self.city,
                    "--store-ref", self.store, "--key", KEY,
                    "--expected", previous, "--next", value)
        if answer.get("outcome") not in {"swapped", "already_next"}:
            raise ValueError("initiative changed concurrently; reread it before retrying")
        return value


def authority(args):
    if not args.authority or not args.authority.strip():
        raise ValueError("record the human's explicit instruction and session/message reference")
    return dict(evidence=args.authority, at=now())


def materialize(state, snap, bead):
    # Build inputs are outside every default Hindsight docs root. They are
    # frozen copies, never a second published document with the same ID.
    repo = Path(state["repo"]).resolve()
    root = repo / ".omg" / bead / snap["digest"]
    for path, expected in snap["files"].items():
        content = git(state["repo"], "show", f"{snap['revision']}:{path}")
        if hashlib.sha256(content).hexdigest() != expected["sha256"]:
            raise ValueError("snapshot hash mismatch")
        target = root / path
        for parent in [target, *target.parents]:
            if parent == repo:
                break
            if parent.is_symlink():
                raise ValueError("snapshot path contains a symlink")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != content:
                raise ValueError("frozen snapshot was modified")
        else:
            target.write_bytes(content)
    return str(root)


def validate_reviews(state):
    snap = state.get("reviewed")
    if not snap:
        raise ValueError("no reviewed document snapshot")
    assert_current(state, snap)
    for role in ("product", "technical"):
        review = state.get("reviews", {}).get(role, {})
        if (review.get("digest") != snap["digest"]
                or review.get("direction") != state["direction"]["digest"]
                or review.get("verdict") != "pass"):
            raise ValueError(f"missing passing {role} review for this revision")
        if hashlib.sha256(Path(review["artifact"]).read_bytes()).hexdigest() != review["artifact_sha256"]:
            raise ValueError(f"{role} review evidence changed")
    return snap


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["init", "list", "show", "direction", "snapshot",
                                     "review", "ready", "decision", "revise", "accept",
                                     "materialize", "generate", "refine", "start",
                                     "recover", "settle", "check"])
    p.add_argument("bead", nargs="?")
    p.add_argument("--slug")
    p.add_argument("--title")
    p.add_argument("--rig", default=None)
    p.add_argument("--revision")
    p.add_argument("--file", action="append", default=[])
    p.add_argument("--authority")
    p.add_argument("--role", choices=["product", "technical"])
    p.add_argument("--verdict", choices=["pass", "required", "human"])
    p.add_argument("--artifact")
    p.add_argument("--input", choices=["direction", "specs"], default="direction")
    p.add_argument("--note")
    p.add_argument("--workflow")
    p.add_argument("--operation")
    p.add_argument("--binding", default="omg")
    p.add_argument("--push", choices=["true", "false"], default="false")
    p.add_argument("--open-pr", choices=["true", "false"], default="false")
    args = p.parse_args(argv)
    ledger = Ledger()
    if args.action == "init":
        if not args.slug or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.slug):
            raise ValueError("--slug must be a lowercase initiative identifier")
        rig = args.rig if args.rig is not None else os.environ.get("GC_RIG", "")
        repo = str(Path(ledger.rigs[rig] if rig else ledger.city).resolve())
        if git(repo, "rev-parse", "--show-toplevel").decode().strip() != repo:
            raise ValueError("initiating city/rig must be a Git repository root")
        directory = f"docs/initiatives/{args.slug}"
        # Do not race to create two records for the same directory. The unique
        # Beads primary key is deterministic within this city's work store.
        prefix = run(os.environ.get("GC_BIN", "gc"), "bd", "--city", ledger.city,
                     "config", "get", "issue_prefix").decode().strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", prefix):
            raise ValueError("cannot resolve city's Beads issue_prefix")
        identity = hashlib.sha256(f"{repo}/{directory}".encode()).hexdigest()[:20]
        bead = f"{prefix}-omg{identity}"
        state = dict(schema=1, repo=repo, rig=rig, directory=directory,
                     slug=args.slug, phase="discussion", directions=[], operations={}, reviews={})
        result = one(ledger.bd("create", args.title or args.slug, "--id", bead,
                              "--status", "pinned", "--labels", "omg:initiative",
                              "--description", "Conversational initiative record; not dispatchable work.",
                              "--metadata", encoded({KEY: encoded(state)})))
        print(encoded(result))
        return
    if args.action == "list":
        rows = ledger.bd("list", "--all", "--limit", "0", "--label", "omg:initiative")
        result = []
        for row in rows:
            state = json.loads(row["metadata"][KEY])
            result.append(dict(bead=row["id"], title=row["title"], phase=state["phase"],
                               repo=state["repo"], directory=state["directory"],
                               reviewed=state.get("reviewed", {}).get("revision"),
                               decision=state.get("decision")))
        print(encoded(result))
        return
    if not args.bead:
        raise ValueError("initiative bead ID required")
    state, old = ledger.load(args.bead)
    action = args.action
    if action == "show":
        print(encoded(state))
        return
    if action == "direction":
        approval = authority(args)
        snap = snapshot(state["repo"], state["directory"], args.revision or "", "direction", args.file)
        snap["approval"] = approval
        snap["previous"] = state.get("direction", {}).get("digest")
        state["directions"].append(snap)
        state["direction"] = snap
        state.update(phase="direction-approved", reviews={})
    elif action == "revise":
        state.update(phase="draft", reviews={})
    elif action == "snapshot":
        if not state.get("direction"):
            raise ValueError("approve direction before reviewing documents")
        snap = snapshot(state["repo"], state["directory"], args.revision or "", "docs")
        assert_current(state, snap)
        state.update(reviewed=snap, reviews={}, phase="refining")
    elif action == "review":
        if not args.role or not args.verdict or not args.artifact:
            raise ValueError("--role, --verdict, and persisted --artifact are required")
        snap = state.get("reviewed")
        if not snap:
            raise ValueError("snapshot the whole document set first")
        assert_current(state, snap)
        artifact = Path(args.artifact).resolve(strict=True)
        # Review evidence is deliberately not an eligible authored document.
        if Path(state["repo"], "docs") in artifact.parents:
            raise ValueError("put review evidence outside docs/, under .omg/")
        state["reviews"][args.role] = dict(
            verdict=args.verdict, artifact=str(artifact),
            artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            digest=snap["digest"], direction=state["direction"]["digest"], at=now())
    elif action in {"ready", "check"}:
        if action == "check" and state.get("phase") == "needs-human":
            print(encoded(dict(outcome="human", note=state.get("decision"))))
            return
        validate_reviews(state)
        if action == "check":
            print(encoded(dict(outcome="pass")))
            return
        state["phase"] = "approval-ready"
    elif action == "decision":
        if not args.note:
            raise ValueError("--note must explain the unresolved decision")
        state.update(phase="needs-human", decision=args.note)
    elif action == "accept":
        approval = authority(args)
        if state["phase"] != "approval-ready":
            raise ValueError("only the exact approval-ready revision can be accepted")
        snap = validate_reviews(state)
        state.update(accepted=dict(snapshot=snap, direction=state["direction"], approval=approval),
                     phase="accepted")
        state.setdefault("acceptances", []).append(dict(
            revision=snap["revision"], digest=snap["digest"],
            direction=state["direction"]["digest"], approval=approval))
        # Status publication is a subsequent, auditable docs-only operation.
        # It does not rewrite the reviewed snapshot or trigger a build.
    elif action == "materialize":
        snap = state.get("accepted", {}).get("snapshot") if args.input == "specs" else state.get("direction")
        if not snap:
            raise ValueError("no approved snapshot")
        print(materialize(state, snap, args.bead))
        return
    elif action in {"generate", "refine", "start"}:
        intent = authority(args)
        if not state.get("direction"):
            raise ValueError("direction approval required")
        if action == "generate" and any(o["kind"] == "generate" for o in state["operations"].values()):
            raise ValueError("initial generation already requested; recover or refine it")
        if action != "start" and any(o["kind"] in {"generate", "refine"}
                                     and o["phase"] != "settled" for o in state["operations"].values()):
            raise ValueError("document workflow still active or launch unresolved")
        rig = args.rig if args.rig is not None else state["rig"]
        if rig and rig not in ledger.rigs:
            raise ValueError("unknown target rig")
        if action == "start":
            if state["phase"] != "accepted" or not state.get("accepted"):
                raise ValueError("spec approval required; approval itself never launches a build")
            if not rig:
                raise ValueError("select a build rig explicitly for a city initiative")
            assert_accepted_current(state)
            snap = state["accepted"]["snapshot"]
            # Repeated requests for this rig and accepted revision reuse the
            # recorded operation, including failed or interrupted launches.
            key = "build-" + rig + "-" + snap["digest"]
        else:
            key = action + "-" + uuid.uuid4().hex
        if key in state["operations"]:
            print(encoded(state["operations"][key]))
            return
        formula = {"generate": "omg-docs", "refine": "omg-refine", "start": "omg-build"}[action]
        op = dict(kind=action, phase="launching", formula=formula, rig=rig, authority=intent)
        if action == "start":
            op["approved"] = dict(revision=snap["revision"], digest=snap["digest"],
                                  direction=state["accepted"]["direction"]["digest"])
        state["operations"][key] = op
        if action != "start":
            state.update(phase="draft", reviews={})
        old = ledger.save(args.bead, old, state)  # durable intent BEFORE dispatch
        vars_ = dict(initiative=args.bead, operation=key, omg_binding=args.binding)
        if action == "start":
            inputs = materialize(state, snap, args.bead)
            vars_.update(approved_root=inputs, approved_revision=snap["revision"],
                         artifact_root=f".omg/builds/{args.bead}/{snap['digest']}",
                         requirements_path=f".omg/builds/{args.bead}/{snap['digest']}/requirements.md",
                         push=args.push, open_pr=args.open_pr)
            # Native drain continuations need a source bead. Its creation is
            # covered by the already persisted launch intent.
            source = one(gc("bd", "--rig", rig, "create", f"Build {state['slug']}",
                            "--description", f"Explicit launch for {args.bead}, revision {snap['revision']}."))
            op["source"] = source["id"]
            old = ledger.save(args.bead, old, state)
            command = ["sling", "--rig", rig, "gc.run-operator", source["id"], "--on", formula]
        else:
            target = f"{args.binding}.product-manager"
            if rig:
                target = rig + "/" + target
            command = ["sling", target, formula, "--formula"]
        for key_, value in vars_.items():
            command.extend(["--var", f"{key_}={value}"])
        result = gc(*command)
        op.update(phase="launched", receipt=result)
        # Formula workers can already have updated state. Merge only this
        # operation against a fresh CAS; never overwrite their progress.
        state, old = ledger.load(args.bead)
        existing = state["operations"][key]
        if existing["phase"] == "settled":
            existing["receipt"] = result
        else:
            state["operations"][key] = op
    elif action == "recover":
        authority(args)
        op = state["operations"].get(args.operation)
        if not op or not args.workflow:
            raise ValueError("--operation and an existing --workflow are required")
        root = one(gc("bd", "show", args.workflow))
        meta = root.get("metadata", {})
        if (meta.get("gc.kind") != "workflow" or meta.get("gc.formula_name") != op["formula"]
                or meta.get("gc.var.initiative") != args.bead
                or meta.get("gc.var.operation") != args.operation
                or (op["rig"] and meta.get("gc.root_store_ref") != "rig:" + op["rig"])):
            raise ValueError("workflow does not match the saved launch intent")
        op.update(phase="launched", receipt=dict(workflow_id=root["id"]), recovered=authority(args))
    elif action == "settle":
        op = state["operations"].get(args.operation)
        if not op or not args.workflow:
            raise ValueError("--operation and --workflow required")
        root = one(gc("bd", "show", args.workflow))
        meta = root.get("metadata", {})
        if (root.get("status") != "closed" or meta.get("gc.var.initiative") != args.bead
                or meta.get("gc.var.operation") != args.operation):
            raise ValueError("workflow has not settled or belongs to another operation")
        op.update(phase="settled", workflow=root["id"], outcome=meta.get("gc.outcome", "unknown"))
    ledger.save(args.bead, old, state)
    print(encoded(state))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print(f"omg initiative: {error}", file=sys.stderr)
        sys.exit(1)
