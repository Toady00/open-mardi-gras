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
import shutil
import subprocess
import sys
import tempfile
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


def snapshot_files(repo, directory, revision, kind, paths=None):
    """Read the exact Git blobs; safe for controller checks without a YAML tool."""
    safe_relative(directory)
    if not re.fullmatch(r"[0-9a-f]{40,64}", revision):
        raise ValueError("revision must be an exact Git commit SHA")
    if git(repo, "rev-parse", f"{revision}^{{commit}}").decode().strip() != revision:
        raise ValueError("revision is not a commit")
    rows = git(repo, "ls-tree", "-r", "-z", revision, "--", directory).split(b"\0")
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
        yield path, git(repo, "show", f"{revision}:{path}")


def snapshot(repo, directory, revision, kind, paths=None):
    files = {}
    specs = {}
    ids = set()
    types = set()
    requested = set(paths or [])
    for path, content in snapshot_files(repo, directory, revision, kind, paths):
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
            if fm["type"] == "spec":
                specs[path] = content
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
    if kind != "direction":
        # Parse the exact Git blobs being approved, never mutable working files.
        with tempfile.TemporaryDirectory(prefix="omg-contract-") as tmp:
            for path, content in specs.items():
                target = Path(tmp, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            result["delivery_contract"] = json.loads(run(
                "bash", str(Path(__file__).with_name("delivery-contract.sh")), tmp, *specs))
    result["digest"] = hashlib.sha256(encoded(files).encode()).hexdigest()
    return result


def assert_current(state, snap):
    """Conservatively invalidate readiness on any tracked or untracked doc edit."""
    dirty = git(state["repo"], "status", "--porcelain", "--untracked-files=all", "--", state["directory"])
    if dirty.strip():
        raise ValueError("initiative has uncommitted edits; commit and refine the changed set")
    head = git(state["repo"], "rev-parse", "HEAD").decode().strip()
    current = {path: hashlib.sha256(content).hexdigest()
               for path, content in snapshot_files(state["repo"], state["directory"], head, "docs")}
    expected = {path: item["sha256"] for path, item in snap["files"].items()}
    if current != expected:
        raise ValueError("document revision changed; shared refinement is required")


def assert_accepted_current(state):
    """Allow Hindsight approval metadata publication, not hidden content edits."""
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
        # Hindsight's source field records approval provenance. The human
        # approval already recorded by accept permits this exact transition.
        approval = state["accepted"].get("approval", {})
        if (old_fm.get("source") == "agent" and new_fm.get("source") == "human"
                and new_fm.get("status") == "accepted" and approval.get("evidence")):
            old_fm["source"] = "human"
        for fm in (old_fm, new_fm):
            fm.pop("status", None)
            fm.pop("updated_at", None)
        old_body = before.split(b"\n---\n", 1)[1]
        new_body = after.split(b"\n---\n", 1)[1]
        if old_fm != new_fm or old_body != new_body:
            raise ValueError(f"{path} changed substantively after approval; refine again")


class Ledger:
    def __init__(self, city_path=None):
        info = gc("rig", "list", *(["--city", city_path] if city_path else []))
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

    def launch_evidence(self, bead, operation, op):
        # gc beads list can silently skip stores that fail to open. Absence
        # requires an exact-store, uncached read, not that federated inventory.
        listing = ["list", "--all", "--limit", "0", "--long",
                   "--include-infra", "--include-gates", "--include-templates"]
        if op["rig"]:
            rows = gc("bd", "--city", self.city, "--rig", op["rig"],
                      *listing)
        else:
            config = run(os.environ.get("GC_BIN", "gc"), "config", "show", "--city", self.city)
            graph = json.loads(run("yq", "-p=toml", "-o=json", ".storage.classes.graph", data=config))
            if graph not in {None, "", "work"}:
                raise ValueError("city graph store is relocated; cannot prove launch absence with an exact-store list; "
                                 "recover the existing workflow or inspect native storage before repair")
            rows = self.bd(*listing)
        if not isinstance(rows, list):
            raise ValueError("expected complete uncached bead inventory")
        matches = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                raise ValueError("invalid bead inventory entry")
            meta = row.get("metadata") or {}
            if not isinstance(meta, dict):
                raise ValueError("invalid bead metadata in launch inventory")
            if (meta.get("gc.var.operation") == operation
                    or (op.get("source") and meta.get("gc.source_bead_id") == op["source"])
                    or (row["id"] == op.get("source") and meta.get("workflow_id"))):
                matches.append(row["id"])
        return matches


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
    if not snap.get("delivery_contract"):
        raise ValueError("reviewed snapshot predates the delivery contract; refine and snapshot the classified specs")
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


def conversation(args, state):
    # Worker sessions must not become the human-facing return address.
    return (args.notify or
            (os.environ.get("GC_SESSION_ID") if os.environ.get("GC_SESSION_ORIGIN") in {"manual", "named"} else None)
            or state.get("conversation"))


def active_operation(state, requested=None):
    if requested:
        op = state["operations"].get(requested)
        if not op or op["phase"] not in {"launching", "launched"}:
            raise ValueError("operation is not active; do not change state from an old assignment")
        return requested
    active = [key for key, op in state["operations"].items()
              if op["phase"] in {"launching", "launched"}]
    if len(active) > 1:
        raise ValueError("--operation required when multiple operations are active")
    return active[0] if active else None


def notice(state, key, subject, body, operation=None):
    target = state["operations"].get(operation, {}).get("conversation") or state.get("conversation")
    state.setdefault("notifications", {}).setdefault(key, dict(
        target=target, subject=subject, body=body, operation=operation, at=now()))


def request_decision(state, args):
    if not args.note or not args.note.strip():
        raise ValueError("--note must state the question, options/recommendation, and why human input is needed")
    operation = active_operation(state, args.operation)
    pending = state.get("pending_decision")
    if not pending:
        pending = dict(id="decision-" + uuid.uuid4().hex, note=args.note,
                       operation=operation, at=now())
        state["pending_decision"] = pending
    state.update(phase="needs-human", decision=pending["note"])
    if operation:
        state["operations"][operation]["interruption"] = dict(pending)
    notice(state, pending["id"], f"{state['slug']}: decision needed",
           f"Initiative {args.bead}, decision {pending['id']}.\n{pending['note']}\n"
           "Present this question and recommendation to the human now. Read the current initiative "
           "record first; if already resolved, do not ask it again. Record the answer with initiative "
           "resolve, then explicitly resume document work after the old operation settles. "
           "Do not approve specs or launch a build.", operation)


def deliver_notices(ledger, bead):
    """Durable, retryable mail + attention request. Never overwrite workflow progress.

    Receipts suppress ordinary duplicate sends. A crash between an external send
    and its receipt can repeat a notice; event IDs in subjects identify that case.
    """
    state, _ = ledger.load(bead)
    for key in list(state.get("notifications", {})):
        for channel in ("mail", "nudge"):
            current, _ = ledger.load(bead)
            item = current["notifications"][key]
            if item.get(channel):
                continue
            target = item.get("target")
            error = None
            receipt = None
            try:
                if not target:
                    raise ValueError("no conversation recorded; use initiative watch --notify <session-id>")
                if channel == "mail":
                    receipt = gc("mail", "send", target, "--city", ledger.city,
                                 "-s", f"{item['subject']} [{key}]", "-m", item["body"])
                else:
                    receipt = gc("session", "nudge", target, item["body"],
                                 "--delivery", "wait-idle", "--city", ledger.city)
                if receipt.get("ok") is False:
                    raise ValueError(encoded(receipt))
            except (ValueError, OSError) as exc:
                error = str(exc)
            # Retry only the metadata merge after CAS contention, not the send.
            for attempt in range(3):
                current, previous = ledger.load(bead)
                entry = current["notifications"][key]
                if error:
                    entry["error"] = error
                else:
                    entry[channel] = dict(receipt=receipt, at=now())
                    entry.pop("error", None)
                try:
                    ledger.save(bead, previous, current)
                    break
                except ValueError:
                    if attempt == 2:
                        raise
            if error:
                print(f"omg initiative: notification {key} pending: {error}", file=sys.stderr)
                break
    return ledger.load(bead)[0]


def missing_authoring(state):
    kinds = set()
    directory = Path(state["repo"], state["directory"])
    for file in directory.rglob("*.md"):
        if {"reports", "visuals"} & set(file.relative_to(directory).parts[:-1]):
            continue
        kinds.add(frontmatter(file.read_bytes()).get("type"))
    return not {"discussion", "prd", "hld", "spec"} <= kinds


def operation_bead(ledger, op, *args):
    return gc("bd", "--city", ledger.city, *(["--rig", op["rig"]] if op["rig"] else []), *args)


def operation_workflow(ledger, bead, operation, op, workflow_id):
    """Read a native root and require it to be this operation's own workflow.

    Shared by recover, settle and retry: every consumer must reject a bead that
    merely carries this initiative/operation (an omg-work item root inside the
    build does), a root of another formula, another store, or a root other than
    the one already recorded for the operation.
    """
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ValueError("--workflow required")
    root = one(operation_bead(ledger, op, "show", workflow_id))
    meta = root.get("metadata", {})
    recorded = op.get("workflow") or (op.get("receipt") or {}).get("workflow_id")
    if (meta.get("gc.kind") != "workflow" or meta.get("gc.formula_name") != op.get("formula")
            or meta.get("gc.var.initiative") != bead
            or meta.get("gc.var.operation") != operation
            or (op.get("rig") and meta.get("gc.root_store_ref") != "rig:" + op["rig"])
            or (recorded and recorded != root["id"])):
        raise ValueError("workflow does not match the recorded operation")
    return root, meta


def latest_attempt(attempts):
    """Follow retry_of links from the live root; key order is not chronological.

    Operations are stored with sorted keys and retry keys carry random UUIDs,
    so neither insertion nor key order identifies the newest attempt. Returns
    None when no live attempt exists; a fork is reported, never guessed.
    """
    live = {key: op for key, op in attempts.items() if op["phase"] != "abandoned"}
    heads = [key for key, op in live.items() if op.get("retry_of") not in live]
    if not live:
        return None
    if len(heads) != 1:
        raise ValueError("ambiguous build attempt history for this approval; inspect the initiative record")
    current = heads[0]
    for _ in range(len(live)):
        successors = [key for key, op in live.items() if op.get("retry_of") == current]
        if not successors:
            return current
        if len(successors) > 1:
            raise ValueError("ambiguous build attempt history for this approval; inspect the initiative record")
        current = successors[0]
    raise ValueError("ambiguous build attempt history for this approval; inspect the initiative record")


def persist_baseline(artifact_root, baseline):
    """Create the immutable operation baseline exactly once.

    Called only after the launch intent won the metadata CAS, so a losing
    concurrent caller never writes here. An identical existing file is the
    same intent replayed; a different one is never overwritten.
    """
    artifact_root.mkdir(parents=True, exist_ok=True)
    target = artifact_root / "baseline.json"
    content = encoded(baseline)
    fd, temporary = tempfile.mkstemp(dir=artifact_root, prefix=".baseline-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.read_text() != content:
                raise ValueError("artifact root already holds a different baseline; "
                                 "inspect it before launching this operation")
    finally:
        os.unlink(temporary)


def finish_step(ledger, state, args):
    if not args.operation or not args.step:
        raise ValueError("complete-step requires --operation and --step")
    op = state["operations"].get(args.operation)
    if not op or op["phase"] not in {"launching", "launched"} or op["kind"] not in {"generate", "refine"}:
        raise ValueError("complete-step requires an active document operation")
    step = one(operation_bead(ledger, op, "show", args.step))
    meta = step.get("metadata", {})
    root = one(operation_bead(ledger, op, "show", meta.get("gc.root_bead_id", "")))
    root_meta = root.get("metadata", {})
    if (root_meta.get("gc.var.initiative") != args.bead
            or root_meta.get("gc.var.operation") != args.operation
            or meta.get("gc.kind") not in {None, "", "task"}
            or meta.get("gc.scope_role") not in {"setup", "member"}):
        raise ValueError("step is not ordinary scoped work for this document operation")
    if step["status"] == "closed":
        return  # Retrying after a lost close response is harmless.
    if step["status"] != "in_progress":
        raise ValueError("claim the step before completing it")
    pending = op.get("interruption") or state.get("pending_decision")
    human = bool(pending or state.get("phase") == "needs-human")
    if human and meta.get("gc.ralph_step_id"):
        # The current engine retries a failed scope even when failure_class is
        # hard. End this operation's authored retry budget before closing the
        # subject; native scope/control dispatch still owns all graph closure.
        attempt = int(meta.get("gc.attempt", "0"))
        members = operation_bead(ledger, op, "query",
                                 "metadata.gc.root_bead_id=" + root["id"], "--limit", "0")
        controls = [row for row in members if row.get("metadata", {}).get("gc.kind") == "ralph"
                    and row["metadata"].get("gc.step_id") == meta["gc.ralph_step_id"]]
        if len(controls) != 1 or attempt < 1:
            raise ValueError("cannot identify the enclosing document check and attempt")
        control = controls[0]
        if control.get("status") == "closed":
            raise ValueError("enclosing document check is already closed")
        budget = min(attempt, int(control["metadata"]["gc.max_attempts"]))
        if budget < 1:
            raise ValueError("invalid enclosing document check budget")
        operation_bead(ledger, op, "update", control["id"],
                       "--set-metadata", f"gc.max_attempts={budget}")
    outcome = "fail" if human else args.outcome
    fields = {"gc.outcome": outcome, "omg.outcome": "needs-human" if human else outcome}
    if outcome == "fail":
        fields.update({"gc.failure_class": "hard", "gc.failure_reason":
                       "needs-human" if human else (args.note or "document step failed")})
    if pending:
        fields["omg.decision"] = pending["id"]
    flags = [value for key, val in fields.items() for value in ("--set-metadata", f"{key}={val}")]
    operation_bead(ledger, op, "update", args.step, *flags)
    operation_bead(ledger, op, "close", args.step, "--reason", fields["omg.outcome"])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["init", "list", "show", "direction", "snapshot",
                                     "review", "ready", "decision", "revise", "accept",
                                     "materialize", "generate", "refine", "start",
                                     "recover", "abandon", "settle", "check", "resolve",
                                     "watch", "notify", "complete-step"])
    p.add_argument("bead", nargs="?")
    p.add_argument("--slug")
    p.add_argument("--title")
    p.add_argument("--rig", default=None)
    p.add_argument("--city", default=None, help="explicit city context, also accepted when forwarded by gc")
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
    p.add_argument("--decision", dest="decision_id")
    p.add_argument("--notify", help="originating conversation session ID or alias")
    p.add_argument("--step", help="claimed document work bead, never a control bead")
    p.add_argument("--outcome", choices=["pass", "fail"], default="pass")
    p.add_argument("--launcher-stopped", action="store_true",
                   help="confirm the original launcher and its child processes have exited")
    p.add_argument("--binding", default="omg")
    p.add_argument("--push", choices=["true", "false"],
                   help="new start: default false; retry: must equal the prior authorization")
    p.add_argument("--open-pr", choices=["true", "false"],
                   help="new start: default false; retry: must equal the prior authorization")
    p.add_argument("--retry", help="explicitly retry this settled failed build operation")
    args = p.parse_args(argv)
    ledger = Ledger(args.city)
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
        state["conversation"] = conversation(args, state)
        result = one(ledger.bd("create", args.title or args.slug, "--id", bead,
                              "--status", "pinned", "--labels", "omg:initiative",
                              "--description", "Conversational initiative record; not dispatchable work.",
                              "--metadata", encoded({KEY: encoded(state)})))
        print(encoded(result))
        return
    if args.action == "list":
        rows = ledger.bd("list", "--all", "--limit", "0", "--long", "--label", "omg:initiative")
        result = []
        for row in rows:
            state = json.loads(row["metadata"][KEY])
            result.append(dict(bead=row["id"], title=row["title"], phase=state["phase"],
                               repo=state["repo"], directory=state["directory"],
                                reviewed=state.get("reviewed", {}).get("revision"),
                                decision=(state.get("pending_decision") or state.get("decision")) if state["phase"] == "needs-human" else None,
                                operations={key: {field: op.get(field) for field in ("phase", "result", "outcome", "workflow")}
                                            for key, op in state["operations"].items()},
                                notifications=state.get("notifications", {})))
        print(encoded(result))
        return
    if not args.bead:
        raise ValueError("initiative bead ID required")
    state, old = ledger.load(args.bead)
    action = args.action
    if args.retry and action != "start":
        raise ValueError("--retry is only valid with start")
    if action == "show":
        print(encoded(state))
        return
    if action == "notify":
        print(encoded(deliver_notices(ledger, args.bead)))
        return
    if action == "complete-step":
        finish_step(ledger, state, args)
        print(encoded(dict(step=args.step, completed=True)))
        return
    if args.operation and action in {"revise", "snapshot", "review", "ready"}:
        active_operation(state, args.operation)
    if state.get("phase") == "needs-human" and action in {"direction", "revise", "snapshot", "generate", "refine", "start"}:
        raise ValueError("resolve the recorded human decision before revising, approving direction or launching work")
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
        state.update(reviewed=snap, reviewed_operation=active_operation(state, args.operation),
                     reviews={}, phase="refining")
    elif action == "review":
        if not args.role or not args.verdict or not args.artifact:
            raise ValueError("--role, --verdict, and persisted --artifact are required")
        snap = state.get("reviewed")
        if not snap and args.verdict != "human":
            raise ValueError("snapshot the whole document set first")
        if snap:
            if args.verdict == "human":
                try:
                    assert_current(state, snap)
                except ValueError:
                    snap = None  # A human interruption does not certify stale document bytes.
            else:
                assert_current(state, snap)
        artifact = Path(args.artifact).resolve(strict=True)
        # Review evidence is deliberately not an eligible authored document.
        if Path(state["repo"], "docs") in artifact.parents:
            raise ValueError("put review evidence outside docs/, under .omg/")
        state["reviews"][args.role] = dict(
            verdict=args.verdict, artifact=str(artifact),
            artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            digest=snap["digest"] if snap else None, direction=state["direction"]["digest"], at=now())
        if args.verdict == "human":
            request_decision(state, args)
    elif action in {"ready", "check"}:
        if state.get("phase") == "needs-human":
            if action == "check":
                raise ValueError("needs-human: " + state.get("decision", "decision required"))
            raise ValueError("unresolved human decision; cannot mark approval-ready")
        validate_reviews(state)
        if action == "check":
            print(encoded(dict(outcome="pass")))
            return
        state["phase"] = "approval-ready"
    elif action == "decision":
        request_decision(state, args)
    elif action == "resolve":
        evidence = authority(args)
        if state.get("phase") != "needs-human" or not args.note or not args.note.strip():
            raise ValueError("resolve requires an outstanding decision and --note with the human's answer")
        pending = state.get("pending_decision") or dict(id="legacy", note=state.get("decision"), at=None)
        if args.decision_id != pending["id"]:
            raise ValueError(f"resolve the current --decision {pending['id']}; do not resolve a stale question")
        state.setdefault("decisions", []).append(dict(pending, resolution=args.note, authority=evidence, resolved_at=now()))
        state.pop("pending_decision", None)
        state.pop("decision", None)
        state.update(phase="draft", reviews={})
    elif action == "watch":
        target = conversation(args, state)
        if not target:
            raise ValueError("watch requires --notify or a managed manual session")
        state["conversation"] = target
        for op in state["operations"].values():
            if op["phase"] in {"launching", "launched"}:
                op["conversation"] = target
        for item in state.get("notifications", {}).values():
            if not item.get("nudge"):
                item["target"] = target
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
        if action == "generate" and any(o["kind"] == "generate" and o["phase"] != "abandoned"
                                        for o in state["operations"].values()):
            raise ValueError("initial generation already requested; recover or refine it")
        if action != "start" and any(o["kind"] in {"generate", "refine"}
                                     and o["phase"] not in {"settled", "abandoned"}
                                     for o in state["operations"].values()):
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
            # A new start authorizes only what was said: absent flags mean no
            # code publication. A retry keeps the prior attempt's authorization;
            # a different one is a separate request, never granted by a retry.
            publication = dict(push=args.push == "true", open_pr=args.open_pr == "true")
            if args.retry:
                prior = state["operations"].get(args.retry)
                if (not prior or prior.get("kind") != "start" or prior.get("phase") != "settled"
                        or prior.get("rig") != rig or prior.get("approved", {}).get("digest") != snap["digest"]):
                    raise ValueError("--retry requires a settled build for this rig and approved snapshot; changed approval uses a fresh start")
                publication = dict(prior.get("publication") or {})
                if set(publication) != {"push", "open_pr"} or not all(isinstance(v, bool) for v in publication.values()):
                    raise ValueError("the settled build has no recorded publication authorization to retry")
                for flag, value in (("push", args.push), ("open_pr", args.open_pr)):
                    if value is not None and (value == "true") != publication[flag]:
                        raise ValueError(f"retry keeps the prior publication authorization ({flag}={str(publication[flag]).lower()}); "
                                         "a different publication is a separate request, not a retry")
                root, meta = operation_workflow(ledger, args.bead, args.retry, prior,
                                                prior.get("workflow") or (prior.get("receipt") or {}).get("workflow_id"))
                if root.get("status") != "closed" or meta.get("gc.outcome") != "fail":
                    raise ValueError("retry requires the matching terminal failed native workflow")
            attempts = {k: o for k, o in state["operations"].items()
                        if k == key or k.startswith(key + "-retry-")}
            latest = latest_attempt(attempts)
            if args.retry:
                existing = [k for k, o in attempts.items()
                            if o.get("retry_of") == args.retry and o["phase"] != "abandoned"]
                if len(existing) > 1:
                    raise ValueError("ambiguous build attempt history for this approval; inspect the initiative record")
                if existing:
                    print(encoded(state["operations"][existing[0]]))
                    return
                if latest and state["operations"][latest]["phase"] != "settled":
                    raise ValueError("another build attempt for this approval is still active or launch-unresolved")
            elif latest:
                print(encoded(state["operations"][latest]))
                return
            if attempts:
                key += "-retry-" + uuid.uuid4().hex
        else:
            key = action + "-" + uuid.uuid4().hex
        if key in state["operations"]:
            print(encoded(state["operations"][key]))
            return
        if action == "start":
            for tool in ("bash", "jq", "yq", "git", "shasum"):
                if not shutil.which(tool):
                    raise ValueError(f"build verification requires {tool} on PATH")
            inputs = materialize(state, snap, args.bead)
            artifact_root = Path(ledger.rigs[rig]).resolve() / ".omg" / "builds" / args.bead / key
            baseline = dict(initiative=args.bead, operation=key, revision=snap["revision"],
                            digest=snap["digest"], approved_root=inputs, files=snap["files"],
                            binding=args.binding, city=ledger.city,
                            repo=str(Path(ledger.rigs[rig]).resolve()),
                            publication=publication)
        formula = {"generate": "omg-docs", "refine": "omg-refine", "start": "omg-build"}[action]
        target_conversation = conversation(args, state)
        if target_conversation:
            state["conversation"] = target_conversation
        op = dict(kind=action, phase="launching", formula=formula, rig=rig, authority=intent,
                  conversation=target_conversation)
        if action != "start":
            op["initial"] = action == "generate" or missing_authoring(state)
        if action == "start":
            if args.retry:
                op["retry_of"] = args.retry
            op["publication"] = baseline["publication"]
            op["approved"] = dict(revision=snap["revision"], digest=snap["digest"],
                                  direction=state["accepted"]["direction"]["digest"])
            op["artifact_root"] = str(artifact_root)
            op["repo"] = baseline["repo"]
            op["approved_root"] = inputs
        state["operations"][key] = op
        if action != "start":
            state.update(phase="draft", reviews={})
        old = ledger.save(args.bead, old, state)  # durable intent BEFORE dispatch
        if action == "start":
            # Only the CAS winner reaches this point; a failure here leaves the
            # recorded launching operation for recovery or abandonment.
            persist_baseline(artifact_root, baseline)
        vars_ = dict(initiative=args.bead, operation=key, omg_binding=args.binding)
        if action != "start":
            vars_["initial"] = "true" if op["initial"] else "false"
        if action == "start":
            vars_.update(approved_root=inputs, approved_revision=snap["revision"],
                         artifact_root=str(artifact_root),
                         push=str(publication["push"]).lower(), open_pr=str(publication["open_pr"]).lower())
            # Native drain continuations need a source bead. Its creation is
            # covered by the already persisted launch intent.
            source = one(gc("bd", "--rig", rig, "create", f"Build {state['slug']}",
                            "--description", f"Explicit launch for {args.bead}, revision {snap['revision']}."))
            op["source"] = source["id"]
            old = ledger.save(args.bead, old, state)
            command = ["sling", "--rig", rig, f"{args.binding}.architect", source["id"], "--on", formula]
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
            existing.update(phase="launched", receipt=result)  # preserve early decisions/notifications
    elif action == "abandon":
        evidence = authority(args)
        op = state["operations"].get(args.operation)
        if not op or op["phase"] != "launching":
            raise ValueError("only an unresolved launching operation can be abandoned")
        if not args.launcher_stopped or not args.note or not args.note.strip():
            raise ValueError("confirm --launcher-stopped and explain the failed launch with --note")
        matches = ledger.launch_evidence(args.bead, args.operation, op)
        if matches:
            raise ValueError("launch has workflow evidence; recover or inspect: " + ", ".join(matches))
        op.update(phase="abandoned", abandonment=dict(authority=evidence, reason=args.note,
                                                      launcher_stopped=True, checked_at=now()))
        # Save with the original CAS version. A concurrent recovery or receipt
        # must win rather than being overwritten by an absence-based decision.
    elif action == "recover":
        authority(args)
        op = state["operations"].get(args.operation)
        if not op or not args.workflow:
            raise ValueError("--operation and an existing --workflow are required")
        if op["phase"] == "abandoned":
            raise ValueError("abandoned operation has unexpected workflow evidence; inspect before recovery")
        root, meta = operation_workflow(ledger, args.bead, args.operation, op, args.workflow)
        op.update(phase="launched", receipt=dict(workflow_id=root["id"]), recovered=authority(args))
    elif action == "settle":
        op = state["operations"].get(args.operation)
        if not op or not args.workflow:
            raise ValueError("--operation and --workflow required")
        if op["phase"] == "abandoned":
            raise ValueError("an abandoned operation has no workflow to settle; recover it first if evidence exists")
        root, meta = operation_workflow(ledger, args.bead, args.operation, op, args.workflow)
        if root.get("status") != "closed":
            raise ValueError("workflow has not settled")
        engine_outcome = meta.get("gc.outcome", "unknown")
        if "result" not in op:
            if op.get("interruption") or state.get("phase") == "needs-human":
                result = "needs-human"
            elif op["kind"] in {"generate", "refine"}:
                try:
                    if state.get("reviewed_operation") != args.operation:
                        raise ValueError("snapshot belongs to another operation")
                    validate_reviews(state)
                    result = "approval-ready" if engine_outcome == "pass" else "failed"
                except (ValueError, OSError, KeyError):
                    result = "incomplete" if engine_outcome == "pass" else "failed"
            else:
                result = "development-verified" if engine_outcome == "pass" else "failed"
            op["result"] = result
        op.update(phase="settled", workflow=root["id"], outcome=engine_outcome)
        note = (op.get("interruption") or {}).get("note") or state.get("decision", "")
        notice(state, "settled-" + args.operation, f"{state['slug']}: {op['result']}",
               f"Initiative {args.bead}, operation {args.operation}, workflow {root['id']}: {op['result']}.\n"
               f"Engine outcome: {engine_outcome}; this alone is not document approval.\n{note}\n"
               "Read the current initiative state and present the result and next action to the human. "
               "If a newer operation or resolution supersedes this notice, summarize that instead. "
               "Do not infer spec approval or build authorization.", args.operation)
    ledger.save(args.bead, old, state)
    if action in {"decision", "review", "settle", "watch"}:
        state = deliver_notices(ledger, args.bead)
    print(encoded(state))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print(f"omg initiative: {error}", file=sys.stderr)
        sys.exit(1)
