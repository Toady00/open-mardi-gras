"""Real Git revision checks and deterministic launch/approval failure tests."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


PACK = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("initiative", PACK / "assets/scripts/initiative.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
LiveLedger = m.Ledger


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve()
        m.git(self.repo, "init", "-q")
        self.directory = "docs/initiatives/example"
        self.docs = self.repo / self.directory
        self.docs.mkdir(parents=True)
        for kind in ["discussion", "prd", "hld", "spec"]:
            (self.docs / f"{kind}.md").write_text(
                f"---\nschema_version: 2\nid: {kind}.example\ntype: {kind}\n"
                f"title: Example {kind}\nstatus: draft\nsource: agent\n"
                "scope: platform\nupdated_at: 2026-09-13T00:00:00Z\n---\n\n"
                f"# {kind}\n\nR1: Preserve the requested behavior.\n")
        spec_file = self.docs / "spec.md"
        spec_file.write_text(spec_file.read_text() +
                            '\n```omg-delivery\nversion: 1\nrequirements:\n  R1:\n    kind: implementation\n```\n')
        (self.docs / "direction.json").write_text('{"diagram_type":"workflow","nodes":[]}')
        (self.docs / "direction.html").write_text("<html>exact reviewed rendering</html>")
        self.sha = self.commit()
        self.snap = m.snapshot(str(self.repo), self.directory, self.sha, "docs")
        self.direction = m.snapshot(str(self.repo), self.directory, self.sha, "direction",
                                    [f"{self.directory}/direction.json", f"{self.directory}/direction.html"])
        self.state = dict(schema=1, repo=str(self.repo), rig="app", slug="example",
                          directory=self.directory, phase="refining", directions=[self.direction],
                          direction=self.direction, reviewed=self.snap, reviews={}, operations={})

    def commit(self):
        m.git(self.repo, "add", ".")
        m.git(self.repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
              "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        return m.git(self.repo, "rev-parse", "HEAD").decode().strip()

    def reviews(self):
        for role in ["product", "technical"]:
            artifact = self.repo / f"{role}.review"
            artifact.write_text("R1 checked against direction and code; pass")
            self.state["reviews"][role] = dict(
                artifact=str(artifact), artifact_sha256=m.hashlib.sha256(artifact.read_bytes()).hexdigest(),
                digest=self.snap["digest"], direction=self.direction["digest"], verdict="pass")

class RevisionTests(GitFixture):
    def test_snapshot_requires_unambiguous_delivery_classification(self):
        file = self.docs / "spec.md"
        original = file.read_text()
        for content in [original.split('```omg-delivery')[0],
                        original.replace('kind: implementation', 'kind: imaginary'),
                        original.replace('    kind: implementation', '    kind: implementation\n    kind: development-check')]:
            file.write_text(content)
            sha = self.commit()
            with self.assertRaises(ValueError):
                m.snapshot(str(self.repo), self.directory, sha, "docs")

    def test_reclassifying_requirement_requires_new_approval(self):
        self.state["accepted"] = dict(snapshot=self.snap, direction=self.direction, approval={"evidence": "human"})
        file = self.docs / "spec.md"
        file.write_text(file.read_text().replace('kind: implementation', 'kind: development-check'))
        self.commit()
        with self.assertRaisesRegex(ValueError, "substantively"):
            m.assert_accepted_current(self.state)

    def test_controller_check_executes_without_yq(self):
        self.reviews()
        bin_dir = self.repo / "bin"
        bin_dir.mkdir()
        (bin_dir / "python3").symlink_to(sys.executable)
        (bin_dir / "git").symlink_to(shutil.which("git"))
        gc_stub = bin_dir / "gc"
        gc_stub.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
args = sys.argv[1:]
if args[:2] == ["bd", "show"]:
    print(json.dumps({"id": "check-bead", "metadata": {"omg.binding": "omg", "omg.initiative": "city-123"}}))
elif args[:2] == ["rig", "list"]:
    print(json.dumps({"city_path": os.environ["TEST_REPO"], "city_name": "fixture", "rigs": []}))
elif args[:2] == ["bd", "--city"]:
    print(json.dumps({"id": "city-123", "metadata": {"omg.state": os.environ["TEST_STATE"]}}))
elif args[:2] == ["omg", "initiative"]:
    os.execv(sys.executable, [sys.executable, os.environ["TEST_COMMAND"], *args[2:]])
else:
    sys.exit("unexpected gc call: " + repr(args))
''')
        gc_stub.chmod(0o755)
        baseline = self.commit()  # Keep test executables and review evidence across resets.
        env = {**os.environ, "PATH": str(bin_dir) + ":/usr/bin:/bin", "GC_BEAD_ID": "check-bead",
               "GC_BIN": str(gc_stub), "TEST_STATE": m.encoded(self.state), "TEST_REPO": str(self.repo),
               "TEST_COMMAND": str(PACK / "assets/scripts/initiative.py")}
        self.assertIsNone(shutil.which("yq", path=env["PATH"]))
        script = str(PACK / "assets/scripts/checks/omg-refinement.sh")
        result = subprocess.run([script], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["outcome"], "pass")
        # Committed changes, additions and removals must still invalidate the
        # revision even though the controller no longer reparses frontmatter.
        for change in ["edit", "add", "remove"]:
            with self.subTest(change=change):
                if change == "edit":
                    path = self.docs / "spec.md"
                    path.write_text(path.read_text() + "R2: New scope.\n")
                elif change == "add":
                    (self.docs / "extra.md").write_text("unreviewed document")
                else:
                    (self.docs / "hld.md").unlink()
                self.commit()
                result = subprocess.run([script], env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("revision changed", result.stderr)
                m.git(self.repo, "reset", "--hard", baseline)

    def test_direction_requires_exact_commit_and_render_pair(self):
        for sha, files in [("HEAD", [f"{self.directory}/direction.json"]),
                           (self.sha, [f"{self.directory}/direction.json"]),
                           (self.sha, ["../direction.json"])]:
            with self.subTest(sha=sha, files=files), self.assertRaises(ValueError):
                m.snapshot(str(self.repo), self.directory, sha, "direction", files)

    def test_whole_set_excludes_reports_and_visuals(self):
        reports = self.docs / "reports"
        reports.mkdir()
        (reports / "run.md").write_text("not an authoring input")
        sha = self.commit()
        self.assertEqual(m.snapshot(str(self.repo), self.directory, sha, "docs")["digest"], self.snap["digest"])
        self.assertEqual(len(self.snap["files"]), 4)

    def test_both_reviews_and_unchanged_artifacts_required(self):
        with self.assertRaisesRegex(ValueError, "product"):
            m.validate_reviews(self.state)
        self.reviews()
        m.validate_reviews(self.state)
        Path(self.state["reviews"]["technical"]["artifact"]).write_text("changed")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            m.validate_reviews(self.state)

    def test_substantive_edits_invalidate_readiness_even_when_committed(self):
        self.reviews()
        (self.docs / "spec.md").write_text((self.docs / "spec.md").read_text() + "R2: New scope.\n")
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            m.validate_reviews(self.state)
        self.commit()
        with self.assertRaisesRegex(ValueError, "revision changed"):
            m.validate_reviews(self.state)

    def test_acceptance_status_publication_is_not_new_semantic_scope(self):
        self.state["accepted"] = {"snapshot": self.snap, "approval": {"evidence": "Human approved this revision"}}
        for path in self.docs.glob("*.md"):
            path.write_text(path.read_text().replace("status: draft", "status: accepted")
                            .replace("source: agent", "source: human")
                            .replace("2026-09-13T00:00:00Z", "2026-09-14T00:00:00Z"))
        self.commit()
        m.assert_accepted_current(self.state)
        path = self.docs / "spec.md"
        path.write_text(path.read_text() + "R2: Unapproved behavior.\n")
        self.commit()
        with self.assertRaisesRegex(ValueError, "substantively"):
            m.assert_accepted_current(self.state)

    def test_provenance_changes_require_recorded_human_approval(self):
        path = self.docs / "spec.md"
        original = path.read_text()
        for approval, source, status in [({}, "human", "accepted"),
                                         ({"evidence": "approved"}, "external", "accepted"),
                                         ({"evidence": "approved"}, "human", "draft")]:
            with self.subTest(approval=approval, source=source, status=status):
                self.state["accepted"] = {"snapshot": self.snap, "approval": approval}
                path.write_text(original.replace("source: agent", f"source: {source}")
                                .replace("status: draft", f"status: {status}"))
                self.commit()
                with self.assertRaisesRegex(ValueError, "substantively"):
                    m.assert_accepted_current(self.state)

    def test_materialized_input_is_immutable_and_outside_docs(self):
        root = Path(m.materialize(self.state, self.snap, "city-123"))
        self.assertNotIn(self.repo / "docs", root.parents)
        file = root / self.directory / "spec.md"
        self.assertEqual(file.read_bytes(), (self.docs / "spec.md").read_bytes())
        file.write_text("tampered")
        with self.assertRaisesRegex(ValueError, "modified"):
            m.materialize(self.state, self.snap, "city-123")

    def test_duplicate_ids_and_symlinks_refused(self):
        path = self.docs / "prd.md"
        path.write_text(path.read_text().replace("id: prd.example", "id: spec.example"))
        sha = self.commit()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            m.snapshot(str(self.repo), self.directory, sha, "docs")
        path.write_text(path.read_text().replace("id: spec.example", "id: prd.example"))
        spec_path = self.docs / "spec.md"
        spec_path.unlink()
        spec_path.symlink_to("hld.md")
        sha = self.commit()
        with self.assertRaisesRegex(ValueError, "symlink"):
            m.snapshot(str(self.repo), self.directory, sha, "docs")


class LaunchTests(GitFixture):
    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            m.main(args)

    def setUp(self):
        super().setUp()
        self.reviews()
        self.state["phase"] = "approval-ready"
        owner = self

        class FakeLedger:
            city = str(owner.repo)
            rigs = {"app": str(owner.repo)}

            def __init__(self, city_path=None):
                pass

            def load(self, bead):
                # Real records round-trip through encoded() with sorted keys;
                # insertion order never survives a reload.
                raw = m.encoded(owner.state)
                return json.loads(raw), raw

            def save(self, bead, previous, state):
                if previous != m.encoded(owner.state):
                    raise ValueError("CAS conflict")
                owner.state = copy.deepcopy(state)
                return m.encoded(state)

            def launch_evidence(self, bead, operation, op):
                raise AssertionError("test must supply an explicit launch inventory")

        self.ledger_patch = patch.object(m, "Ledger", FakeLedger)
        self.ledger_patch.start()
        self.addCleanup(self.ledger_patch.stop)

    def test_approval_does_not_launch(self):
        with patch.object(m, "gc") as command:
            self.invoke("accept", "city-123", "--authority", "human approved in session 1")
            command.assert_not_called()
        self.assertEqual(self.state["phase"], "accepted")
        self.assertFalse(self.state["operations"])

    def test_ready_cannot_clear_a_human_decision(self):
        self.invoke("decision", "city-123", "--note", "human must resolve scope")
        with self.assertRaisesRegex(ValueError, "needs-human"):
            self.invoke("check", "city-123")
        with self.assertRaisesRegex(ValueError, "unresolved human"):
            self.invoke("ready", "city-123")
        self.assertEqual(self.state["phase"], "needs-human")

    def failed_start(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        with patch.object(m, "gc", side_effect=[{"id": "app-source"}, ValueError("target missing")]):
            with self.assertRaisesRegex(ValueError, "target missing"):
                self.invoke("start", "city-123", "--authority", "start")
        return next(iter(self.state["operations"]))

    def abandon(self, key):
        self.invoke("abandon", "city-123", "--operation", key, "--authority", "operator request",
                    "--launcher-stopped", "--note", "Launcher exited after target resolution failed")

    def test_abandoned_build_can_restart_and_retry_deduplicates(self):
        key = self.failed_start()
        with patch.object(m.Ledger, "launch_evidence", return_value=[]), patch.object(m, "gc") as command:
            self.abandon(key)
            command.assert_not_called()  # Abandonment itself cannot dispatch.
        self.assertEqual(self.state["operations"][key]["phase"], "abandoned")
        self.assertEqual(self.state["operations"][key]["source"], "app-source")
        with patch.object(m, "gc", side_effect=[{"id": "app-new-source"}, {"workflow_id": "app-new-root"}]) as command:
            self.invoke("start", "city-123", "--authority", "retry after installing roles")
            self.invoke("start", "city-123", "--authority", "same request repeated")
            self.assertEqual(command.call_count, 2)
        self.assertEqual(len(self.state["operations"]), 2)
        new_key = next(k for k in self.state["operations"] if k != key)
        self.assertEqual(self.state["operations"][new_key]["phase"], "launched")

    def test_abandon_requires_authority_and_launcher_quiescence(self):
        key = self.failed_start()
        before = copy.deepcopy(self.state)
        with patch.object(m.Ledger, "launch_evidence") as inventory:
            with self.assertRaisesRegex(ValueError, "explicit instruction"):
                self.invoke("abandon", "city-123", "--operation", key)
            with self.assertRaisesRegex(ValueError, "launcher-stopped"):
                self.invoke("abandon", "city-123", "--operation", key, "--authority", "abandon")
            inventory.assert_not_called()
        self.assertEqual(self.state, before)

    def test_existing_workflow_or_inventory_failure_prevents_abandonment(self):
        key = self.failed_start()
        before = copy.deepcopy(self.state)
        with patch.object(m.Ledger, "launch_evidence", return_value=["app-root"]):
            with self.assertRaisesRegex(ValueError, "workflow evidence"):
                self.abandon(key)
        with patch.object(m.Ledger, "launch_evidence", side_effect=ValueError("store unavailable")):
            with self.assertRaisesRegex(ValueError, "store unavailable"):
                self.abandon(key)
        self.assertEqual(self.state, before)

    def test_concurrent_receipt_prevents_abandonment(self):
        key = self.failed_start()
        def inventory(*args):
            self.state["operations"][key]["phase"] = "launched"
            return []
        with patch.object(m.Ledger, "launch_evidence", side_effect=inventory):
            with self.assertRaisesRegex(ValueError, "CAS conflict"):
                self.abandon(key)
        self.assertEqual(self.state["operations"][key]["phase"], "launched")

    def test_abandoned_authoring_attempt_does_not_block_generation_or_refinement(self):
        for kind in ["generate", "refine"]:
            with self.subTest(kind=kind):
                self.state["operations"] = {"old": dict(kind=kind, phase="launching", rig="app", formula="omg-docs")}
                with patch.object(m.Ledger, "launch_evidence", return_value=[]):
                    self.abandon("old")
                with patch.object(m, "gc", return_value={"workflow_id": "app-root"}) as command:
                    self.invoke(kind, "city-123", "--authority", "retry failed launch")
                    command.assert_called_once()
                self.assertEqual(len(self.state["operations"]), 2)
                with self.assertRaises(ValueError):
                    self.invoke(kind, "city-123", "--authority", "duplicate")

    def test_explicit_request_required_and_repeated_start_deduplicated(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        with self.assertRaisesRegex(ValueError, "explicit instruction"):
            self.invoke("start", "city-123", "--rig", "app")
        calls = []

        def gc(*args):
            calls.append(args)
            self.assertTrue(any(op["phase"] == "launching" for op in self.state["operations"].values()))
            return {"id": "app-source"} if args[0] == "bd" else {"workflow_id": "app-root"}

        with patch.object(m, "gc", gc):
            self.invoke("start", "city-123", "--rig", "app", "--authority", "start build")
            self.invoke("start", "city-123", "--rig", "app", "--authority", "start build")
        self.assertEqual(len(calls), 2)
        self.assertIn("--on", calls[1])
        self.assertIn("omg-build", calls[1])
        self.assertIn("omg.architect", calls[1])
        self.assertFalse(any("requirements_path=" in arg for arg in calls[1]))
        artifact_arg = next(arg for arg in calls[1] if arg.startswith("artifact_root="))
        self.assertTrue(Path(artifact_arg.split("=", 1)[1]).is_absolute())
        baseline = json.loads((Path(artifact_arg.split("=", 1)[1]) / "baseline.json").read_text())
        self.assertEqual(baseline["files"], self.snap["files"])
        self.assertEqual(baseline["revision"], self.sha)

    def test_ambiguous_dispatch_never_automatically_repeated(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        with patch.object(m, "gc", side_effect=[{"id": "app-source"}, ValueError("lost acknowledgement")]):
            with self.assertRaisesRegex(ValueError, "acknowledgement"):
                self.invoke("start", "city-123", "--authority", "start")
        with patch.object(m, "gc") as command:
            self.invoke("start", "city-123", "--authority", "start again")
            command.assert_not_called()
        self.assertEqual(next(iter(self.state["operations"].values()))["phase"], "launching")

    def test_city_initiative_needs_explicit_build_rig(self):
        self.state["rig"] = ""
        self.invoke("accept", "city-123", "--authority", "approved")
        with self.assertRaisesRegex(ValueError, "build rig"):
            self.invoke("start", "city-123", "--authority", "start")

    def test_changed_docs_cannot_start_from_stale_approval(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        path = self.docs / "spec.md"
        path.write_text(path.read_text() + "Unexpected edit")
        self.commit()
        with patch.object(m, "gc") as command:
            with self.assertRaisesRegex(ValueError, "substantively"):
                self.invoke("start", "city-123", "--authority", "start")
            command.assert_not_called()

    def test_failed_intent_persistence_prevents_dispatch(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        with patch.object(m.Ledger, "save", side_effect=ValueError("CAS unavailable")), patch.object(m, "gc") as command:
            with self.assertRaisesRegex(ValueError, "CAS unavailable"):
                self.invoke("start", "city-123", "--authority", "start")
            command.assert_not_called()

    def test_missing_tool_creates_no_launch_intent(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        before = copy.deepcopy(self.state)
        with patch.object(m.shutil, "which", return_value=None), patch.object(m, "gc") as command:
            with self.assertRaisesRegex(ValueError, "requires bash"):
                self.invoke("start", "city-123", "--authority", "start")
            command.assert_not_called()
        self.assertEqual(self.state, before)

    def settled_build(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        with patch.object(m, "gc", side_effect=[{"id": "source-1"}, {"workflow_id": "build-root"}]):
            self.invoke("start", "city-123", "--authority", "build locally")
        key = next(iter(self.state["operations"]))
        self.state["operations"][key].update(phase="settled", workflow="build-root", outcome="fail")
        root = {"id": "build-root", "status": "closed", "metadata": {
            "gc.kind": "workflow", "gc.outcome": "fail", "gc.var.operation": key, "gc.var.initiative": "city-123",
            "gc.formula_name": "omg-build", "gc.root_store_ref": "rig:app"}}
        return key, root

    def test_explicit_failed_build_retry_preserves_old_attempt_and_deduplicates(self):
        key, root = self.settled_build()
        original = copy.deepcopy(self.state["operations"][key])
        with patch.object(m, "gc", side_effect=[root, {"id": "source-2"}, {"workflow_id": "new-root"}, root]) as command:
            self.invoke("start", "city-123", "--retry", key, "--authority", "retry corrected workflow")
            self.invoke("start", "city-123", "--retry", key, "--authority", "same request repeated")
            self.assertEqual(command.call_count, 4)
        self.assertEqual(self.state["operations"][key], original)
        retry = next(op for k, op in self.state["operations"].items() if k != key)
        self.assertEqual(retry["retry_of"], key)
        self.assertNotEqual(retry["artifact_root"], original["artifact_root"])
        self.assertEqual(retry["receipt"]["workflow_id"], "new-root")
        output = io.StringIO()
        with patch.object(m, "gc") as command, contextlib.redirect_stdout(output):
            m.main(["start", "city-123", "--authority", "repeat latest build request"])
        command.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["receipt"]["workflow_id"], "new-root")

    def test_retry_rejects_live_successful_or_wrong_native_root(self):
        key, root = self.settled_build()
        for change, message in [({"status": "open"}, "terminal failed"),
                                ({"metadata": {**root["metadata"], "gc.outcome": "pass"}}, "terminal failed"),
                                ({"metadata": {**root["metadata"], "gc.var.operation": "other"}}, "does not match"),
                                ({"metadata": {**root["metadata"], "gc.formula_name": "omg-work"}}, "does not match"),
                                ({"metadata": {**root["metadata"], "gc.root_store_ref": "rig:other"}}, "does not match"),
                                ({"id": "another-root"}, "does not match")]:
            with patch.object(m, "gc", return_value={**root, **change}), self.assertRaisesRegex(ValueError, message):
                self.invoke("start", "city-123", "--retry", key, "--authority", "retry")
        self.assertEqual(len(self.state["operations"]), 1)
        self.state["operations"][key]["phase"] = "launched"
        with patch.object(m, "gc") as command, self.assertRaisesRegex(ValueError, "settled build"):
            self.invoke("start", "city-123", "--retry", key, "--authority", "retry")
        command.assert_not_called()

    def test_retry_needs_explicit_authority_and_unchanged_approval(self):
        key, _ = self.settled_build()
        with self.assertRaisesRegex(ValueError, "explicit instruction"):
            self.invoke("start", "city-123", "--retry", key)
        self.state["operations"][key]["approved"]["digest"] = "different-approval"
        with patch.object(m, "gc") as command, self.assertRaisesRegex(ValueError, "approved snapshot"):
            self.invoke("start", "city-123", "--retry", key, "--authority", "retry")
        command.assert_not_called()

    def failed_root(self, root, identifier, operation):
        return {**root, "id": identifier, "metadata": {**root["metadata"], "gc.var.operation": operation}}

    def baseline_of(self, op):
        return json.loads((Path(op["artifact_root"]) / "baseline.json").read_text())

    def test_new_start_defaults_to_no_publication(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        with patch.object(m, "gc", side_effect=[{"id": "source-1"}, {"workflow_id": "build-root"}]) as command:
            self.invoke("start", "city-123", "--authority", "build locally")
        op = next(iter(self.state["operations"].values()))
        self.assertEqual(op["publication"], {"push": False, "open_pr": False})
        self.assertEqual(self.baseline_of(op)["publication"], {"push": False, "open_pr": False})
        self.assertIn("push=false", command.call_args_list[1].args)
        self.assertIn("open_pr=false", command.call_args_list[1].args)

    def test_retry_keeps_prior_publication_and_rejects_a_different_one(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        with patch.object(m, "gc", side_effect=[{"id": "source-1"}, {"workflow_id": "build-root"}]):
            self.invoke("start", "city-123", "--authority", "push it", "--push", "true")
        key = next(iter(self.state["operations"]))
        self.state["operations"][key].update(phase="settled", workflow="build-root", outcome="fail")
        root = {"id": "build-root", "status": "closed", "metadata": {
            "gc.kind": "workflow", "gc.outcome": "fail", "gc.var.operation": key, "gc.var.initiative": "city-123",
            "gc.formula_name": "omg-build", "gc.root_store_ref": "rig:app"}}
        # An explicit flag that differs from the settled authorization is a
        # separate request; nothing is read or dispatched.
        for flags in (["--push", "false"], ["--open-pr", "true"], ["--push", "true", "--open-pr", "true"]):
            with self.subTest(flags=flags), patch.object(m, "gc", return_value=root) as command:
                with self.assertRaisesRegex(ValueError, "separate request"):
                    self.invoke("start", "city-123", "--retry", key, "--authority", "retry", *flags)
                command.assert_not_called()
        self.assertEqual(len(self.state["operations"]), 1)
        # Omitted flags keep the prior authorization; an equal explicit flag is accepted.
        with patch.object(m, "gc", side_effect=[root, {"id": "source-2"}, {"workflow_id": "root-2"}]) as command:
            self.invoke("start", "city-123", "--retry", key, "--authority", "retry", "--push", "true")
        retry_key, retry = next((k, op) for k, op in self.state["operations"].items() if k != key)
        self.assertEqual(retry["publication"], {"push": True, "open_pr": False})
        self.assertEqual(self.baseline_of(retry)["publication"], {"push": True, "open_pr": False})
        self.assertIn("push=true", command.call_args_list[2].args)
        self.assertIn("open_pr=false", command.call_args_list[2].args)
        self.state["operations"][retry_key].update(phase="settled", workflow="root-2", outcome="fail")
        root2 = self.failed_root(root, "root-2", retry_key)
        with patch.object(m, "gc", side_effect=[root2, {"id": "source-3"}, {"workflow_id": "root-3"}]) as command:
            self.invoke("start", "city-123", "--retry", retry_key, "--authority", "retry again")
        second = next(op for k, op in self.state["operations"].items() if k not in {key, retry_key})
        self.assertEqual(second["publication"], {"push": True, "open_pr": False})
        self.assertIn("push=true", command.call_args_list[2].args)

    def test_repeated_start_returns_newest_attempt_regardless_of_key_order(self):
        key, root = self.settled_build()
        # Retry keys carry UUIDs; make them sort in the reverse of chronology so
        # neither sorted-key order nor insertion order can pass by accident.
        uuids = [Mock(hex="f" * 32), Mock(hex="0" * 32)]
        with patch.object(m.uuid, "uuid4", side_effect=uuids), \
                patch.object(m, "gc", side_effect=[root, {"id": "source-2"}, {"workflow_id": "root-2"}]):
            self.invoke("start", "city-123", "--retry", key, "--authority", "retry 1")
        first = next(k for k in self.state["operations"] if k != key)
        self.state["operations"][first].update(phase="settled", workflow="root-2", outcome="fail")
        with patch.object(m.uuid, "uuid4", side_effect=uuids[1:]), \
                patch.object(m, "gc", side_effect=[self.failed_root(root, "root-2", first), {"id": "source-3"}, {"workflow_id": "root-3"}]):
            self.invoke("start", "city-123", "--retry", first, "--authority", "retry 2")
        second = next(k for k in self.state["operations"] if k not in {key, first})
        self.assertLess(second, first)
        self.assertEqual(list(json.loads(m.encoded(self.state))["operations"]), [key, second, first])
        for request in (["--authority", "repeat latest build request"],
                        ["--retry", first, "--authority", "retry 2 repeated"]):
            with self.subTest(request=request):
                output = io.StringIO()
                with patch.object(m, "gc", return_value=self.failed_root(root, "root-2", first)), \
                        contextlib.redirect_stdout(output):
                    m.main(["start", "city-123", *request])
                self.assertEqual(json.loads(output.getvalue())["receipt"]["workflow_id"], "root-3")
        self.assertEqual(len(self.state["operations"]), 3)
        # Retrying the superseded attempt returns its existing retry rather
        # than forking the history, and a live newest attempt blocks new ones.
        output = io.StringIO()
        with patch.object(m, "gc", return_value=root), contextlib.redirect_stdout(output):
            m.main(["start", "city-123", "--retry", key, "--authority", "fork"])
        self.assertEqual(json.loads(output.getvalue())["receipt"]["workflow_id"], "root-2")
        self.assertEqual(len(self.state["operations"]), 3)

    def test_forked_retry_history_is_reported_not_guessed(self):
        key, root = self.settled_build()
        template = self.state["operations"][key]
        for suffix in ("a", "b"):
            self.state["operations"][f"{key}-retry-{suffix}"] = {
                **copy.deepcopy(template), "phase": "launched", "retry_of": key,
                "receipt": {"workflow_id": "root-" + suffix}}
        with patch.object(m, "gc") as command, self.assertRaisesRegex(ValueError, "ambiguous"):
            self.invoke("start", "city-123", "--authority", "repeat")
        command.assert_not_called()
        with patch.object(m, "gc", return_value=root), self.assertRaisesRegex(ValueError, "ambiguous"):
            self.invoke("start", "city-123", "--retry", key, "--authority", "retry")
        self.assertEqual(len(self.state["operations"]), 3)

    def test_baseline_is_written_only_after_the_launch_intent_wins_cas(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        owner = self
        key = "build-app-" + self.state["accepted"]["snapshot"]["digest"]
        artifact_root = self.repo / ".omg" / "builds" / "city-123" / key
        winner = copy.deepcopy(self.state)

        def losing_save(bead, previous, state):
            # Another caller recorded the same operation with its own
            # authorization between this caller's read and its CAS.
            winner["operations"][key] = {**copy.deepcopy(state["operations"][key]),
                                         "authority": "winner", "publication": {"push": True, "open_pr": False}}
            owner.state = winner
            raise ValueError("initiative changed concurrently; reread it before retrying")

        with patch.object(m.Ledger, "save", side_effect=losing_save), patch.object(m, "gc") as command:
            with self.assertRaisesRegex(ValueError, "concurrently"):
                self.invoke("start", "city-123", "--authority", "loser")
            command.assert_not_called()
        self.assertFalse((artifact_root / "baseline.json").exists())
        self.assertEqual(self.state["operations"][key]["publication"], {"push": True, "open_pr": False})
        # The winner persists after its CAS; a replay of the same content is a
        # no-op and different content is refused rather than overwritten.
        m.persist_baseline(artifact_root, {"operation": key, "publication": {"push": True, "open_pr": False}})
        m.persist_baseline(artifact_root, {"operation": key, "publication": {"push": True, "open_pr": False}})
        with self.assertRaisesRegex(ValueError, "different baseline"):
            m.persist_baseline(artifact_root, {"operation": key, "publication": {"push": False, "open_pr": False}})
        self.assertEqual(json.loads((artifact_root / "baseline.json").read_text())["publication"],
                         {"push": True, "open_pr": False})
        self.assertEqual([p.name for p in artifact_root.iterdir()], ["baseline.json"])

    def test_baseline_persist_failure_leaves_a_recoverable_launch_intent(self):
        self.invoke("accept", "city-123", "--authority", "approved")
        with patch.object(m, "persist_baseline", side_effect=OSError("disk full")), patch.object(m, "gc") as command:
            with self.assertRaisesRegex(OSError, "disk full"):
                self.invoke("start", "city-123", "--authority", "start")
            command.assert_not_called()
        key, op = next(iter(self.state["operations"].items()))
        self.assertEqual(op["phase"], "launching")
        self.assertNotIn("source", op)
        self.assertFalse((Path(op["artifact_root"]) / "baseline.json").exists())
        with patch.object(m.Ledger, "launch_evidence", return_value=[]):
            self.invoke("abandon", "city-123", "--operation", key, "--launcher-stopped",
                        "--note", "artifact root was not writable", "--authority", "operator")
        self.assertEqual(self.state["operations"][key]["phase"], "abandoned")


class NativeFormulaTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("gc"), "native gc compiler required")
    def test_native_compilation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "omg"
            pack.mkdir()
            for name in ["agents", "assets", "formulas", "template-fragments", "commands", "skills"]:
                (pack / name).symlink_to(PACK / name, target_is_directory=True)
            manifest = json.loads(m.run("yq", "-p=toml", "-o=json", ".", str(PACK / "pack.toml")))
            self.assertFalse(manifest.get("imports"))
            (pack / "pack.toml").write_bytes(m.run("yq", "-p=json", "-o=toml", ".",
                                                 data=json.dumps(manifest).encode()))
            (root / "city.toml").write_text(
                '[workspace]\nname="omg-check"\n'
                f'[imports.omg]\nsource={json.dumps(str(pack))}\n'
                '[[rigs]]\nname="app"\n' + f'path={json.dumps(str(root / "app"))}\n')
            (root / "app").mkdir()
            result = subprocess.run(["gc", "agent", "list", "--city", str(root), "--json"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            names = [agent["qualified_name"] for agent in json.loads(result.stdout)["agents"]]
            self.assertFalse(any(name.startswith("gc.") for name in names))
            self.assertIn("omg.product-manager", names)
            self.assertIn("omg.architect", names)
            for role in ["builder", "tester", "reviewer"]:
                self.assertIn("app/omg." + role, names)
            discovered = subprocess.run(["gc", "--city", str(root), "omg", "verify", "--help"], capture_output=True, text=True)
            self.assertEqual(discovered.returncode, 0, discovered.stderr)
            for formula in ["omg-docs", "omg-refine", "omg-build", "omg-work"]:
                with self.subTest(formula=formula):
                    result = subprocess.run(["gc", "formula", "show", formula,
                                             "--city", str(root), "--json",
                                             "--var", "initiative=city-example",
                                             "--var", "operation=example-run",
                                             "--var", "artifact_root=.omg/build",
                                             "--var", "approved_root=/tmp/approved",
                                             "--var", "approved_revision=" + "a" * 40], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    data = json.loads(result.stdout)
                    self.assertTrue(data["ok"])
                    steps = {s["id"]: s for s in data["steps"]}
                    checks = [s["metadata"]["gc.check_path"] for s in steps.values()
                              if "gc.check_path" in s.get("metadata", {})]
                    self.assertTrue(checks, "expected compiled runtime checks")
                    for check in checks:
                        self.assertTrue(Path(check).is_absolute(), check)
                        self.assertTrue(Path(check).is_file(), check)
                        self.assertTrue(os.access(check, os.X_OK), check)
                    if formula == "omg-work":
                        self.assertEqual(steps["omg-work.work"]["metadata"]["gc.kind"], "ralph")
                        self.assertIn("{{convoy_id}}", steps["omg-work.work"]["metadata"]["omg.convoy"])
                        self.assertEqual(steps["omg-work.work.iteration.1"]["metadata"]["omg.stage"], "work")
                        continue
                    if formula != "omg-build":
                        self.assertIn((PACK / "assets/scripts/checks/omg-refinement.sh").resolve(),
                                      [Path(check).resolve() for check in checks])
                    if formula == "omg-build":
                        report = steps["omg-build.omg-report"]
                        self.assertEqual(report["metadata"]["gc.scope_role"], "teardown")
                        # formula show substitutes display prose but leaves
                        # metadata placeholders for runtime instantiation.
                        self.assertEqual(report["metadata"]["gc.run_target"], "{{omg_binding}}.architect")
                        self.assertEqual(steps["omg-build.implement"]["metadata"]["gc.kind"], "drain")
                        for step, stage in [("plan", "plan"), ("decompose", "decompose"), ("quality", "quality"), ("omg-reconcile", "reconcile")]:
                            subject = steps[f"omg-build.{step}.iteration.1"]["metadata"]
                            self.assertEqual(subject["omg.stage"], stage)
                            self.assertIn("omg.artifact_root", subject)
                        edges = {(d["step_id"], d["depends_on_id"]) for d in data["deps"]}
                        def depends_on(step, dependency):
                            pending, seen = [step], set()
                            while pending:
                                node = pending.pop()
                                if node == dependency:
                                    return True
                                if node not in seen:
                                    seen.add(node)
                                    pending.extend(b for a, b in edges if a == node)
                            return False
                        # The finalization producer is checked and must follow
                        # reconciliation through native scope-check controls.
                        self.assertTrue(depends_on("omg-build.finalize", "omg-build.omg-reconcile"))
                        self.assertTrue(depends_on("omg-build.quality.iteration.1.repair", "omg-build.implement"))
                        self.assertTrue(depends_on("omg-build.omg-reconcile.iteration.1", "omg-build.quality"))
                        self.assertFalse(any("omg-input" in key for key in steps))
                        self.assertFalse(any("gc.build" in json.dumps(s) for s in steps.values()))
                        self.assertFalse(depends_on("omg-build.workflow-finalize", "omg-build.omg-report"))
                    else:
                        self.assertEqual(formula + ".prd" in steps, formula == "omg-docs")
                        for suffix, role in [("review-product", "product-manager"), ("review-technical", "architect")]:
                            matches = [s for key, s in steps.items() if key.endswith("." + suffix)]
                            self.assertEqual(len(matches), 1, list(steps))
                            self.assertEqual(matches[0]["metadata"]["gc.run_target"], "{{omg_binding}}." + role)
                        self.assertEqual(steps[formula + ".refinement"]["metadata"]["gc.kind"], "ralph")


class LaunchInventoryTests(unittest.TestCase):
    def test_inventory_is_uncached_complete_and_includes_closed_or_partial_work(self):
        ledger = LiveLedger.__new__(LiveLedger)
        ledger.city = "/city"
        rows = [{"id": "closed-root", "status": "closed", "metadata": {
                    "gc.var.initiative": "city-123", "gc.var.operation": "attempt"}},
                {"id": "partial", "metadata": {"gc.source_bead_id": "source"}},
                {"id": "unrelated", "metadata": {"gc.var.operation": "other"}}]
        with patch.object(m, "gc", return_value=rows) as command:
            self.assertEqual(ledger.launch_evidence("city-123", "attempt", {"source": "source", "rig": "app"}),
                             ["closed-root", "partial"])
        self.assertIn("--all", command.call_args.args)
        self.assertEqual(command.call_args.args[:5], ("bd", "--city", "/city", "--rig", "app"))
        self.assertIn("--limit", command.call_args.args)
        with patch.object(m, "gc", return_value={"_cache_age_s": 0, "beads": []}):
            with self.assertRaisesRegex(ValueError, "uncached"):
                ledger.launch_evidence("city-123", "attempt", {"rig": "app"})

    def test_city_abandonment_requires_unrelocated_graph_store(self):
        ledger = LiveLedger.__new__(LiveLedger)
        ledger.city = "/city"
        for graph in [None, "work", "infra"]:
            with self.subTest(graph=graph), patch.object(m, "run", side_effect=[b"config", json.dumps(graph).encode()]), patch.object(m, "gc", return_value=[]) as command:
                if graph == "infra":
                    with self.assertRaisesRegex(ValueError, "relocated"):
                        ledger.launch_evidence("city-123", "attempt", {"rig": ""})
                    command.assert_not_called()
                else:
                    self.assertEqual(ledger.launch_evidence("city-123", "attempt", {"rig": ""}), [])
                    self.assertEqual(command.call_args.args[:3], ("bd", "--city", "/city"))


if __name__ == "__main__":
    unittest.main()
