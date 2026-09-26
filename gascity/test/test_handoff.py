"""Human interruption, recoverable notification and exact-operation resumption."""
import contextlib
import copy
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from test_initiative import GitFixture, m


class HandoffTests(GitFixture):
    def setUp(self):
        super().setUp()
        self.state["conversation"] = "chat-1"
        self.state["operations"]["run-1"] = dict(kind="refine", phase="launched", rig="app",
                                                 formula="omg-refine", conversation="chat-1")
        self.root = dict(id="root-1", status="in_progress", metadata={
            "gc.kind": "workflow", "gc.formula_name": "omg-refine", "gc.root_store_ref": "rig:app",
            "gc.var.initiative": "city-123", "gc.var.operation": "run-1"})
        self.step = dict(id="step-1", status="in_progress", metadata={
            "gc.root_bead_id": "root-1", "gc.scope_role": "member"})
        self.control = dict(id="check-1", status="open", metadata={
            "gc.root_bead_id": "root-1", "gc.kind": "ralph", "gc.step_id": "refinement", "gc.max_attempts": "3"})
        self.calls = []
        owner = self

        class Ledger:
            city = str(owner.repo)
            rigs = {"app": str(owner.repo)}

            def __init__(self, city_path=None):
                pass

            def load(self, bead):
                return copy.deepcopy(owner.state), m.encoded(owner.state)

            def save(self, bead, previous, state):
                if previous != m.encoded(owner.state):
                    raise ValueError("CAS conflict")
                owner.state = copy.deepcopy(state)
                return m.encoded(state)

        self.ledger = Ledger
        for mocked in [patch.object(m, "Ledger", Ledger), patch.object(m, "gc", side_effect=self.gc),
                       patch.dict(os.environ, {"GC_SESSION_ORIGIN": "", "GC_SESSION_ID": ""})]:
            mocked.start()
            self.addCleanup(mocked.stop)

    def gc(self, *args):
        self.calls.append(args)
        if args[0] == "bd":
            if "query" in args:
                return [self.control]
            if "show" in args:
                return copy.deepcopy(self.root if args[args.index("show") + 1] == "root-1" else self.step)
            if "update" in args:
                target = self.control if args[args.index("update") + 1] == "check-1" else self.step
                for index, value in enumerate(args):
                    if value == "--set-metadata":
                        key, val = args[index + 1].split("=", 1)
                        target["metadata"][key] = val
                return target
            if "close" in args:
                self.step["status"] = "closed"
                return self.step
        if args[:2] in {("mail", "send"), ("session", "nudge")}:
            return {"ok": True, "queued": args[0] == "session"}
        if args[0] == "sling":
            return {"workflow_id": "root-2"}
        raise AssertionError(args)

    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            m.main(args)

    def decision(self):
        self.invoke("decision", "city-123", "--operation", "run-1", "--note",
                    "Who provisions backup? Recommend external activation prerequisite; affects deployment scope.")
        return self.state["pending_decision"]["id"]

    def resolve(self, decision):
        self.invoke("resolve", "city-123", "--decision", decision,
                    "--note", "External activation prerequisite, not part of this implementation.",
                    "--authority", "human message 42")

    def test_decision_notifies_once_and_preserves_original_question(self):
        key = self.decision()
        self.decision()
        self.assertEqual(self.state["pending_decision"]["id"], key)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0][:3], ("mail", "send", "chat-1"))
        self.assertEqual(self.calls[1][:3], ("session", "nudge", "chat-1"))
        self.assertIn("--delivery", self.calls[1])
        self.assertEqual(self.state["operations"]["run-1"]["interruption"]["id"], key)
        self.assertIn("mail", self.state["notifications"][key])
        self.assertIn("nudge", self.state["notifications"][key])

    def test_nudge_failure_is_durable_and_retry_does_not_duplicate_mail(self):
        transport = self.gc
        def fail_nudge(*args):
            if args[:2] == ("session", "nudge"):
                raise ValueError("runtime unavailable")
            return transport(*args)
        with patch.object(m, "gc", side_effect=fail_nudge):
            key = self.decision()
        self.assertEqual(self.state["phase"], "needs-human")
        self.assertIn("mail", self.state["notifications"][key])
        self.assertNotIn("nudge", self.state["notifications"][key])
        self.assertIn("unavailable", self.state["notifications"][key]["error"])
        self.invoke("notify", "city-123")
        self.assertEqual(sum(c[:2] == ("mail", "send") for c in self.calls), 1)
        self.assertIn("nudge", self.state["notifications"][key])

    def test_missing_origin_can_be_repaired_without_relaunch(self):
        self.state.pop("conversation")
        self.state["operations"]["run-1"].pop("conversation")
        key = self.decision()
        self.assertFalse(self.calls)
        self.assertIn("no conversation", self.state["notifications"][key]["error"])
        self.invoke("watch", "city-123", "--notify", "new-chat")
        self.assertEqual(self.state["notifications"][key]["target"], "new-chat")
        self.assertEqual(len(self.calls), 2)

    def test_notification_merge_preserves_concurrent_resolution(self):
        transport = self.gc
        def resolve_during_send(*args):
            result = transport(*args)
            if args[:2] == ("mail", "send"):
                self.state["phase"] = "draft"
                self.state.pop("pending_decision")
                self.state.pop("decision")
            return result
        with patch.object(m, "gc", side_effect=resolve_during_send):
            self.decision_without_readback()
        self.assertEqual(self.state["phase"], "draft")
        self.assertNotIn("decision", self.state)

    def decision_without_readback(self):
        self.invoke("decision", "city-123", "--operation", "run-1", "--note", "Question?")

    def test_resolve_requires_exact_question_and_human_authority(self):
        key = self.decision()
        for args in [("--decision", key, "--note", "answer"),
                     ("--decision", "stale", "--note", "answer", "--authority", "human")]:
            with self.assertRaises(ValueError):
                self.invoke("resolve", "city-123", *args)
        for action in ["revise", "snapshot", "generate", "refine", "start", "direction"]:
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "resolve"):
                self.invoke(action, "city-123", "--authority", "human")
        self.resolve(key)
        self.assertEqual(self.state["phase"], "draft")
        self.assertNotIn("pending_decision", self.state)
        self.assertNotIn("decision", self.state)
        self.assertEqual(self.state["decisions"][0]["id"], key)
        self.assertEqual(self.state["decisions"][0]["authority"]["evidence"], "human message 42")

    def test_old_interrupted_step_cannot_pass_after_human_resolution(self):
        self.resolve(self.decision())
        self.invoke("complete-step", "city-123", "--operation", "run-1", "--step", "step-1")
        self.assertEqual(self.step["status"], "closed")
        self.assertEqual(self.step["metadata"]["gc.outcome"], "fail")
        self.assertEqual(self.step["metadata"]["gc.failure_class"], "hard")
        self.assertEqual(self.step["metadata"]["omg.outcome"], "needs-human")
        self.assertIn("--rig", self.calls[-1])

    def test_complete_step_refuses_control_or_foreign_work(self):
        for key, val in [("gc.kind", "ralph"), ("gc.scope_role", "teardown")]:
            with self.subTest(key=key):
                self.step["metadata"][key] = val
                with self.assertRaisesRegex(ValueError, "ordinary scoped"):
                    self.invoke("complete-step", "city-123", "--operation", "run-1", "--step", "step-1")
                self.step["metadata"].pop(key)
                self.step["metadata"]["gc.scope_role"] = "member"
        self.root["metadata"]["gc.var.initiative"] = "foreign"
        with self.assertRaises(ValueError):
            self.invoke("complete-step", "city-123", "--operation", "run-1", "--step", "step-1")
        self.assertEqual(self.step["status"], "in_progress")

    def test_human_interruption_exhausts_only_its_current_check(self):
        self.decision()
        self.step["metadata"].update({"gc.ralph_step_id": "refinement", "gc.attempt": "2"})
        self.invoke("complete-step", "city-123", "--operation", "run-1", "--step", "step-1")
        self.assertEqual(self.control["metadata"]["gc.max_attempts"], "2")
        self.assertEqual(self.control["status"], "open")  # Only the engine closes controls.
        self.assertEqual(self.step["metadata"]["gc.outcome"], "fail")
        updates = [call for call in self.calls if "update" in call]
        self.assertEqual(updates[0][updates[0].index("update") + 1], "check-1")

    def test_unknown_check_does_not_close_human_blocked_step(self):
        self.decision()
        self.step["metadata"].update({"gc.ralph_step_id": "unknown", "gc.attempt": "1"})
        with self.assertRaisesRegex(ValueError, "enclosing document check"):
            self.invoke("complete-step", "city-123", "--operation", "run-1", "--step", "step-1")
        self.assertEqual(self.step["status"], "in_progress")
        self.assertEqual(self.control["metadata"]["gc.max_attempts"], "3")

    def test_completed_required_review_remains_repairable(self):
        self.state["reviews"]["product"] = {"verdict": "required"}
        self.step["metadata"].update({"gc.ralph_step_id": "refinement", "gc.attempt": "1"})
        self.invoke("complete-step", "city-123", "--operation", "run-1", "--step", "step-1")
        self.assertEqual(self.step["metadata"]["gc.outcome"], "pass")
        self.assertEqual(self.control["metadata"]["gc.max_attempts"], "3")

    def test_native_retry_task_kind_is_still_ordinary_work(self):
        self.step["metadata"]["gc.kind"] = "task"
        self.invoke("complete-step", "city-123", "--operation", "run-1", "--step", "step-1")
        self.assertEqual(self.step["status"], "closed")
        self.assertEqual(self.step["metadata"]["gc.outcome"], "pass")

    def test_human_review_before_snapshot_is_not_a_passing_review(self):
        self.state.pop("reviewed")
        artifact = self.repo / ".omg/question.md"
        artifact.parent.mkdir()
        artifact.write_text("Question and supporting evidence")
        self.invoke("review", "city-123", "--operation", "run-1", "--role", "product",
                    "--verdict", "human", "--artifact", str(artifact), "--note", "Question?")
        self.assertIsNone(self.state["reviews"]["product"]["digest"])
        self.assertEqual(self.state["phase"], "needs-human")
        with self.assertRaises(ValueError):
            self.invoke("ready", "city-123")

    def test_settlement_preserves_new_resolution_and_reports_interruption(self):
        key = self.decision()
        self.resolve(key)
        self.root.update(status="closed")
        self.root["metadata"]["gc.outcome"] = "fail"
        self.invoke("settle", "city-123", "--operation", "run-1", "--workflow", "root-1")
        op = self.state["operations"]["run-1"]
        self.assertEqual(op["result"], "needs-human")
        self.assertEqual(op["outcome"], "fail")
        self.assertEqual(self.state["phase"], "draft")
        self.assertNotIn("decision", self.state)
        self.assertIn("nudge", self.state["notifications"]["settled-run-1"])

    def test_engine_pass_with_missing_reviews_is_not_approval_ready(self):
        self.root.update(status="closed")
        self.root["metadata"]["gc.outcome"] = "pass"
        self.invoke("settle", "city-123", "--operation", "run-1", "--workflow", "root-1")
        self.assertEqual(self.state["operations"]["run-1"]["result"], "incomplete")

    def test_matching_reviews_produce_approval_ready_result(self):
        self.reviews()
        self.state.update(phase="approval-ready", reviewed_operation="run-1")
        self.root.update(status="closed")
        self.root["metadata"]["gc.outcome"] = "pass"
        self.invoke("settle", "city-123", "--operation", "run-1", "--workflow", "root-1")
        self.assertEqual(self.state["operations"]["run-1"]["result"], "approval-ready")

    def build_operation(self):
        self.state["operations"]["build-1"] = dict(
            kind="start", phase="launched", rig="app", formula="omg-build",
            receipt={"workflow_id": "root-b"}, publication={"push": False, "open_pr": False})
        run = {"gc.var.initiative": "city-123", "gc.var.operation": "build-1", "gc.root_store_ref": "rig:app"}
        beads = {
            "root-b": dict(id="root-b", status="closed", metadata={
                **run, "gc.kind": "workflow", "gc.formula_name": "omg-build", "gc.outcome": "pass"}),
            # An omg-work item root inside the build carries the same
            # initiative/operation variables and also closes with a pass.
            "item-1": dict(id="item-1", status="closed", metadata={
                **run, "gc.kind": "workflow", "gc.formula_name": "omg-work", "gc.outcome": "pass"}),
            "root-x": dict(id="root-x", status="closed", metadata={
                **run, "gc.kind": "workflow", "gc.formula_name": "omg-build", "gc.outcome": "pass"}),
            "drain-1": dict(id="drain-1", status="closed", metadata={
                **run, "gc.kind": "drain", "gc.outcome": "pass"}),
            "root-other-store": dict(id="root-other-store", status="closed", metadata={
                **run, "gc.kind": "workflow", "gc.formula_name": "omg-build", "gc.outcome": "pass",
                "gc.root_store_ref": "rig:other"})}

        def gc(*args):
            self.calls.append(args)
            if args[0] == "bd" and "show" in args:
                return copy.deepcopy(beads[args[args.index("show") + 1]])
            return self.gc(*args)

        patcher = patch.object(m, "gc", side_effect=gc)
        patcher.start()
        self.addCleanup(patcher.stop)
        return beads

    def test_settle_accepts_only_the_recorded_build_root(self):
        self.build_operation()
        for workflow in ("item-1", "root-x", "drain-1", "root-other-store"):
            with self.subTest(workflow=workflow), self.assertRaisesRegex(ValueError, "does not match"):
                self.invoke("settle", "city-123", "--operation", "build-1", "--workflow", workflow)
            self.assertNotIn("result", self.state["operations"]["build-1"])
            self.assertEqual(self.state["operations"]["build-1"]["phase"], "launched")
        self.assertNotIn("settled-build-1", self.state.get("notifications", {}))
        self.invoke("settle", "city-123", "--operation", "build-1", "--workflow", "root-b")
        op = self.state["operations"]["build-1"]
        self.assertEqual((op["phase"], op["workflow"], op["result"]), ("settled", "root-b", "development-verified"))
        self.assertIn("--rig", self.calls[0])
        self.assertIn("app", self.calls[0])

    def test_settled_operation_rejects_a_second_settlement_with_another_root(self):
        beads = self.build_operation()
        beads["root-b"]["metadata"]["gc.outcome"] = "fail"
        self.invoke("settle", "city-123", "--operation", "build-1", "--workflow", "root-b")
        self.assertEqual(self.state["operations"]["build-1"]["result"], "failed")
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.invoke("settle", "city-123", "--operation", "build-1", "--workflow", "root-x")
        beads["root-b"]["metadata"]["gc.outcome"] = "pass"
        self.invoke("settle", "city-123", "--operation", "build-1", "--workflow", "root-b")
        self.assertEqual(self.state["operations"]["build-1"]["result"], "failed")

    def test_unrecorded_launch_settles_only_a_matching_root_and_open_roots_wait(self):
        beads = self.build_operation()
        del self.state["operations"]["build-1"]["receipt"]
        self.state["operations"]["build-1"]["phase"] = "launching"
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.invoke("settle", "city-123", "--operation", "build-1", "--workflow", "item-1")
        beads["root-b"]["status"] = "in_progress"
        with self.assertRaisesRegex(ValueError, "has not settled"):
            self.invoke("settle", "city-123", "--operation", "build-1", "--workflow", "root-b")
        self.assertEqual(self.state["operations"]["build-1"]["phase"], "launching")

    def test_recover_rejects_nested_or_foreign_roots(self):
        self.build_operation()
        del self.state["operations"]["build-1"]["receipt"]
        self.state["operations"]["build-1"]["phase"] = "launching"
        for workflow in ("item-1", "drain-1", "root-other-store"):
            with self.subTest(workflow=workflow), self.assertRaisesRegex(ValueError, "does not match"):
                self.invoke("recover", "city-123", "--operation", "build-1", "--workflow", workflow,
                            "--authority", "operator inspected native state")
            self.assertEqual(self.state["operations"]["build-1"]["phase"], "launching")
        self.invoke("recover", "city-123", "--operation", "build-1", "--workflow", "root-b",
                    "--authority", "operator inspected native state")
        self.assertEqual(self.state["operations"]["build-1"]["receipt"], {"workflow_id": "root-b"})
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.invoke("recover", "city-123", "--operation", "build-1", "--workflow", "root-x",
                        "--authority", "operator inspected native state")

    def test_refine_reenters_missing_authoring_and_keeps_return_address(self):
        self.state["operations"]["run-1"]["phase"] = "settled"
        (self.docs / "hld.md").unlink()
        with patch.dict(os.environ, {"GC_SESSION_ORIGIN": "ephemeral", "GC_SESSION_ID": "worker-9"}):
            self.invoke("refine", "city-123", "--authority", "human continuation")
        launched = next(op for key, op in self.state["operations"].items() if key != "run-1")
        self.assertEqual(launched["conversation"], "chat-1")
        self.assertTrue(launched["initial"])
        self.assertIn("initial=true", self.calls[-1])
        self.assertTrue((self.docs / "prd.md").exists())

    def test_full_document_set_refines_without_repeating_generation(self):
        self.state["operations"]["run-1"]["phase"] = "settled"
        with patch.dict(os.environ, {"GC_SESSION_ORIGIN": "manual", "GC_SESSION_ID": "chat-2"}):
            self.invoke("refine", "city-123", "--authority", "human refinement")
        self.assertIn("initial=false", self.calls[-1])
        self.assertEqual(self.state["conversation"], "chat-2")

    def test_named_conversation_is_a_valid_return_address(self):
        self.state["operations"]["run-1"]["phase"] = "settled"
        with patch.dict(os.environ, {"GC_SESSION_ORIGIN": "named", "GC_SESSION_ID": "named-chat"}):
            self.invoke("refine", "city-123", "--authority", "human refinement")
        self.assertEqual(self.state["conversation"], "named-chat")

    def test_early_worker_decision_survives_launch_receipt_merge(self):
        self.state["operations"]["run-1"]["phase"] = "settled"
        def decide_before_receipt(*args):
            if args[0] == "sling":
                key = next(k for k in self.state["operations"] if k != "run-1")
                self.state["operations"][key]["interruption"] = {"id": "early", "note": "question"}
                return {"workflow_id": "root-2"}
            return self.gc(*args)
        with patch.object(m, "gc", side_effect=decide_before_receipt):
            self.invoke("refine", "city-123", "--authority", "human")
        op = next(op for key, op in self.state["operations"].items() if key != "run-1")
        self.assertEqual(op["interruption"]["id"], "early")
        self.assertEqual(op["phase"], "launched")


if __name__ == "__main__":
    unittest.main()
