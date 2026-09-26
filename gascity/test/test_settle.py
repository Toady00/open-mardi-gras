"""Settlement tests use in-memory gc state; no live verifier or backend calls."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:
    Draft202012Validator = None

SCRIPTS = Path(__file__).resolve().parents[1] / "assets/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("settle", SCRIPTS / "settle.py")
SETTLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SETTLE)


class Fake(SETTLE.Transport):
    def __init__(self, root):
        super().__init__(str(root / "city"), "rig")
        self.root = root
        self.supported = True
        self.quality_calls = 0
        self.quality_failure = False
        self.fail_item = None
        self.race_item = None
        self.reread_race = None
        self.reads = {}
        self.updates = []
        self.beads = {}
        self.units = {}
        self.calls = []
        self.rig_list = {"schema_version": "1", "city_path": str(root / "city"),
                         "city_name": "testcity", "rigs": [
                             {"name": "testcity", "path": str(root / "city"), "prefix": "city",
                              "hq": True, "suspended": False, "running": False, "beads": "ok"},
                             {"name": "rig", "path": str(root / "repo"), "prefix": "app",
                              "hq": False, "suspended": False, "running": False, "beads": "ok"}],
                         "summary": {"total": 2, "suspended": 0, "running": 0}}

    def capable(self):
        return self.supported

    def quality(self, root):
        assert root == self.root
        self.quality_calls += 1
        if self.quality_failure:
            raise ValueError("quality failed")

    def call(self, *args, rig=True):
        self.calls.append(args)
        if args == ("rig", "list"):
            # gc resolves --rig by registered name only; a listing read before
            # the rig is validated must be city-scoped.
            assert rig is False, "rig list must be read city-scoped"
            return copy.deepcopy(self.rig_list)
        assert rig, "bead and convoy commands need the bound rig context"
        if args[:2] == ("bd", "list"):
            return copy.deepcopy(list(self.beads.values()))
        if args[:2] == ("convoy", "status"):
            return {"convoy": {"id": args[2]}, "children": [{"id": self.units[args[2]]}]}
        if args[:2] == ("bd", "show"):
            identifier = args[2]
            self.reads[identifier] = self.reads.get(identifier, 0) + 1
            if identifier == self.reread_race and self.reads[identifier] == 2:
                self.beads[identifier]["metadata"]["gc.exclusive_drain_reservation"] = "other-drain"
                self.beads[identifier]["revision"] += 1
            return copy.deepcopy(self.beads[identifier])
        if args[:2] == ("bd", "update"):
            self.updates.append(args)
            identifier = args[2]
            bead = self.beads[identifier]
            if identifier == self.fail_item:
                raise ValueError("injected backend failure")
            if identifier == self.race_item:
                bead["metadata"]["gc.exclusive_drain_reservation"] = "other-drain"
                bead["revision"] += 1
            if bead["revision"] != int(args[args.index("--if-revision") + 1]):
                raise ValueError("precondition-failed")
            assert args[args.index("--status") + 1] == "closed"
            assert "reviewed_revision=" + "a" * 40 in args[args.index("--append-notes") + 1]
            for index, arg in enumerate(args):
                if arg == "--set-metadata":
                    key, value = args[index + 1].split("=", 1)
                    bead["metadata"][key] = value
            bead["status"] = "closed"
            bead["revision"] += 1
            return copy.deepcopy(bead)
        raise AssertionError(args)


class SettlementTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "city").mkdir()
        (self.root / "repo").mkdir()
        self.fake = Fake(self.root)
        self.write("baseline", {"operation": "op", "initiative": "initiative",
                                "city": str(self.root / "city"), "repo": str(self.root / "repo")})
        self.write("decomposition", {"workflow": "workflow", "convoy": "convoy",
                                     "items": [{"id": "s1"}, {"id": "s2"}]})
        self.write("review", {"revision": "a" * 40})
        run = {"gc.var.operation": "op", "gc.var.initiative": "initiative"}
        self.fake.beads["workflow"] = {"id": "workflow", "metadata": {
            **run, "gc.kind": "workflow", "gc.formula_name": "omg-build",
            "gc.formula_contract": "graph.v2", "gc.input_convoy_id": "convoy"}}
        rows = []
        for index in range(2):
            source, item, unit = f"s{index + 1}", f"item{index + 1}", f"unit{index + 1}"
            self.fake.units[unit] = source
            self.fake.beads[source] = {"id": source, "issue_type": "task", "revision": 7, "status": "open",
                "metadata": {"omg.artifact_root": str(self.root), "omg.operation": "op"},
                "dependencies": [] if index == 0 else [{"id": "s1", "dependency_type": "blocks"}]}
            self.fake.beads[item] = {"id": item, "status": "closed", "metadata": {
                **run, "gc.kind": "workflow", "gc.formula_name": "omg-work",
                "gc.formula_contract": "graph.v2", "gc.outcome": "pass",
                "gc.drain_control_id": "drain", "gc.drain_member_id": source,
                "gc.input_convoy_id": unit, "gc.item_root_key": item + "-key",
                "gc.drain_index": str(index), "gc.drain_count": "2"}}
            finalizer = item + "-final"
            self.fake.beads[finalizer] = {"id": finalizer, "status": "closed", "metadata": {
                "gc.root_bead_id": item, "gc.kind": "workflow-finalize", "gc.outcome": "pass",
                "gc.step_id": "omg-work.workflow-finalize", "gc.step_ref": "omg-work.workflow-finalize"}}
            rows.append({"index": index, "member_id": source, "unit_key": unit + "-key",
                         "unit_convoy_id": unit, "item_root_id": item, "item_root_key": item + "-key",
                         "outcome_bead_id": item, "status": "succeeded", "outcome_kind": "pass"})
        self.manifest = {"version": 1, "context": "shared", "parent_convoy_id": "convoy",
                         "formula": "omg-work", "rows": list(reversed(rows))}
        self.fake.beads["drain"] = {"id": "drain", "status": "closed", "metadata": {
            "gc.root_bead_id": "workflow", "gc.kind": "drain", "gc.step_id": "omg-build.implement",
            "gc.step_ref": "omg-build.implement", "gc.drain_parent_convoy_id": "convoy",
            "gc.drain_formula": "omg-work", "gc.drain_context": "shared",
            "gc.drain_state": "succeeded", "gc.outcome": "pass",
            "gc.drain_manifest.v1": json.dumps(self.manifest)}}

    def write(self, name, value):
        (self.root / f"{name}.json").write_text(json.dumps(value))

    def settle(self, apply=False):
        return SETTLE.settle(self.root, self.fake, apply)

    def receipt(self):
        return json.loads((self.root / "settlement.json").read_text())

    def test_named_rig_binds_registered_name_and_canonical_city(self):
        self.assertEqual(self.settle()[1], 0)
        self.assertEqual(self.fake.calls[0], ("rig", "list"))
        self.assertEqual(self.fake.context_values(), (str(self.root / "city"), "rig"))
        self.assertEqual(self.fake.context, ["--city", str(self.root / "city"), "--rig", "rig"])

    def test_absolute_rig_path_resolves_to_registered_name(self):
        # gc bd --rig accepts only registered names (rigByName), so the bound
        # context must carry the name even when the caller supplied the path.
        (self.root / "city-link").symlink_to(self.root / "city", target_is_directory=True)
        (self.root / "repo-link").symlink_to(self.root / "repo", target_is_directory=True)
        self.fake.context = ["--city", str(self.root / "city-link"),
                             "--rig", str(self.root / "repo-link")]
        self.assertEqual(self.settle()[1], 0)
        self.assertEqual(self.fake.calls[0], ("rig", "list"))
        self.assertEqual(self.fake.context_values(), (str(self.root / "city"), "rig"))
        for call in self.fake.calls:
            self.assertNotIn(str(self.root / "repo-link"), call)

    def test_registered_name_spelling_is_retained_for_a_path_caller(self):
        self.fake.rig_list["rigs"][1]["name"] = "App_Rig"
        self.fake.context[3] = str(self.root / "repo")
        self.assertEqual(self.settle()[1], 0)
        self.assertEqual(self.fake.context_values(), (str(self.root / "city"), "App_Rig"))

    def test_wrong_city_rejected_before_any_gc_call(self):
        self.fake.context[1] = str(self.root / "repo")
        with self.assertRaisesRegex(ValueError, "caller city differs"):
            self.settle(True)
        self.assertFalse(self.fake.calls)
        self.assertEqual(self.fake.quality_calls, 0)
        self.assertFalse(self.fake.updates)

    def test_wrong_named_rig_rejected_before_quality_or_bead_reads(self):
        self.fake.rig_list["rigs"][1]["path"] = str(self.root / "city")
        with self.assertRaisesRegex(ValueError, "caller rig differs"):
            self.settle(True)
        self.assertEqual(self.fake.calls, [("rig", "list")])
        self.assertEqual(self.fake.quality_calls, 0)
        self.assertFalse(self.fake.updates)

    def test_absolute_path_must_match_exactly_one_registered_rig(self):
        (self.root / "elsewhere").mkdir()
        original = copy.deepcopy(self.fake.rig_list)
        unregistered = str(self.root / "elsewhere")
        duplicate = {**original, "rigs": original["rigs"] + [{**original["rigs"][1], "name": "twin"}]}
        hq_only = {**original, "rigs": [{**original["rigs"][1], "hq": True}]}
        for path, listing, message in [(unregistered, original, "exactly one registered rig"),
                                       (str(self.root / "repo"), duplicate, "exactly one registered rig"),
                                       (str(self.root / "repo"), hq_only, "exactly one registered rig"),
                                       (str(self.root / "city"), original, "exactly one registered rig")]:
            with self.subTest(path=path, rigs=[rig["name"] for rig in listing["rigs"]]):
                self.fake.rig_list = copy.deepcopy(listing)
                self.fake.context = ["--city", str(self.root / "city"), "--rig", path]
                with self.assertRaisesRegex(ValueError, message):
                    self.settle(True)
                self.assertEqual(self.fake.calls[-1], ("rig", "list"))
                self.assertEqual(self.fake.quality_calls, 0)
                self.assertFalse(self.fake.reads)

    def test_registered_rig_path_differing_from_baseline_repo_is_rejected(self):
        (self.root / "other").mkdir()
        self.fake.rig_list["rigs"][1]["path"] = str(self.root / "other")
        self.fake.context[3] = str(self.root / "other")
        with self.assertRaisesRegex(ValueError, "caller rig differs"):
            self.settle(True)
        self.assertEqual(self.fake.quality_calls, 0)

    def test_missing_checkout_of_another_rig_does_not_block_path_binding(self):
        self.fake.rig_list["rigs"].append({"name": "gone", "path": str(self.root / "missing"), "hq": False})
        self.fake.context[3] = str(self.root / "repo")
        self.assertEqual(self.settle()[1], 0)
        self.assertEqual(self.fake.context_values(), (str(self.root / "city"), "rig"))

    def test_rig_lookup_rejects_wrong_city_unknown_duplicate_and_relative_path(self):
        original = copy.deepcopy(self.fake.rig_list)
        variants = [None, [], {**original, "city_path": str(self.root / "repo")},
                    {**original, "rigs": []},
                    {**original, "rigs": [original["rigs"][1]] * 2},
                    {**original, "rigs": [{"name": "rig", "path": "../repo"}]}]
        for listing in variants:
            with self.subTest(listing=listing):
                self.fake.rig_list = listing
                with self.assertRaises(ValueError):
                    self.settle(True)
                self.assertEqual(self.fake.quality_calls, 0)
                self.assertFalse(self.fake.reads)
                self.assertFalse(self.fake.updates)

    def test_relative_caller_city_and_rig_paths_do_not_use_cwd(self):
        for city, rig in ((".", "rig"), (str(self.root / "city"), "../repo")):
            self.fake.context = ["--city", city, "--rig", rig]
            with self.assertRaises(ValueError):
                self.settle(True)
            self.assertFalse(self.fake.calls)
            self.assertEqual(self.fake.quality_calls, 0)

    def test_preview_sorted_read_only_and_deterministic(self):
        self.fake.supported = False
        del self.fake.beads["s1"]["revision"]
        first, code = self.settle()
        self.assertEqual(code, 0)
        self.assertEqual(first, self.settle()[0])
        self.assertEqual([i["source"] for i in first["items"]], ["s1", "s2"])
        self.assertEqual(self.fake.quality_calls, 2)
        self.assertFalse(self.fake.updates)
        self.assertFalse((self.root / "settlement.json").exists())

    def test_apply_then_idempotent(self):
        receipt, code = self.settle(True)
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "settled")
        self.assertEqual(receipt["revision"], "a" * 40)
        self.assertEqual(self.fake.quality_calls, 2)
        self.assertEqual([args[2] for args in self.fake.updates], ["s1", "s2"])
        self.assertEqual(self.receipt(), receipt)
        receipt, code = self.settle(True)
        self.assertEqual(code, 0)
        self.assertEqual([i["status"] for i in receipt["items"]], ["already-settled"] * 2)
        self.assertEqual(len(self.fake.updates), 2)
        self.assertFalse(list(self.root.glob(".settlement-*")))

    def test_partial_failure_resume(self):
        self.fake.fail_item = "s2"
        receipt, code = self.settle(True)
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual([i["status"] for i in receipt["items"]], ["closed", "failed"])
        self.assertEqual(self.receipt(), receipt)
        self.fake.fail_item = None
        receipt, code = self.settle(True)
        self.assertEqual(code, 0)
        self.assertEqual([i["status"] for i in receipt["items"]], ["already-settled", "closed"])
        self.assertEqual([args[2] for args in self.fake.updates], ["s1", "s2", "s2"])

    def test_cas_reservation_race_stops_without_retry(self):
        self.fake.race_item = "s1"
        receipt, code = self.settle(True)
        self.assertEqual(code, 1)
        self.assertIn("precondition-failed", receipt["error"])
        self.assertEqual(len(self.fake.updates), 1)
        self.assertEqual(self.fake.beads["s1"]["status"], "open")
        self.assertEqual(self.fake.beads["s2"]["status"], "open")
        self.assertEqual(self.receipt()["status"], "failed")

    def test_reread_reservation_race(self):
        self.fake.reread_race = "s1"
        receipt, code = self.settle(True)
        self.assertEqual(code, 1)
        self.assertIn("reservation", receipt["error"])
        self.assertFalse(self.fake.updates)

    def test_reread_revision_change_is_not_retried(self):
        call = self.fake.call

        def changed(*args, **kwargs):
            result = call(*args, **kwargs)
            if args == ("bd", "show", "s1") and self.fake.reads["s1"] == 2:
                result["revision"] += 1
            return result

        self.fake.call = changed
        receipt, code = self.settle(True)
        self.assertEqual(code, 1)
        self.assertIn("changed since validation", receipt["error"])
        self.assertFalse(self.fake.updates)

    def test_expanded_dependency_status_can_change_during_apply(self):
        call = self.fake.call

        def expanded(*args, **kwargs):
            result = call(*args, **kwargs)
            if args == ("bd", "show", "s2"):
                result["dependencies"][0]["status"] = self.fake.beads["s1"]["status"]
            return result

        self.fake.call = expanded
        self.assertEqual(self.settle(True)[1], 0)

    def test_missing_capability(self):
        self.fake.supported = False
        with self.assertRaisesRegex(SETTLE.Unsupported, "does not advertise"):
            self.settle(True)
        self.assertFalse(self.fake.updates)
        self.assertFalse((self.root / "settlement.json").exists())

    def test_revision_required_for_every_source_before_writes(self):
        for value in (None, "7", True, -(2 ** 63) - 1, 2 ** 63):
            with self.subTest(value=value):
                self.fake.beads["s2"]["revision"] = value
                with self.assertRaises(SETTLE.Unsupported):
                    self.settle(True)
                self.assertFalse(self.fake.updates)

    def test_opaque_signed_revisions_preserved_in_cas_and_receipt(self):
        for revision in (-6341175321048868863, -(2 ** 63), -1, 0, 2 ** 63 - 1):
            with self.subTest(revision=revision):
                # Restore only the source tasks between independent applications.
                for source in ("s1", "s2"):
                    bead = self.fake.beads[source]
                    bead["status"] = "open"
                    bead["revision"] = revision
                    bead["metadata"] = {"omg.artifact_root": str(self.root), "omg.operation": "op"}
                self.fake.updates.clear()
                receipt, code = self.settle(True)
                self.assertEqual(code, 0)
                for args in self.fake.updates:
                    self.assertEqual(args[args.index("--if-revision") + 1], str(revision))
                self.assertEqual([i["source_revision"] for i in receipt["items"]], [revision] * 2)
                self.assertEqual(self.receipt(), receipt)

    def external_dependency(self, status="open"):
        self.fake.beads["external"] = {"id": "external", "status": status}
        self.fake.beads["s2"]["dependencies"].append(
            {"issue_id": "s2", "depends_on_id": "external", "type": "blocks"})

    def test_external_unresolved_blocker_prevents_entire_batch(self):
        self.external_dependency()
        for status in ("open", "in_progress", "blocked", "deferred", "unknown"):
            with self.subTest(status=status):
                self.fake.beads["external"]["status"] = status
                with self.assertRaisesRegex(ValueError, "unresolved blocking dependency external"):
                    self.settle(True)
                self.assertFalse(self.fake.updates)
                self.assertFalse((self.root / "settlement.json").exists())

    def test_external_closed_blocker_allows_apply(self):
        self.external_dependency("closed")
        self.assertEqual(self.settle(True)[1], 0)
        self.assertEqual(self.fake.reads["external"], 2)

    def test_external_blocker_reopened_before_item_is_reread(self):
        self.external_dependency("closed")
        call = self.fake.call

        def reopened(*args, **kwargs):
            if args == ("bd", "show", "external") and self.fake.reads.get("external") == 1:
                self.fake.beads["external"]["status"] = "open"
            return call(*args, **kwargs)

        self.fake.call = reopened
        receipt, code = self.settle(True)
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual([args[2] for args in self.fake.updates], ["s1"])
        self.assertEqual(self.fake.beads["s2"]["status"], "open")

    def test_unsupported_dependency_gates_prevent_entire_batch(self):
        for kind in ("waits-for", "conditional-blocks", "parent-child", "future-gate"):
            with self.subTest(kind=kind):
                self.fake.beads["s2"]["dependencies"] = [{"id": "s1", "dependency_type": kind}]
                with self.assertRaisesRegex(SETTLE.Unsupported, "unsupported dependency gate"):
                    self.settle(True)
                self.assertFalse(self.fake.updates)

    def test_dependency_owned_by_another_source_is_rejected(self):
        self.fake.beads["s2"]["dependencies"] = [
            {"issue_id": "other", "depends_on_id": "s1", "type": "blocks"}]
        with self.assertRaisesRegex(ValueError, "dependency belongs to another source"):
            self.settle(True)
        self.assertFalse(self.fake.updates)

    def test_sources_must_be_plain_tasks(self):
        for issue_type in (None, "epic", "feature", "bug"):
            with self.subTest(issue_type=issue_type):
                self.fake.beads["s2"]["issue_type"] = issue_type
                with self.assertRaisesRegex(ValueError, "plain task source"):
                    self.settle(True)
                self.assertFalse(self.fake.updates)
        del self.fake.beads["s2"]["issue_type"]
        self.fake.beads["s2"]["type"] = "task"
        self.assertEqual(self.settle()[1], 0)

    def test_all_source_ownership_and_status_validated_before_writes(self):
        original = copy.deepcopy(self.fake.beads["s2"])
        variants = [{"status": "closed"}, {"status": "in_progress"}, {"assignee": "worker"}]
        variants += [{"metadata": {**original["metadata"], key: value}} for key, value in (
            ("omg.operation", "other"), ("omg.artifact_root", "/other"), ("gc.kind", "workflow"),
            ("gc.exclusive_drain_reservation", "reserved"), ("omg.settled_by", "other"))]
        for variant in variants:
            with self.subTest(variant=variant):
                self.fake.beads["s2"] = {**original, **variant}
                with self.assertRaises(ValueError):
                    self.settle(True)
                self.assertFalse(self.fake.updates)

    def test_closed_binding_must_match_all_fields(self):
        self.settle(True)
        for key in ("omg.settled_by", "omg.item_root", "omg.settled_drain"):
            old = self.fake.beads["s2"]["metadata"][key]
            self.fake.beads["s2"]["metadata"][key] = "other"
            with self.assertRaisesRegex(ValueError, "another settlement"):
                self.settle()
            self.fake.beads["s2"]["metadata"][key] = old

    def test_bad_dependency_order_rejected(self):
        self.fake.beads["s1"]["dependencies"] = [{"depends_on_id": "s2", "type": "blocks"}]
        with self.assertRaisesRegex(ValueError, "manifest order"):
            self.settle(True)
        self.assertFalse(self.fake.updates)

    def test_quality_failure_blocks_preview(self):
        self.fake.quality_failure = True
        with self.assertRaisesRegex(ValueError, "quality failed"):
            self.settle()
        self.assertFalse(self.fake.updates)

    def test_real_execution_helper_rejects_unfinished_finalizer(self):
        self.fake.beads["item2-final"]["status"] = "open"
        with self.assertRaisesRegex(ValueError, "finalizer is unfinished"):
            self.settle(True)
        self.assertFalse(self.fake.updates)

    def test_second_quality_failure_prevents_apply(self):
        with patch.object(self.fake, "quality", side_effect=[None, ValueError("quality changed")]):
            with self.assertRaisesRegex(ValueError, "quality changed"):
                self.settle(True)
        self.assertFalse(self.fake.updates)

    def test_second_execution_validation_prevents_apply(self):
        quality = self.fake.quality

        def change(root):
            quality(root)
            if self.fake.quality_calls == 2:
                self.fake.beads["item2-final"]["status"] = "open"

        self.fake.quality = change
        with self.assertRaisesRegex(ValueError, "finalizer is unfinished"):
            self.settle(True)
        self.assertFalse(self.fake.updates)

    def test_transport_context_and_capability_fail_closed(self):
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            output = "--if-status --if-assignee" if "--help" in command else '{"outcome":"pass"}'
            return subprocess.CompletedProcess(command, 0, output, "")

        transport = SETTLE.Transport("/city", "rig", run=run)
        self.assertFalse(transport.capable())
        transport.quality(self.root)
        transport.call("bd", "show", "s1")
        for command in calls:
            self.assertEqual(command[-5:], ["--city", "/city", "--rig", "rig", "--json"])
        self.assertIn("--stage", calls[1])
        self.assertIn("quality", calls[1])
        self.assertEqual(calls[1][0], "bash")

    def test_capability_requires_exact_flag_and_successful_probe(self):
        for output, exit_code, supported in (
                ("--if-revision int", 0, True), ("--if-revision-new", 0, False),
                ("--if-revision", 1, None)):
            with self.subTest(output=output, exit_code=exit_code):
                transport = SETTLE.Transport("/city", "rig", run=lambda cmd, **kw:
                    subprocess.CompletedProcess(cmd, exit_code, output, "probe failed"))
                if supported is None:
                    with self.assertRaises(SETTLE.Unsupported):
                        transport.capable()
                else:
                    self.assertEqual(transport.capable(), supported)

    def test_cli_unsupported_and_malformed_errors_are_json(self):
        from contextlib import redirect_stdout
        import io
        args = ["--root", str(self.root), "--city", "/city", "--rig", "rig", "--apply"]
        self.fake.supported = False
        with patch.object(SETTLE, "Transport", return_value=self.fake), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(SETTLE.main(args), 2)
        self.assertEqual(json.loads(out.getvalue())["status"], "unsupported")
        (self.root / "baseline.json").write_text("invalid")
        with patch.object(SETTLE, "Transport", return_value=self.fake), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(SETTLE.main(args), 1)
        self.assertEqual(json.loads(out.getvalue())["status"], "failed")

    def schema_validators(self):
        directory = SCRIPTS.parents[1] / "commands/settle/schemas"
        result = json.loads((directory / "result.schema.json").read_text())
        failure = json.loads((directory / "failure.schema.json").read_text())
        Draft202012Validator.check_schema(result)
        Draft202012Validator.check_schema(failure)
        registry = Registry().with_resource("result.schema.json", Resource.from_contents(result))
        return (Draft202012Validator(result, registry=registry),
                Draft202012Validator(failure, registry=registry))

    @unittest.skipIf(Draft202012Validator is None, "schema tests require jsonschema, run with uv --with jsonschema")
    def test_schema_contract_for_actual_plan_partial_resume_and_cli_errors(self):
        from contextlib import redirect_stdout
        import io

        result_schema, failure_schema = self.schema_validators()
        # Preview works on older backends and reports their revision verbatim.
        for revision in (None, "opaque-old-backend", -6341175321048868863):
            self.fake.beads["s1"]["revision"] = revision
            result_schema.validate(self.settle()[0])
        self.fake.fail_item = "s2"
        partial, code = self.settle(True)
        self.assertEqual(code, 1)
        result_schema.validate(partial)
        failure_schema.validate(partial)
        self.fake.fail_item = None
        settled, code = self.settle(True)
        self.assertEqual(code, 0)
        result_schema.validate(settled)
        self.assertFalse(failure_schema.is_valid(settled))
        args = ["--root", str(self.root), "--city", str(self.root / "city"),
                "--rig", str(self.root / "repo"), "--apply"]
        for expected_status in ("unsupported", "failed"):
            self.fake.supported = False
            if expected_status == "failed":
                self.fake.quality_failure = True
            with patch.object(SETTLE, "Transport", return_value=self.fake), redirect_stdout(io.StringIO()) as out:
                self.assertNotEqual(SETTLE.main(args), 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["status"], expected_status)
            result_schema.validate(payload)
            failure_schema.validate(payload)

    @unittest.skipIf(Draft202012Validator is None, "schema tests require jsonschema, run with uv --with jsonschema")
    def test_schema_rejects_false_success_invalid_tokens_and_incomplete_receipts(self):
        result_schema, failure_schema = self.schema_validators()
        planned, _ = self.settle()
        settled, _ = self.settle(True)
        broken = copy.deepcopy(settled)
        broken["items"][0]["status"] = "failed"
        broken["items"][0]["error"] = "conflict"
        self.assertFalse(result_schema.is_valid(broken))
        for revision in (True, None, "7", -(2 ** 63) - 1, 2 ** 63):
            broken = copy.deepcopy(settled)
            broken["items"][0]["source_revision"] = revision
            self.assertFalse(result_schema.is_valid(broken))
        for revision in (-(2 ** 63), -6341175321048868863, 0, 2 ** 63 - 1):
            valid = copy.deepcopy(settled)
            valid["items"][0]["source_revision"] = revision
            result_schema.validate(valid)
        for payload in ({"status": "settled"}, {"status": "unsupported"},
                        {"status": "failed"}, {**planned, "error": "conflict"}):
            self.assertFalse(result_schema.is_valid(payload))
        partial = copy.deepcopy(settled)
        partial.update(status="failed", error="unsupported gate", failure_kind="unsupported")
        partial["items"][0].update(status="failed", error="unsupported gate")
        partial["items"][1]["status"] = "pending"
        result_schema.validate(partial)
        failure_schema.validate(partial)
        failure_schema.validate({"schema_version": "1", "ok": False,
                                 "error": {"code": "command_failed", "message": "dispatch failed", "exit_code": 1}})
        self.assertFalse(failure_schema.is_valid(planned))

    @unittest.skipUnless(shutil.which("gc"), "strict discovery test requires gc")
    def test_strict_json_dispatch_and_schema_discovery_in_temporary_city(self):
        # Only the temporary city is loaded. The deliberately mismatched baseline
        # stops settlement before quality, rig lookup, or any bead command.
        city = self.root / "discovery-city"
        city.mkdir()
        (city / ".gc").mkdir()
        (city / "city.toml").write_text(
            '[workspace]\nname = "testcity"\n[imports.omg]\nsource = "./pack"\n')
        pack = city / "pack"
        pack.mkdir()
        (pack / "pack.toml").write_text('[pack]\nname = "omg"\nschema = 2\n')
        shipped = SCRIPTS.parents[1] / "commands/settle"
        shutil.copytree(shipped, pack / "commands/settle")
        (pack / "assets").mkdir()
        (pack / "assets/scripts").symlink_to(SCRIPTS, target_is_directory=True)
        env = {"PATH": os.environ["PATH"], "HOME": str(self.root),
               "PYTHONDONTWRITEBYTECODE": "1", "GC_JSON_CONTRACT_STRICT": "1"}
        prefix = [shutil.which("gc"), "--city", str(city), "omg", "settle"]
        dispatch = subprocess.run([*prefix, "--city", str(city), "--rig", str(self.root / "repo"),
                                   "--root", str(self.root), "--json"],
                                  cwd=self.root, env=env, text=True, capture_output=True, timeout=30)
        self.assertEqual(dispatch.returncode, 1, dispatch.stderr)
        payload = json.loads(dispatch.stdout)
        self.assertEqual(payload, {"status": "failed", "error": "caller city differs from baseline.city"})
        self.assertNotIn("json_unsupported", dispatch.stdout + dispatch.stderr)
        manifest = subprocess.run([*prefix, "--json-schema"], cwd=self.root, env=env,
                                  text=True, capture_output=True, timeout=30)
        self.assertEqual(manifest.returncode, 0, manifest.stderr)
        decoded = json.loads(manifest.stdout)
        self.assertTrue(decoded["json_supported"])
        self.assertEqual(decoded["command"], ["omg", "settle"])
        for role in ("result", "failure"):
            self.assertEqual(decoded["schemas"][role],
                             json.loads((shipped / "schemas" / f"{role}.schema.json").read_text()))
        if Draft202012Validator is not None:
            for validator in self.schema_validators():
                validator.validate(payload)


if __name__ == "__main__":
    unittest.main()
