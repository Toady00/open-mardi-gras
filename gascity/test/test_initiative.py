"""Real Git revision checks and deterministic launch/approval failure tests."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


PACK = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("initiative", PACK / "assets/scripts/initiative.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


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
        self.state["accepted"] = {"snapshot": self.snap}
        for path in self.docs.glob("*.md"):
            path.write_text(path.read_text().replace("status: draft", "status: accepted")
                            .replace("2026-09-13T00:00:00Z", "2026-09-14T00:00:00Z"))
        self.commit()
        m.assert_accepted_current(self.state)
        path = self.docs / "spec.md"
        path.write_text(path.read_text() + "R2: Unapproved behavior.\n")
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

            def load(self, bead):
                return copy.deepcopy(owner.state), m.encoded(owner.state)

            def save(self, bead, previous, state):
                if previous != m.encoded(owner.state):
                    raise ValueError("CAS conflict")
                owner.state = copy.deepcopy(state)
                return m.encoded(state)

        self.ledger_patch = patch.object(m, "Ledger", FakeLedger)
        self.ledger_patch.start()
        self.addCleanup(self.ledger_patch.stop)

    def test_approval_does_not_launch(self):
        with patch.object(m, "gc") as command:
            self.invoke("accept", "city-123", "--authority", "human approved in session 1")
            command.assert_not_called()
        self.assertEqual(self.state["phase"], "accepted")
        self.assertFalse(self.state["operations"])

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


class NativeFormulaTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("GC_BASE_PACK") and os.environ.get("HINDSIGHT_PACK"),
                         "set GC_BASE_PACK and HINDSIGHT_PACK to check against native compiler")
    def test_native_compilation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "omg"
            pack.mkdir()
            for name in ["agents", "assets", "formulas", "template-fragments"]:
                (pack / name).symlink_to(PACK / name, target_is_directory=True)
            (pack / "pack.toml").write_text(
                '[pack]\nname="omg"\nschema=2\nversion="0.1.0"\n'
                f'[imports.gc]\nsource={json.dumps(os.environ["GC_BASE_PACK"])}\n'
                f'[imports.hindsight]\nsource={json.dumps(os.environ["HINDSIGHT_PACK"])}\n')
            (root / "city.toml").write_text(
                '[workspace]\nname="omg-check"\n'
                f'[imports.omg]\nsource={json.dumps(str(pack))}\n')
            for formula in ["omg-docs", "omg-refine", "omg-build"]:
                with self.subTest(formula=formula):
                    result = subprocess.run(["gc", "formula", "show", formula,
                                             "--city", str(root), "--json",
                                             "--var", "initiative=city-example",
                                             "--var", "operation=example-run",
                                             "--var", "artifact_root=.omg/build",
                                             "--var", "requirements_path=.omg/build/requirements.md",
                                             "--var", "approved_root=/tmp/approved",
                                             "--var", "approved_revision=" + "a" * 40], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    data = json.loads(result.stdout)
                    self.assertTrue(data["ok"])
                    steps = {s["id"]: s for s in data["steps"]}
                    if formula == "omg-build":
                        report = steps["omg-build.omg-report"]
                        self.assertEqual(report["metadata"]["gc.scope_role"], "teardown")
                        # formula show substitutes display prose but leaves
                        # metadata placeholders for runtime instantiation.
                        self.assertEqual(report["metadata"]["gc.run_target"], "{{omg_binding}}.architect")
                        self.assertEqual(steps["omg-build.implement"]["metadata"]["gc.kind"], "drain")
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
                        self.assertTrue(depends_on("omg-build.finalize.iteration.1", "omg-build.omg-reconcile"))
                        self.assertFalse(depends_on("omg-build.workflow-finalize", "omg-build.omg-report"))
                    else:
                        self.assertEqual(formula + ".prd" in steps, formula == "omg-docs")
                        for suffix, role in [("review-product", "product-manager"), ("review-technical", "architect")]:
                            matches = [s for key, s in steps.items() if key.endswith("." + suffix)]
                            self.assertEqual(len(matches), 1, list(steps))
                            self.assertEqual(matches[0]["metadata"]["gc.run_target"], "{{omg_binding}}." + role)
                        self.assertEqual(steps[formula + ".refinement"]["metadata"]["gc.kind"], "ralph")


if __name__ == "__main__":
    unittest.main()
