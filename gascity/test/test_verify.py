"""Run the shipped Bash checker with real Git/yq/jq and isolated bead transport."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PACK = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_execution", PACK / "assets/scripts/verify_execution.py")
EXECUTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXECUTION)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "rig with spaces"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "app.txt").write_text("implemented R1\n")
        self.commit()
        self.root = self.repo / ".omg" / "build"
        self.root.mkdir(parents=True)
        self.approved = self.base / "approved"
        self.approved.mkdir()
        self.spec = self.approved / "spec.md"
        self.spec.write_text("---\nschema_version: 2\ntype: spec\n---\nR1: Required behavior.\n"
                             "```omg-delivery\nversion: 1\nrequirements:\n  R1:\n    kind: implementation\n```\n")
        self.files = {"spec.md": {"sha256": self.hash(self.spec), "type": "spec", "id": "spec.example", "status": "draft"}}
        self.baseline = dict(initiative="city-1", operation="build-1", revision="a" * 40,
                             digest=hashlib.sha256(encoded(self.files).encode()).hexdigest(),
                             approved_root=str(self.approved), files=self.files,
                             repo=str(self.repo), city=str(self.base), binding="omg",
                             publication={"push": False, "open_pr": False})
        self.write("baseline", self.baseline)
        (self.root / "plan.md").write_text("Implement R1 and test its observable behavior.\n")
        self.write("plan", {"requirements": [{"id": "R1", "kind": "implementation", "source": "spec.md", "quote": "R1: Required behavior."}]})
        self.refresh_plan_review()
        self.write("decomposition", {"workflow": "workflow-1", "convoy": "convoy-1", "items": [{"id": "app-1", "requirements": ["R1"]}], "downstream": []})
        self.write("work/app-1", {"operation": "build-1", "work": "app-1", "revision": self.head, "checks": self.checks()})
        self.write("tests", {"operation": "build-1", "revision": self.head, "checks": self.checks()})
        self.write("review", {"revision": self.head, "tests_sha256": self.hash(self.root / "tests.json"), "verdict": "pass", "findings": []})
        self.write("reconciliation", {"revision": self.head, "review_sha256": self.hash(self.root / "review.json"), "requirements": [{"id": "R1", "status": "implemented", "evidence": "app.txt and test log"}]})
        self.state = {"operations": {"build-1": {"kind": "start", "phase": "launched", "artifact_root": str(self.root), "approved": {"digest": self.baseline["digest"], "revision": "a" * 40}}}}
        self.state["operations"]["build-1"].update(repo=str(self.repo), approved_root=str(self.approved), publication=self.baseline["publication"])
        self.beads = {
            "city-1": {"id": "city-1", "metadata": {"omg.state": encoded(self.state)}},
            "workflow-1": {"id": "workflow-1", "metadata": {"gc.kind": "workflow", "gc.formula_name": "omg-build", "gc.var.operation": "build-1", "gc.var.initiative": "city-1", "gc.input_convoy_id": "convoy-1"}},
            "app-1": {"id": "app-1", "status": "open", "metadata": {"omg.operation": "build-1", "omg.artifact_root": str(self.root)}},
            "check": {"id": "check", "metadata": {"omg.stage": "quality", "omg.artifact_root": str(self.root), "omg.operation": "build-1", "omg.initiative": "city-1"}},
            "work-check": {"id": "work-check", "metadata": {"omg.stage": "work", "omg.convoy": "unit-1"}},
        }
        self.manifest = {"version": 1, "context": "shared", "parent_convoy_id": "convoy-1",
                         "formula": "omg-work", "rows": [{"index": 0, "member_id": "app-1",
                         "unit_key": "drain-unit:drain-1:0:app-1", "unit_convoy_id": "unit-1",
                         "item_root_key": "drain-item-root:drain-1:0:app-1", "item_root_id": "item-1",
                         "status": "succeeded", "outcome_kind": "pass", "outcome_bead_id": "item-1"}]}
        self.beads["drain-1"] = {"id": "drain-1", "status": "closed", "metadata": {
            "gc.root_bead_id": "workflow-1", "gc.kind": "drain", "gc.step_id": "omg-build.implement",
            "gc.step_ref": "omg-build.implement",
            "gc.drain_parent_convoy_id": "convoy-1", "gc.drain_formula": "omg-work",
            "gc.drain_context": "shared", "gc.drain_state": "succeeded", "gc.outcome": "pass",
            "gc.drain_manifest.v1": encoded(self.manifest)}}
        self.beads["item-1"] = {"id": "item-1", "status": "closed", "metadata": {
            "gc.kind": "workflow", "gc.formula_name": "omg-work", "gc.outcome": "pass",
            "gc.var.operation": "build-1", "gc.var.initiative": "city-1",
            "gc.drain_control_id": "drain-1", "gc.drain_member_id": "app-1",
            "gc.input_convoy_id": "unit-1", "gc.drain_index": "0", "gc.drain_count": "1",
            "gc.item_root_key": self.manifest["rows"][0]["item_root_key"]}}
        # Minimal projections of the native ing-autp / ing-ofr9 records.
        for identifier in ["workflow-1", "item-1"]:
            self.beads[identifier]["metadata"]["gc.formula_contract"] = "graph.v2"
        self.beads["finalizer-1"] = self.finalizer("finalizer-1", "item-1")
        self.beads["executable-1"] = {"id": "executable-1", "status": "closed", "metadata": {
            "gc.root_bead_id": "item-1", "gc.step_id": "work", "gc.step_ref": "work.iteration.1",
            "gc.outcome": "pass"}}
        self.transport = self.base / "transport.json"
        self.stub = self.base / "gc"
        self.stub.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
with open(os.environ["TEST_TRANSPORT"]) as f:
    state = json.load(f)
args = sys.argv[1:]
if args[0] == "bd" and "show" in args:
    print(json.dumps(state.get(args[args.index("show") + 1], [])))
elif args[:2] == ["convoy", "status"]:
    if args[2] not in ["convoy-1", "unit-1"]:
        sys.exit("unknown convoy")
    print(json.dumps({"convoy": {"id": args[2]}, "children": [{"id": "app-1", "status": state["app-1"]["status"]}]}))
elif args[:2] == ["bd", "list"]:
    print(json.dumps(list(state.values())))
else:
    sys.exit("unexpected gc command: " + repr(args))
''')
        self.stub.chmod(0o755)
        self.env = {**os.environ, "GC_BIN": str(self.stub), "TEST_TRANSPORT": str(self.transport)}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def tool_path(self, *omit):
        """A PATH holding exactly the resolved tools the checker declares, plus POSIX utilities."""
        tools = self.base / "tools"
        tools.mkdir(exist_ok=True)
        for name in ("bash", "jq", "yq", "git", "shasum", "python3"):
            link = tools / name
            if link.exists() or link.is_symlink():
                link.unlink()
            if name not in omit:
                resolved = sys.executable if name == "python3" else shutil.which(name)
                self.assertIsNotNone(resolved, f"test needs {name} on PATH")
                link.symlink_to(resolved)
        return os.pathsep.join([str(tools), "/usr/bin", "/bin"])

    def finalizer(self, identifier, root):
        return {"id": identifier, "status": "closed", "metadata": {
            "gc.root_bead_id": root, "gc.kind": "workflow-finalize", "gc.outcome": "pass",
            "gc.step_id": "omg-work.workflow-finalize", "gc.step_ref": "omg-work.workflow-finalize"}}

    def commit(self):
        self.git("add", "app.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "commit", "-qm", "test")
        self.head = self.git("rev-parse", "HEAD")

    def hash(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def write(self, name, value):
        file = self.root / (name + ".json")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(encoded(value))

    def refresh_plan_review(self):
        self.write("plan-review", {"verdict": "pass", "inventory_complete": True,
                                   "plan_sha256": self.hash(self.root / "plan.json"),
                                   "prose_sha256": self.hash(self.root / "plan.md")})

    def checks(self):
        log = self.root / "logs/test.txt"
        log.parent.mkdir(exist_ok=True)
        log.write_text("One meaningful test passed.\n")
        return [{"command": "test actual-behavior", "exit_code": 0, "log": "logs/test.txt", "sha256": self.hash(log)}]

    def verify(self, stage="quality", ok=True, controller=False, restricted=False):
        self.transport.write_text(encoded(self.beads))
        args = [str(PACK / "assets/scripts/verify.sh")]
        env = self.env.copy()
        if controller:
            env["GC_BEAD_ID"] = {"work": "work-check", "report": "report-check"}.get(stage, "check")
        else:
            args += ["--root", str(self.root), "--stage", stage]
            if stage == "work":
                args += ["--work", "app-1"]
        if restricted:
            # A controller sandbox: unrelated HOME and only the tools the
            # caller resolved. The script must not add Homebrew or other
            # directories of its own.
            env.update(PATH=self.tool_path(), HOME=str(self.base))
        result = subprocess.run(args, cwd=self.base, env=env, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout), {"outcome": "pass"})
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_all_stages_and_controller_environment(self):
        for stage in ["plan", "decompose", "work", "quality", "reconcile"]:
            with self.subTest(stage=stage):
                self.verify(stage)
        self.verify(controller=True, restricted=True)
        self.verify("work", controller=True, restricted=True)

    def test_caller_path_selects_the_tools(self):
        script = PACK / "assets/scripts/verify.sh"
        self.transport.write_text(encoded(self.beads))
        # Without yq on the caller's PATH the check must report it, even though
        # a Homebrew or /usr/local copy exists on this host.
        env = {**self.env, "PATH": self.tool_path("yq"), "HOME": str(self.base)}
        result = subprocess.run([str(script), "--root", str(self.root), "--stage", "plan"],
                                cwd=self.base, env=env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing yq", result.stderr)
        # A jq placed first on the caller's PATH is the one used, not a
        # system or Homebrew jq the script might prefer on its own.
        path = self.tool_path()
        marker = self.base / "tools" / "jq"
        marker.unlink()
        marker.write_text("#!/bin/sh\necho 'caller-selected jq' >&2\nexit 3\n")
        marker.chmod(0o755)
        result = subprocess.run([str(script), "--root", str(self.root), "--stage", "plan"],
                                cwd=self.base, env={**self.env, "PATH": path, "HOME": str(self.base)},
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("caller-selected jq", result.stderr)
        self.assertFalse(any(line.lstrip().startswith("export PATH") for line in script.read_text().splitlines()))

    def test_changed_approved_bytes_and_inventory_fail(self):
        self.spec.write_text(self.spec.read_text() + "R2: unapproved change\n")
        self.assertIn("approved file changed", self.verify("plan", ok=False).stderr)
        self.baseline["files"]["spec.md"]["sha256"] = self.hash(self.spec)
        self.write("baseline", self.baseline)
        self.assertIn("inventory changed", self.verify("plan", ok=False).stderr)

    def test_wrong_operation_and_missing_approval_fail(self):
        self.beads["check"]["metadata"]["omg.operation"] = "another-run"
        self.assertIn("different operation", self.verify(controller=True, ok=False).stderr)
        self.state["operations"]["build-1"]["approved"]["digest"] = "other"
        self.beads["city-1"]["metadata"]["omg.state"] = encoded(self.state)
        self.assertIn("recorded build approval", self.verify(ok=False).stderr)

    def test_plan_duplicates_missing_quotes_and_stale_review_fail(self):
        original = json.loads((self.root / "plan.json").read_text())
        for change in ["duplicate", "quote", "missing"]:
            plan = copy.deepcopy(original)
            if change == "duplicate":
                plan["requirements"] *= 2
            elif change == "quote":
                plan["requirements"][0]["quote"] = "invented requirement"
            else:
                plan["requirements"] = []
            self.write("plan", plan)
            self.refresh_plan_review()
            self.verify("plan", ok=False)
        self.write("plan", original)
        self.verify("plan", ok=False)

    def test_decomposition_missing_coverage_and_wrong_convoy_fail(self):
        self.write("decomposition", {"workflow": "workflow-1", "convoy": "convoy-1", "items": [{"id": "app-1", "requirements": []}]})
        self.verify("decompose", ok=False)
        self.write("decomposition", {"workflow": "workflow-1", "convoy": "convoy-1", "items": [{"id": "other", "requirements": ["R1"]}], "downstream": []})
        self.assertIn("membership", self.verify("decompose", ok=False).stderr)

    def test_failing_missing_and_changed_test_evidence_fail(self):
        tests = json.loads((self.root / "tests.json").read_text())
        tests["checks"][0]["exit_code"] = 1
        self.write("tests", tests)
        self.verify(ok=False)
        tests["checks"][0]["exit_code"] = 0
        self.write("tests", tests)
        (self.root / "logs/test.txt").write_text("modified")
        self.assertIn("log changed", self.verify(ok=False).stderr)
        (self.root / "logs/test.txt").unlink()
        self.verify(ok=False)

    def test_dirty_code_and_new_commit_invalidate_quality(self):
        (self.repo / "app.txt").write_text("changed R1\n")
        self.assertIn("committed", self.verify(ok=False).stderr)
        self.commit()
        self.assertIn("stale", self.verify(ok=False).stderr)

    def test_open_sources_pass_but_required_findings_block_completion(self):
        self.beads["app-1"]["status"] = "open"
        self.verify("work")
        self.verify()
        review = json.loads((self.root / "review.json").read_text())
        review["findings"] = [{"required": True, "status": "open", "bead": "finding-1"}]
        self.write("review", review)
        self.verify(ok=False)
        review["findings"][0]["status"] = "resolved"
        self.write("review", review)
        self.beads["finding-1"] = {"id": "finding-1", "status": "open", "metadata": {"omg.operation": "build-1"}}
        self.verify(ok=False)
        self.beads["finding-1"]["status"] = "closed"
        self.verify()

    def test_closed_sources_cannot_bypass_missing_execution(self):
        for status in ["open", "closed"]:
            with self.subTest(status=status):
                self.beads["app-1"]["status"] = status
                self.beads.pop("drain-1", None)
                self.assertIn("exactly one implementation drain", self.verify(ok=False).stderr)

    def test_pass_root_cannot_hide_unfinished_execution_or_finalizer(self):
        for identifier in ["executable-1", "finalizer-1"]:
            with self.subTest(identifier=identifier):
                self.beads[identifier]["status"] = "in_progress"
                self.assertIn("unfinished", self.verify(ok=False).stderr)
                self.beads[identifier]["status"] = "closed"
        self.beads["executable-1"]["metadata"]["gc.outcome"] = "fail"
        self.verify()  # A closed failed attempt can precede a successful retry.
        self.beads["finalizer-1"]["metadata"]["gc.outcome"] = "fail"
        self.assertIn("item finalizer", self.verify(ok=False).stderr)
        del self.beads["finalizer-1"]
        self.assertIn("exactly one item workflow finalizer", self.verify(ok=False).stderr)

    def test_graph_contract_and_canonical_step_identity_are_required(self):
        for identifier in ["workflow-1", "item-1"]:
            self.beads[identifier]["metadata"].pop("gc.formula_contract")
            self.assertIn("bindings or outcome", self.verify(ok=False).stderr)
            self.beads[identifier]["metadata"]["gc.formula_contract"] = "graph.v2"
        for key in ["gc.step_id", "gc.step_ref"]:
            self.beads["drain-1"]["metadata"][key] = "implement"
            self.assertIn("implementation drain", self.verify(ok=False).stderr)
            self.beads["drain-1"]["metadata"][key] = "omg-build.implement"

    def test_invalid_drain_identity_and_completion_fail(self):
        original = copy.deepcopy(self.beads)
        for key, value in [("gc.root_bead_id", "old-run"), ("gc.kind", "workflow"),
                           ("gc.step_id", "other"), ("gc.drain_parent_convoy_id", "other"),
                           ("gc.drain_formula", "other"), ("gc.drain_state", "failed"),
                           ("gc.outcome", "fail"), ("gc.drain_state", "expanded")]:
            with self.subTest(key=key, value=value):
                self.beads = copy.deepcopy(original)
                self.beads["drain-1"]["metadata"][key] = value
                self.assertIn("execution", self.verify(ok=False).stderr)
        self.beads = copy.deepcopy(original)
        self.beads["drain-1"]["status"] = "open"
        self.verify(ok=False)
        self.beads = copy.deepcopy(original)
        self.beads["drain-2"] = copy.deepcopy(self.beads["drain-1"])
        self.beads["drain-2"]["id"] = "drain-2"
        self.assertIn("exactly one", self.verify(ok=False).stderr)

    def test_missing_active_failed_and_wrong_run_item_roots_fail(self):
        original = copy.deepcopy(self.beads["item-1"])
        del self.beads["item-1"]
        self.assertIn("missing or mismatched", self.verify(ok=False).stderr)
        for status in ["open", "in_progress"]:
            self.beads["item-1"] = {**copy.deepcopy(original), "status": status}
            self.assertIn("not closed", self.verify(ok=False).stderr)
        for key, value in [("gc.outcome", "fail"), ("gc.var.operation", "previous-run"),
                           ("gc.var.initiative", "other"), ("gc.drain_control_id", "other"),
                           ("gc.drain_member_id", "other"), ("gc.input_convoy_id", "other"),
                           ("gc.kind", "task"), ("gc.formula_name", "other"),
                           ("gc.item_root_key", "other")]:
            with self.subTest(key=key):
                self.beads["item-1"] = copy.deepcopy(original)
                self.beads["item-1"]["metadata"][key] = value
                self.assertIn("bindings or outcome", self.verify(ok=False).stderr)

    def test_manifest_schema_inventory_and_row_outcomes_fail_closed(self):
        variants = [None, {}, {**self.manifest, "version": 2}, {**self.manifest, "version": True},
                    {**self.manifest, "rows": []}, {**self.manifest, "rows": None},
                    {**self.manifest, "rows": self.manifest["rows"] * 2},
                    {**self.manifest, "parent_convoy_id": "other"}]
        for key, value in [("member_id", "other"), ("item_root_id", ""), ("status", "failed"),
                           ("status", "active"), ("outcome_kind", "fail"), ("index", "0"),
                           ("outcome_bead_id", "other")]:
            row = {**self.manifest["rows"][0], key: value}
            variants.append({**self.manifest, "rows": [row]})
        for manifest in variants:
            with self.subTest(manifest=manifest):
                self.beads["drain-1"]["metadata"]["gc.drain_manifest.v1"] = encoded(manifest)
                self.assertIn("execution", self.verify(ok=False).stderr)
        self.beads["drain-1"]["metadata"]["gc.drain_manifest.v1"] = "not JSON"
        self.verify(ok=False)

    def test_multi_member_proof_requires_distinct_roots_and_exact_inventory(self):
        decomposition = {"workflow": "workflow-1", "convoy": "convoy-1",
                         "items": [{"id": "app-1"}, {"id": "app-2"}]}
        manifest = copy.deepcopy(self.manifest)
        manifest["rows"].append({"index": 1, "member_id": "app-2", "unit_key": "unit-key-2",
                                 "unit_convoy_id": "unit-2", "item_root_key": "root-key-2",
                                 "item_root_id": "item-2", "status": "succeeded", "outcome_kind": "pass",
                                 "outcome_bead_id": "item-2"})
        self.beads["item-1"]["metadata"]["gc.drain_count"] = "2"
        self.beads["item-2"] = copy.deepcopy(self.beads["item-1"])
        self.beads["item-2"]["id"] = "item-2"
        self.beads["finalizer-2"] = self.finalizer("finalizer-2", "item-2")
        self.beads["item-2"]["metadata"].update({"gc.drain_member_id": "app-2",
            "gc.input_convoy_id": "unit-2", "gc.item_root_key": "root-key-2", "gc.drain_index": "1"})
        units = {"unit-1": "app-1", "unit-2": "app-2"}
        unit_ids = {"unit-1": "unit-1", "unit-2": "unit-2"}

        def call(*args):
            if args[:2] == ("bd", "show"):
                return self.beads.get(args[2], [])
            if args == ("bd", "list", "--all", "--limit", "0", "--long"):
                return list(self.beads.values())
            if args[:2] == ("convoy", "status"):
                return {"convoy": {"id": unit_ids[args[2]]}, "children": [{"id": units[args[2]]}]}
            self.fail(f"non-read-only call: {args}")

        def validate(value):
            self.beads["drain-1"]["metadata"]["gc.drain_manifest.v1"] = encoded(value)
            return EXECUTION.validate_execution(decomposition, "build-1", "city-1", call)

        self.assertEqual(validate(manifest), {"drain_id": "drain-1", "rows": manifest["rows"]})
        for key in ["item_root_id", "item_root_key", "unit_convoy_id", "unit_key", "member_id"]:
            with self.subTest(key=key):
                bad = copy.deepcopy(manifest)
                bad["rows"][1][key] = bad["rows"][0][key]
                with self.assertRaises(ValueError):
                    validate(bad)
        with self.assertRaisesRegex(ValueError, "inventory"):
            validate({**manifest, "rows": manifest["rows"][:1]})
        units["unit-2"] = "unrelated-source"
        with self.assertRaisesRegex(ValueError, "unit convoy membership"):
            validate(manifest)
        units["unit-2"] = "app-2"
        unit_ids["unit-2"] = "unrelated-convoy"
        with self.assertRaisesRegex(ValueError, "unit convoy identity"):
            validate(manifest)

    def test_reconciliation_cannot_omit_or_defer_requirement(self):
        for rows in [[], [{"id": "R1", "status": "deferred", "evidence": "later"}]]:
            self.write("reconciliation", {"revision": self.head, "review_sha256": self.hash(self.root / "review.json"), "requirements": rows})
            self.verify("reconcile", ok=False)

    def test_omitting_a_required_finding_cannot_pass(self):
        self.beads["finding-1"] = {"id": "finding-1", "status": "open", "metadata": {"omg.operation": "build-1", "omg.required": "true"}}
        self.assertIn("finding inventory", self.verify(ok=False).stderr)
        self.beads["finding-1"]["status"] = "closed"
        self.verify(ok=False)  # Resolution still needs review evidence.

    def mixed_contract(self):
        self.spec.write_text('---\nschema_version: 2\ntype: spec\n---\n'
                            'R1: Required behavior.\nB01: Validate locally.\nS01: Deliver smoke script.\nO01: Operator runs smoke after release.\n'
                            '```omg-delivery\nversion: 1\nrequirements:\n'
                            '  R1: {kind: implementation}\n  B01: {kind: development-check}\n'
                            '  S01: {kind: verification-artifact}\n'
                            '  O01: {kind: downstream-check, owner: operator, stage: post-deployment}\n```\n')
        self.files['spec.md']['sha256'] = self.hash(self.spec)
        self.baseline['digest'] = hashlib.sha256(encoded(self.files).encode()).hexdigest()
        self.write('baseline', self.baseline)
        self.state['operations']['build-1']['approved']['digest'] = self.baseline['digest']
        self.beads['city-1']['metadata']['omg.state'] = encoded(self.state)
        rows = [{"id": key, "kind": kind, "source": "spec.md", "quote": quote} for key, kind, quote in [
            ('R1', 'implementation', 'R1: Required behavior.'),
            ('B01', 'development-check', 'B01: Validate locally.'),
            ('S01', 'verification-artifact', 'S01: Deliver smoke script.'),
            ('O01', 'downstream-check', 'O01: Operator runs smoke after release.')]]
        rows[-1].update(owner='operator', stage='post-deployment')
        self.write('plan', {'requirements': rows})
        self.refresh_plan_review()
        self.write('decomposition', {'workflow': 'workflow-1', 'convoy': 'convoy-1',
                                    'items': [{'id': 'app-1', 'requirements': ['R1', 'B01', 'S01']}],
                                    'downstream': [{'id': 'O01', 'owner': 'operator', 'stage': 'post-deployment'}]})
        (self.repo / 'smoke.sh').write_text('#!/bin/sh\n# The deployment pipeline supplies the target.\ntest -n "$DEPLOYED_TARGET"\n')
        self.git('add', 'smoke.sh')
        self.commit()
        checks = self.checks()
        checks[0]['requirements'] = ['B01']
        self.write('work/app-1', {'operation': 'build-1', 'work': 'app-1', 'revision': self.head, 'checks': checks})
        self.write('tests', {'operation': 'build-1', 'revision': self.head, 'checks': checks})
        self.write('review', {'revision': self.head, 'tests_sha256': self.hash(self.root / 'tests.json'), 'verdict': 'pass', 'findings': []})
        self.write('reconciliation', {'revision': self.head, 'review_sha256': self.hash(self.root / 'review.json'), 'requirements': [
            {'id': 'R1', 'status': 'implemented', 'evidence': 'app.txt'},
            {'id': 'B01', 'status': 'implemented', 'evidence': 'logs/test.txt'},
            {'id': 'S01', 'status': 'implemented', 'evidence': 'script reviewed and checked locally', 'artifacts': ['smoke.sh']},
            {'id': 'O01', 'status': 'pending-downstream', 'owner': 'operator', 'stage': 'post-deployment', 'evidence': 'CI/CD executes smoke.sh after promotion'}]})
        self.write('publication', {'revision': self.head, 'development': 'verified', 'status': 'local', 'deployed': False, 'pr_approved': False})

    def test_pending_downstream_results_allow_development_completion(self):
        self.mixed_contract()
        for stage in ['contract', 'plan', 'decompose', 'work', 'quality', 'reconcile', 'finalize']:
            with self.subTest(stage=stage):
                self.verify(stage)

    def test_plan_cannot_reclassify_or_omit_development_requirement(self):
        self.mixed_contract()
        original = json.loads((self.root / 'plan.json').read_text())
        for omit in [False, True]:
            plan = copy.deepcopy(original)
            if omit:
                plan['requirements'].pop(1)
            else:
                plan['requirements'][1].update(kind='downstream-check', owner='operator', stage='later')
            self.write('plan', plan)
            self.refresh_plan_review()
            self.assertIn('approved delivery contract', self.verify('plan', ok=False).stderr)

    def test_operator_ids_cannot_be_assigned_to_builders_or_dropped(self):
        self.mixed_contract()
        original = json.loads((self.root / 'decomposition.json').read_text())
        for omit in [False, True]:
            d = copy.deepcopy(original)
            if omit:
                d['downstream'] = []
            else:
                d['items'][0]['requirements'].append('O01')
            self.write('decomposition', d)
            self.verify('decompose', ok=False)

    def test_missing_local_check_coverage_still_blocks(self):
        self.mixed_contract()
        tests = json.loads((self.root / 'tests.json').read_text())
        for ids in [[], ['O01'], ['B01', 'O01']]:
            tests['checks'][0]['requirements'] = ids
            self.write('tests', tests)
            self.assertIn('development-check coverage', self.verify('quality', ok=False).stderr)

    def test_missing_required_downstream_script_blocks_development(self):
        self.mixed_contract()
        reconciliation = json.loads((self.root / 'reconciliation.json').read_text())
        reconciliation['requirements'][2]['artifacts'] = ['missing-smoke.sh']
        self.write('reconciliation', reconciliation)
        self.assertIn('artifact not committed', self.verify('reconcile', ok=False).stderr)

    def test_unfinished_development_and_false_live_claims_fail(self):
        self.mixed_contract()
        original = json.loads((self.root / 'reconciliation.json').read_text())
        for index, status in [(0, 'pending-downstream'), (1, 'deferred'), (2, 'partial'), (3, 'implemented')]:
            r = copy.deepcopy(original)
            r['requirements'][index]['status'] = status
            self.write('reconciliation', r)
            self.verify('reconcile', ok=False)

    def test_local_handoff_cannot_claim_publication_approval_or_deployment(self):
        self.mixed_contract()
        original = json.loads((self.root / 'publication.json').read_text())
        for field, value in [('status', 'pr-open'), ('pr_approved', True), ('deployed', True), ('remote_ref', 'origin/master')]:
            self.write('publication', {**original, field: value})
            self.verify('finalize', ok=False)

    def test_direct_push_and_pr_handoffs_are_distinct_and_optional(self):
        self.mixed_contract()
        for pr in [False, True]:
            self.baseline['publication'] = {'push': True, 'open_pr': pr}
            self.state['operations']['build-1']['publication'] = self.baseline['publication']
            self.beads['city-1']['metadata']['omg.state'] = encoded(self.state)
            self.write('baseline', self.baseline)
            publication = {'revision': self.head, 'development': 'verified', 'deployed': False, 'pr_approved': False,
                           'status': 'pr-open' if pr else 'pushed', 'remote_ref': 'origin/feature' if pr else 'origin/master'}
            if pr:
                publication['pr_url'] = 'https://example.invalid/pull/1'
            self.write('publication', publication)
            self.verify('finalize')

    # Post-settlement report. By default the initiative repository is the rig
    # checkout, so the report commit sits on top of local, unpushed code commits.
    REPORT_PATH = "docs/initiatives/city-1/reports/build-1.md"

    def settle(self, outcome="pass", publication=None, receipt=None, separate_docs=False):
        self.mixed_contract()
        if publication:
            self.baseline["publication"] = publication
            self.write("baseline", self.baseline)
        if receipt:
            self.write("publication", {"revision": self.head, "development": "verified", "deployed": False,
                                       "pr_approved": False, **receipt})
        self.docs = self.repo
        if separate_docs:
            self.docs = self.base / "docs repo"
            self.docs.mkdir()
            self.docs_git("init", "-q")
            (self.docs / "README.md").write_text("initiative documents\n")
            self.docs_git("add", "README.md")
            self.docs_commit("docs")
        self.state.update(repo=str(self.docs), directory="docs/initiatives/city-1", slug="city-1")
        self.state["operations"]["build-1"].update(phase="settled", workflow="workflow-1", outcome=outcome,
                                                   publication=self.baseline["publication"])
        self.beads["city-1"]["metadata"]["omg.state"] = encoded(self.state)
        self.beads["workflow-1"].update(status="closed")
        if outcome is None:
            self.beads["workflow-1"]["metadata"].pop("gc.outcome", None)
        else:
            self.beads["workflow-1"]["metadata"]["gc.outcome"] = outcome
        self.beads["report-check"] = {"id": "report-check", "metadata": {
            "omg.stage": "report", "omg.artifact_root": str(self.root), "omg.operation": "build-1",
            "omg.initiative": "city-1", "gc.root_bead_id": "workflow-1"}}
        # Unrelated user changes stay in the shared checkout and must be neither
        # required to be clean nor swept into the report commit.
        (self.repo / "notes.txt").write_text("untracked scratch\n")
        (self.repo / "app.txt").write_text("uncommitted edit\n")

    def docs_git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.docs), *args], text=True).strip()

    def docs_commit(self, message, *args):
        self.docs_git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
                      "commit", "-qm", message, *args)
        return self.docs_git("rev-parse", "HEAD")

    def report_document(self, revision=None, identity="build-report.city-1.build-1", status="draft", source="agent"):
        return (f"---\nschema_version: 2\nid: {identity}\ntype: build-report\ntitle: Build report\n"
                f"status: {status}\nsource: {source}\nscope: repo\ncreated_at: 2026-09-26T00:00:00Z\n"
                f"updated_at: 2026-09-26T00:00:00Z\n---\nOperation build-1 assessed revision {revision or self.head}.\n")

    def commit_report(self, content=None, only=True):
        """The documented path-only commit; only=False is a careless plain commit."""
        doc = self.docs / self.REPORT_PATH
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(content or self.report_document())
        self.docs_git("add", "--", self.REPORT_PATH)
        return self.docs_commit("docs: build report", *(["--only", "--", self.REPORT_PATH] if only else []))

    def receipt(self, commit, **overrides):
        record = {"operation": "build-1", "workflow": "workflow-1", "build_outcome": "pass", "revision": self.head,
                  "path": self.REPORT_PATH, "id": "build-report.city-1.build-1",
                  "sha256": self.hash(self.docs / self.REPORT_PATH), "commit": commit,
                  "status": "local", "remote_ref": None}
        record.update(overrides)
        self.write("report", record)
        return record

    def verify_report(self, ok=True, controller=False):
        args = {"controller": True, "restricted": True} if controller else {}
        return self.verify("report", ok=ok, **args)

    def add_remote(self):
        remote = self.base / "origin.git"
        subprocess.check_call(["git", "init", "-q", "--bare", str(remote)])
        self.git("remote", "add", "origin", str(remote))
        return self.git("symbolic-ref", "--short", "HEAD")

    def test_local_only_build_completes_with_durable_local_report(self):
        self.settle()
        commit = self.commit_report()
        self.receipt(commit)
        self.verify_report()
        self.verify_report(controller=True)
        self.assertEqual(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", commit), self.REPORT_PATH)
        self.assertIn("?? notes.txt", self.git("status", "--porcelain"))
        self.assertEqual(self.git("remote"), "")  # no remote exists; the local path never talks to one

    def test_path_only_commit_leaves_prestaged_changes_in_the_index(self):
        self.settle()
        self.git("add", "app.txt")
        staged = self.git("rev-parse", ":app.txt")
        commit = self.commit_report()
        self.receipt(commit)
        self.verify_report()
        self.assertEqual(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", commit), self.REPORT_PATH)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "app.txt")
        self.assertEqual(self.git("rev-parse", ":app.txt"), staged)
        self.assertNotEqual(self.git("rev-parse", "HEAD:app.txt"), staged)

    def test_report_commit_cannot_sweep_in_prestaged_files(self):
        self.settle()
        self.git("add", "app.txt")
        commit = self.commit_report(only=False)
        self.receipt(commit)
        self.assertIn("change only the report", self.verify_report(ok=False).stderr)

    def test_terminal_outcomes_are_reported_exactly(self):
        for outcome in ["fail", "canceled", "skipped"]:
            with self.subTest(outcome=outcome):
                self.setUp()
                self.settle(outcome=outcome)
                for name in ["plan", "plan-review", "decomposition", "tests", "review", "reconciliation", "publication"]:
                    (self.root / (name + ".json")).unlink()
                commit = self.commit_report()
                self.receipt(commit, build_outcome=outcome)
                self.verify_report()
                for claimed in ["pass", "unknown"]:
                    self.receipt(commit, build_outcome=claimed)
                    self.assertIn("actual outcome", self.verify_report(ok=False).stderr)
        for outcome in [None, "mystery"]:
            with self.subTest(outcome=outcome):
                self.setUp()
                self.settle(outcome=outcome)
                commit = self.commit_report()
                self.receipt(commit, build_outcome="unknown")
                self.verify_report()
                self.receipt(commit, build_outcome="pass")
                self.assertIn("actual outcome", self.verify_report(ok=False).stderr)
        self.setUp()
        self.settle()
        commit = self.commit_report()
        self.receipt(commit)
        (self.root / "publication.json").unlink()
        self.assertIn("publication", self.verify_report(ok=False).stderr)

    def test_stale_or_false_report_receipts_fail(self):
        self.settle()
        commit = self.commit_report()
        self.receipt(commit, sha256="0" * 64)
        self.assertIn("hash", self.verify_report(ok=False).stderr)
        self.receipt(commit, path="docs/initiatives/city-1/reports/../../../other.md")
        self.verify_report(ok=False)
        self.receipt(self.git("rev-parse", "HEAD~1"))
        self.assertIn("change only", self.verify_report(ok=False).stderr)
        self.receipt(commit, revision="b" * 40)
        self.assertIn("code history", self.verify_report(ok=False).stderr)
        self.receipt(commit, revision=self.git("rev-parse", "HEAD~2"))  # older code commit than finalized
        self.assertIn("publication receipt", self.verify_report(ok=False).stderr)
        self.receipt(commit, workflow="other")
        self.verify_report(ok=False)
        self.receipt(commit)
        self.beads["report-check"]["metadata"]["gc.root_bead_id"] = "other"
        self.assertIn("another workflow", self.verify_report(ok=False, controller=True).stderr)
        self.beads["report-check"]["metadata"]["gc.root_bead_id"] = "workflow-1"
        self.receipt(commit)
        (self.repo / self.REPORT_PATH).write_text("edited after commit\n")
        self.assertIn("changed after", self.verify_report(ok=False).stderr)
        later = self.commit_report(self.report_document() + "\nRetry addendum.\n")
        self.assertIn("changed after", self.verify_report(ok=False).stderr)  # receipt names the superseded commit
        self.receipt(later)  # a re-committed report with a fresh receipt is the retry path
        self.verify_report()

    def test_initiative_directory_is_validated_not_trusted(self):
        self.settle()
        commit = self.commit_report()
        self.receipt(commit)
        for directory, slug in [("docs/initiatives/city-1/..", "city-1"), ("docs/initiatives/../city-1", "city-1"),
                                ("docs/initiatives/./city-1", "city-1"), (str(self.repo / "docs/initiatives/city-1"), "city-1"),
                                ("docs/other/city-1", "city-1"), ("docs/initiatives/City-1", "City-1"),
                                ("docs/initiatives/city-1", "other"), ("docs/initiatives/city-1/", "city-1")]:
            with self.subTest(directory=directory, slug=slug):
                self.state.update(directory=directory, slug=slug)
                self.beads["city-1"]["metadata"]["omg.state"] = encoded(self.state)
                self.assertIn("initiative directory", self.verify_report(ok=False).stderr)
        self.state.update(directory="docs/initiatives/city-1", slug="city-1")
        self.beads["city-1"]["metadata"]["omg.state"] = encoded(self.state)
        self.verify_report()
        # A legitimate multi-segment slug works end to end.
        self.setUp()
        self.REPORT_PATH = "docs/initiatives/my-init-2/reports/build-1.md"
        self.settle()
        self.state.update(directory="docs/initiatives/my-init-2", slug="my-init-2")
        self.beads["city-1"]["metadata"]["omg.state"] = encoded(self.state)
        commit = self.commit_report(self.report_document(identity="build-report.my-init-2.build-1"))
        self.receipt(commit, id="build-report.my-init-2.build-1")
        self.verify_report()

    def test_report_frontmatter_and_content_are_checked(self):
        self.settle()
        for content in [self.report_document(identity="spec.example"),
                        self.report_document(status="accepted", source="human"),
                        self.report_document(source="human"),
                        self.report_document().replace("type: build-report", "type: spec"),
                        self.report_document(revision="c" * 40)]:
            commit = self.commit_report(content)
            self.receipt(commit)
            self.verify_report(ok=False)
        commit = self.commit_report()
        self.receipt(commit, id="build-report.other")
        self.assertIn("frontmatter", self.verify_report(ok=False).stderr)

    def test_report_requires_settled_operation(self):
        self.settle()
        commit = self.commit_report()
        self.receipt(commit)
        self.state["operations"]["build-1"]["phase"] = "launched"
        self.beads["city-1"]["metadata"]["omg.state"] = encoded(self.state)
        self.assertIn("settle", self.verify_report(ok=False).stderr)

    def test_unauthorized_report_publication_is_rejected(self):
        self.settle()
        commit = self.commit_report()
        self.receipt(commit, status="pushed", remote_ref="origin/master")
        self.assertIn("stays local", self.verify_report(ok=False).stderr)
        self.receipt(commit, status="failed", error="push rejected")
        self.assertIn("stays local", self.verify_report(ok=False).stderr)

    def test_authority_binds_to_the_build_publication_receipt(self):
        # A distinct initiative repository has no report publication authority,
        # even when the code push or PR was authorized and happened.
        self.settle(publication={"push": True, "open_pr": False}, receipt={"status": "pushed", "remote_ref": "origin/master"},
                    separate_docs=True)
        commit = self.commit_report()
        self.receipt(commit)
        self.verify_report()
        self.receipt(commit, status="pushed", remote_ref="origin/master")
        self.assertIn("stays local", self.verify_report(ok=False).stderr)
        # Same repository, publication authorized, but the build failed before a
        # publication receipt existed: nothing was published, so the report stays local.
        self.setUp()
        self.settle(outcome="fail", publication={"push": True, "open_pr": False})
        (self.root / "publication.json").unlink()
        commit = self.commit_report()
        self.receipt(commit, build_outcome="fail")
        self.verify_report()
        self.receipt(commit, build_outcome="fail", status="pushed", remote_ref="origin/master")
        self.assertIn("stays local", self.verify_report(ok=False).stderr)

    # --- worker-side publication (report publish) -------------------------

    def publish(self, *args, ok=True, restricted=False, extra_env=None):
        self.transport.write_text(encoded(self.beads))
        env = self.env.copy()
        if restricted:
            env.update(PATH=self.tool_path(), HOME=str(self.base))
            env.pop("SSH_AUTH_SOCK", None)
        env.update(extra_env or {})
        result = subprocess.run([str(PACK / "assets/scripts/report-publish.sh"), "publish", "--root", str(self.root), *args],
                                cwd=self.base, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        result.json = json.loads(result.stdout) if result.stdout.strip() else None
        return result

    def remote_tip(self, branch):
        return subprocess.check_output(["git", "-C", str(self.base / "origin.git"), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
                                       text=True).strip()

    def authorized(self, pr=False):
        """Rig with a bare remote; the finalized code (C, the assessed revision) is on the authorized branch."""
        self.add_remote()
        ref = "origin/feature/omg-build-1" if pr else "origin/master"
        receipt = {"status": "pr-open" if pr else "pushed", "remote_ref": ref}
        if pr:
            receipt["pr_url"] = "https://example.invalid/pull/1"
        self.settle(publication={"push": not pr, "open_pr": pr}, receipt=receipt)
        self.branch = ref.split("/", 1)[1]
        self.git("push", "-q", "origin", f"HEAD:refs/heads/{self.branch}")
        return ref

    def report_json(self):
        return json.loads((self.root / "report.json").read_text())

    def test_destination_requires_a_passed_root(self):
        for outcome in ["fail", "canceled", "skipped", None]:
            with self.subTest(outcome=outcome):
                self.setUp()
                self.add_remote()
                self.settle(outcome=outcome, publication={"push": True, "open_pr": False},
                            receipt={"status": "pushed", "remote_ref": "origin/master"})
                self.git("push", "-q", "origin", "HEAD:refs/heads/master")
                commit = self.commit_report()
                self.receipt(commit, build_outcome=outcome or "unknown")
                self.verify_report()
                self.assertEqual(self.publish().json["status"], "local")
                self.assertEqual(self.remote_tip("master"), self.head)
                self.receipt(commit, build_outcome=outcome or "unknown", status="pushed", remote_ref="origin/master")
                self.assertIn("stays local", self.verify_report(ok=False).stderr)

    def test_local_only_publish_touches_nothing(self):
        self.settle()
        commit = self.commit_report()
        before = self.receipt(commit)
        raw = (self.root / "report.json").read_bytes()
        self.assertEqual(self.publish("--preflight").json, {"status": "preflight", "destination": None, "normalize": False})
        self.assertEqual(self.publish().json, {"status": "local", "destination": None, "normalized": False})
        self.assertEqual((self.root / "report.json").read_bytes(), raw)
        self.assertEqual(self.report_json(), before)
        self.verify_report()

    def test_publish_pushes_the_exact_report_sha_and_records_verified_proof(self):
        for pr in [False, True]:
            with self.subTest(pr=pr):
                self.setUp()
                ref = self.authorized(pr)
                commit = self.commit_report()
                self.receipt(commit)
                self.assertIn("publish it to " + ref, self.verify_report(ok=False).stderr)
                plan = self.publish("--preflight").json
                self.assertEqual((plan["status"], plan["destination"], plan["commit"], plan["base"], plan["outgoing"]),
                                 ("preflight", ref, commit, self.head, [commit]))
                self.assertEqual(self.report_json()["status"], "local")
                self.assertEqual(self.remote_tip(self.branch), self.head)
                done = self.publish().json
                self.assertEqual((done["status"], done["destination"], done["commit"]), ("pushed", ref, commit))
                self.assertEqual(self.remote_tip(self.branch), commit)
                receipt = self.report_json()
                self.assertEqual(receipt["status"], "pushed")
                self.assertEqual(receipt["remote_ref"], ref)
                proof = receipt["publication"]
                self.assertEqual((proof["destination"], proof["base"], proof["pushed"], proof["observed"], proof["revision"]),
                                 (ref, self.head, commit, commit, self.head))
                self.assertEqual(proof["report_blob"], self.git("rev-parse", f"{commit}:{self.REPORT_PATH}"))
                self.verify_report()
                # Publishing again is idempotent: nothing outgoing, same proof.
                again = self.publish().json
                self.assertEqual((again["status"], again["base"]), ("pushed", commit))
                self.verify_report()
                # The controller check is offline: it passes with the remote unreachable
                # and without any Git credentials, because it checks the retained proof.
                self.git("remote", "set-url", "origin", "git@example.invalid:omg/docs.git")
                self.verify_report(controller=True)
                # Tampered or inconsistent proof fails.
                for field, value in [("observed", self.head), ("pushed", self.head), ("base", "0" * 40),
                                     ("revision", "b" * 40), ("report_blob", "0" * 40)]:
                    self.receipt(commit, status="pushed", remote_ref=ref, publication={**proof, field: value})
                    self.verify_report(ok=False)
                self.receipt(commit, status="pushed", remote_ref=ref)
                self.assertIn("evidence", self.verify_report(ok=False).stderr)

    def test_unrelated_outgoing_commit_blocks_publication_without_remote_mutation(self):
        ref = self.authorized()
        assessed = self.head
        (self.repo / "app.txt").write_text("unpublished code change\n")
        self.commit()  # U: not report-only, not published
        commit = self.commit_report(self.report_document(revision=assessed))  # R on top of U
        self.receipt(commit, revision=assessed)
        self.assertIn("publish it to", self.verify_report(ok=False).stderr)
        result = self.publish(ok=False)
        self.assertEqual((result.json["status"], result.json["reason"]), ("failed", "outgoing"))
        self.assertIn(self.git("rev-parse", "HEAD~1"), result.json["error"])
        self.assertEqual(self.remote_tip(self.branch), assessed)
        receipt = self.report_json()
        self.assertEqual((receipt["status"], receipt["reason"], receipt["remote_ref"]), ("failed", "outgoing", None))
        self.assertEqual(receipt["commit"], commit)  # the local artifact is preserved
        stderr = self.verify_report(ok=False).stderr
        self.assertIn("recoverable", stderr)
        self.assertIn("outgoing", stderr)
        # A hand-written pushed receipt cannot launder the unrelated commit either.
        self.git("push", "-q", "origin", f"HEAD:refs/heads/{self.branch}")
        self.receipt(commit, revision=assessed, status="pushed", remote_ref=ref, publication={
            "destination": ref, "url": str(self.base / "origin.git"), "base": assessed, "pushed": commit,
            "observed": commit, "revision": assessed, "report_blob": self.git("rev-parse", f"{commit}:{self.REPORT_PATH}")})
        self.assertIn("not a report-only commit", self.verify_report(ok=False).stderr)

    def test_report_only_retries_publish_together(self):
        ref = self.authorized()
        first = self.commit_report(self.report_document(identity="build-report.wrong"))
        second = self.commit_report()
        self.receipt(second)
        self.assertEqual(self.publish("--preflight").json["outgoing"], [second, first])
        self.assertEqual(self.publish().json["status"], "pushed")
        self.assertEqual(self.remote_tip(self.branch), second)
        self.assertEqual(self.report_json()["publication"]["base"], self.head)
        self.verify_report()
        self.verify_report(controller=True)

    def test_moved_remote_fails_closed_before_any_push(self):
        ref = self.authorized()
        assessed = self.head
        commit = self.commit_report()
        self.receipt(commit)
        # Someone else advanced the authorized branch after finalization.
        other = self.base / "other"
        subprocess.check_call(["git", "clone", "-q", str(self.base / "origin.git"), str(other)])
        (other / "theirs.txt").write_text("concurrent\n")
        subprocess.check_call(["git", "-C", str(other), "add", "theirs.txt"])
        subprocess.check_call(["git", "-C", str(other), "-c", "user.name=T", "-c", "user.email=t@example.invalid",
                               "-c", "commit.gpgsign=false", "commit", "-qm", "theirs"])
        subprocess.check_call(["git", "-C", str(other), "push", "-q", "origin", f"HEAD:refs/heads/{self.branch}"])
        moved = self.remote_tip(self.branch)
        result = self.publish(ok=False)
        self.assertEqual((result.json["status"], result.json["reason"]), ("failed", "diverged"))
        self.assertIn(moved, result.json["error"])
        self.assertEqual(self.remote_tip(self.branch), moved)
        self.assertEqual(self.report_json()["status"], "failed")
        self.assertIn("recoverable", self.verify_report(ok=False).stderr)
        # The remote no longer holding the assessed revision is its own blocker.
        subprocess.check_call(["git", "-C", str(self.base / "origin.git"), "update-ref", f"refs/heads/{self.branch}",
                               self.git("rev-parse", f"{assessed}~1")])
        result = self.publish(ok=False)
        self.assertEqual(result.json["reason"], "revision_not_published")
        self.assertIn(assessed, result.json["error"])

    def test_remote_failures_retain_diagnostics_under_worker_identity(self):
        ref = self.authorized()
        commit = self.commit_report()
        self.receipt(commit)
        # Authentication or network failure: the worker's Git identity could not
        # reach the remote. The exact stderr is retained and never relabelled.
        self.git("remote", "set-url", "origin", "git@example.invalid:omg/docs.git")
        result = self.publish(ok=False, restricted=True, extra_env={"GIT_SSH_COMMAND": "false"})
        self.assertEqual((result.json["status"], result.json["reason"]), ("failed", "remote"))
        self.assertIn("Could not read from remote repository", result.json["error"])
        receipt = self.report_json()
        self.assertEqual((receipt["status"], receipt["reason"]), ("failed", "remote"))
        self.assertIn("Could not read from remote repository", receipt["error"])
        stderr = self.verify_report(ok=False, controller=True).stderr
        self.assertIn("Could not read from remote repository", stderr)
        self.assertIn("recoverable", stderr)
        for wrong in ["not found", "frontmatter", "report-only", "hash"]:
            self.assertNotIn(wrong, stderr)
        self.assertEqual(receipt["commit"], commit)
        # Missing branch is reported as such, distinct from an unreachable remote.
        self.git("remote", "set-url", "origin", str(self.base / "origin.git"))
        subprocess.check_call(["git", "-C", str(self.base / "origin.git"), "update-ref", "-d", f"refs/heads/{self.branch}"])
        result = self.publish(ok=False)
        self.assertEqual(result.json["reason"], "missing_branch")
        self.assertIn(ref, result.json["error"])
        # A rejected push keeps the remote untouched and retains the server's message.
        self.git("push", "-q", "origin", f"{self.head}:refs/heads/{self.branch}")
        hook = self.base / "origin.git" / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'policy: report pushes refused' >&2\nexit 1\n")
        hook.chmod(0o755)
        result = self.publish(ok=False)
        self.assertEqual(result.json["reason"], "push")
        self.assertIn("policy: report pushes refused", result.json["error"])
        self.assertEqual(self.remote_tip(self.branch), self.head)
        self.assertIn("policy: report pushes refused", self.verify_report(ok=False).stderr)
        hook.unlink()
        # After the blocker clears, the retained local artifact publishes as is.
        self.assertEqual(self.publish().json["status"], "pushed")
        self.verify_report()

    def test_ambiguous_push_endpoints_are_rejected_before_any_write(self):
        ref = self.authorized()
        commit = self.commit_report()
        self.receipt(commit)
        other = self.base / "other.git"
        subprocess.check_call(["git", "init", "-q", "--bare", str(other)])
        subprocess.check_call(["git", "-C", str(other), "symbolic-ref", "HEAD", "refs/heads/master"])
        self.git("push", "-q", str(other), f"{self.head}:refs/heads/{self.branch}")
        # A push URL that differs from the fetch URL would publish to a repository
        # the code receipt never named; two push URLs would publish twice.
        for urls in [[str(other)], [str(self.base / "origin.git"), str(other)]]:
            with self.subTest(pushurls=urls):
                subprocess.run(["git", "-C", str(self.repo), "config", "--unset-all", "remote.origin.pushurl"])
                for url in urls:
                    self.git("config", "--add", "remote.origin.pushurl", url)
                for args in [("--preflight",), ()]:
                    result = self.publish(*args, ok=False)
                    self.assertEqual((result.json["status"], result.json["reason"]), ("failed", "remote_config"))
                    self.assertIn("push", result.json["error"])
                self.assertEqual(self.remote_tip(self.branch), self.head)
                self.assertEqual(subprocess.check_output(["git", "-C", str(other), "rev-parse", f"refs/heads/{self.branch}"], text=True).strip(), self.head)
                self.assertEqual(self.report_json()["status"], "failed")
        subprocess.run(["git", "-C", str(self.repo), "config", "--unset-all", "remote.origin.pushurl"])
        self.git("config", "--add", "remote.origin.pushurl", str(self.base / "origin.git"))  # identical push URL is fine
        self.assertEqual(self.publish().json["status"], "pushed")

    def test_publication_writes_only_the_validated_ref(self):
        ref = self.authorized()
        commit = self.commit_report()
        self.receipt(commit)
        self.git("-c", "user.name=Test", "-c", "user.email=t@example.invalid", "tag", "-a", "-m", "local marker", "report-marker", commit)
        self.git("config", "push.followTags", "true")
        self.git("config", "push.recurseSubmodules", "on-demand")
        self.assertEqual(self.publish().json["status"], "pushed")
        self.assertEqual(self.remote_tip(self.branch), commit)
        listing = subprocess.check_output(["git", "-C", str(self.base / "origin.git"), "for-each-ref", "--format=%(refname)"], text=True).split()
        self.assertEqual(listing, [f"refs/heads/{self.branch}"])
        proof = self.report_json()["publication"]
        self.assertEqual(proof["url"], str(self.base / "origin.git"))
        self.verify_report()

    def test_credentials_never_reach_receipts_or_errors(self):
        self.authorized()
        commit = self.commit_report()
        self.receipt(commit)
        self.git("remote", "set-url", "origin", "https://user:s3cret@example.invalid/omg/docs.git")
        result = self.publish(ok=False, extra_env={"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_COUNT": "1",
                                                   "GIT_CONFIG_KEY_0": "http.connectTimeout", "GIT_CONFIG_VALUE_0": "1"})
        self.assertEqual(result.json["reason"], "remote")
        blob = json.dumps(result.json) + (self.root / "report.json").read_text()
        self.assertNotIn("s3cret", blob)
        self.assertIn("https://example.invalid/omg/docs.git", blob)

    def test_malformed_authorized_destination_is_an_error_not_local(self):
        for pr in [False, True]:
            with self.subTest(pr=pr):
                self.setUp()
                ref = self.authorized(pr)
                commit = self.commit_report()
                self.receipt(commit)
                publication = json.loads((self.root / "publication.json").read_text())
                for bad in ["origin/main..backup", "origin", "/master", "origin/", "origin/refs/heads/x", "origin/a b",
                            "origin/-flag", "origin/x.lock", "origin//x", "origin/x/", "origin/x\\y", "", None]:
                    with self.subTest(remote_ref=bad):
                        self.write("publication", {**publication, "remote_ref": bad})
                        stderr = self.verify_report(ok=False).stderr
                        self.assertIn("remote_ref", stderr)
                        self.assertNotIn("stays local", stderr)
                        result = self.publish(ok=False, extra_env={"GIT_SSH_COMMAND": "false"})
                        self.assertIsNone(result.json)  # the plan itself fails; no disposition, no remote access
                        self.assertIn("remote_ref", result.stderr)
                # A finalized receipt whose status contradicts the flags is an error too.
                self.write("publication", {**publication, "status": "local", "remote_ref": None, "pr_url": None})
                self.assertIn("publication receipt", self.verify_report(ok=False).stderr)
                self.write("publication", publication)
                self.verify_report(ok=False)  # still local; needs publish
                self.assertEqual(self.publish().json["status"], "pushed")

    def test_receipt_persistence_failure_is_reported_after_remote_success(self):
        ref = self.authorized()
        assessed = self.head
        commit = self.commit_report()
        before = self.receipt(commit)
        os.chmod(self.root, 0o555)
        try:
            result = self.publish(ok=False)
        finally:
            os.chmod(self.root, 0o755)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual((result.json["status"], result.json["destination"], result.json["commit"], result.json["observed"]),
                         ("receipt_failed", ref, commit, commit))
        self.assertTrue(result.json["error"])
        self.assertEqual(self.remote_tip(self.branch), commit)
        self.assertEqual(self.report_json(), before)  # untouched, still local
        self.assertIn("publish it to", self.verify_report(ok=False).stderr)
        # Rerunning after the blocker clears records the already published report.
        self.assertEqual(self.publish().json, {"status": "pushed", "destination": ref, "commit": commit, "base": commit})
        self.verify_report()
        # A failure that cannot be recorded still reports itself, without a success.
        (self.repo / "app.txt").write_text("more\n")
        self.commit()
        unrelated = self.commit_report(self.report_document(revision=assessed) + "\nRetry.\n")
        self.receipt(unrelated, revision=assessed)
        os.chmod(self.root, 0o555)
        try:
            result = self.publish(ok=False)
        finally:
            os.chmod(self.root, 0o755)
        self.assertEqual((result.returncode, result.json["status"], result.json["reason"]), (1, "failed", "outgoing"))
        self.assertTrue(result.json["receipt_error"])
        self.assertEqual(self.remote_tip(self.branch), commit)

    def test_stale_publication_state_is_normalized_when_authority_lapses(self):
        for stale in [{"status": "pushed", "remote_ref": "origin/master",
                       "publication": {"destination": "origin/master", "base": "0" * 40, "pushed": "1" * 40}},
                      {"status": "failed", "remote_ref": None, "reason": "remote", "error": "old auth failure"}]:
            with self.subTest(stale=stale["status"]):
                self.setUp()
                self.add_remote()
                # The root was canceled after a code push, or the build never authorized publication.
                if stale["status"] == "pushed":
                    self.settle(outcome="canceled", publication={"push": True, "open_pr": False},
                                receipt={"status": "pushed", "remote_ref": "origin/master"})
                else:
                    self.settle()
                commit = self.commit_report()
                before = self.receipt(commit, build_outcome="canceled" if stale["status"] == "pushed" else "pass", **stale)
                self.git("remote", "set-url", "origin", "git@example.invalid:omg/docs.git")
                env = {"GIT_SSH_COMMAND": "false"}
                self.assertIn("stays local", self.verify_report(ok=False).stderr)
                preflight = self.publish("--preflight", extra_env=env).json
                self.assertEqual(preflight, {"status": "preflight", "destination": None, "normalize": True})
                self.assertEqual(self.report_json(), before)  # preflight never writes
                self.assertEqual(self.publish(extra_env=env).json, {"status": "local", "destination": None, "normalized": True})
                receipt = self.report_json()
                self.assertEqual((receipt["status"], receipt["remote_ref"]), ("local", None))
                for key in ["reason", "error", "publication"]:
                    self.assertNotIn(key, receipt)
                for key in ["operation", "workflow", "build_outcome", "revision", "path", "id", "sha256", "commit"]:
                    self.assertEqual(receipt[key], before[key])
                self.verify_report(controller=True)
                # A clean local receipt is left byte-for-byte alone.
                raw = (self.root / "report.json").read_bytes()
                self.assertEqual(self.publish(extra_env=env).json, {"status": "local", "destination": None, "normalized": False})
                self.assertEqual((self.root / "report.json").read_bytes(), raw)

    def test_preflight_failures_never_touch_the_receipt(self):
        ref = self.authorized()
        assessed = self.head
        commit = self.commit_report()
        self.receipt(commit)
        self.assertEqual(self.publish().json["status"], "pushed")
        self.verify_report()
        published = (self.root / "report.json").read_bytes()  # a successful publication receipt
        # 1. Ambiguous push configuration.
        self.git("config", "--add", "remote.origin.pushurl", str(self.base / "other.git"))
        result = self.publish("--preflight", ok=False)
        self.assertEqual((result.json["status"], result.json["reason"]), ("failed", "remote_config"))
        self.assertEqual((self.root / "report.json").read_bytes(), published)
        subprocess.run(["git", "-C", str(self.repo), "config", "--unset-all", "remote.origin.pushurl"])
        # 2. Remote authentication or network unavailable in this session.
        real = self.git("remote", "get-url", "origin")
        self.git("remote", "set-url", "origin", "git@example.invalid:omg/docs.git")
        result = self.publish("--preflight", ok=False, restricted=True, extra_env={"GIT_SSH_COMMAND": "false"})
        self.assertEqual((result.json["status"], result.json["reason"]), ("failed", "remote"))
        self.assertIn("Could not read from remote repository", result.json["error"])
        self.assertEqual((self.root / "report.json").read_bytes(), published)
        self.verify_report(controller=True)  # the published state is still provable offline
        self.git("remote", "set-url", "origin", real)
        # 3. Outgoing history with an unrelated commit below a new report revision.
        (self.repo / "app.txt").write_text("later unpublished code\n")
        self.commit()
        later = self.commit_report(self.report_document(revision=assessed) + "\nRetry.\n")
        before = self.receipt(later, revision=assessed)
        raw = (self.root / "report.json").read_bytes()
        result = self.publish("--preflight", ok=False)
        self.assertEqual((result.json["status"], result.json["reason"]), ("failed", "outgoing"))
        self.assertEqual((self.root / "report.json").read_bytes(), raw)
        self.assertEqual(self.remote_tip(self.branch), commit)
        # The real attempt still records the same blocker durably.
        result = self.publish(ok=False)
        self.assertEqual(result.json["reason"], "outgoing")
        receipt = self.report_json()
        self.assertEqual((receipt["status"], receipt["reason"], receipt["commit"]), ("failed", "outgoing", later))
        self.assertEqual(self.remote_tip(self.branch), commit)

    def test_plan_mode_is_report_only(self):
        self.mixed_contract()
        result = subprocess.run([str(PACK / "assets/scripts/verify.sh"), "--root", str(self.root), "--stage", "finalize", "--plan"],
                                cwd=self.base, env=self.env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--plan", result.stderr)

if __name__ == "__main__":
    unittest.main()
