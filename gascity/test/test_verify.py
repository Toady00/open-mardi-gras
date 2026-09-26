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
            env["GC_BEAD_ID"] = "work-check" if stage == "work" else "check"
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


if __name__ == "__main__":
    unittest.main()
