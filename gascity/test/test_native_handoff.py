"""Exercise the installed engine's scope/ralph interruption with an isolated file store."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PACK = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("gc"), "native gc runtime required")
class NativeHandoffTests(unittest.TestCase):
    def test_human_failure_aborts_checked_scope_without_another_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            city = Path(tmp)
            (city / ".gc").mkdir()
            (city / "city.toml").write_text(
                '[workspace]\nname="handoff-test"\nprefix="ht"\n'
                '[beads]\nprovider="file"\n'
                f'[imports.omg]\nsource={json.dumps(str(PACK))}\n'
                '[[agent]]\nname="control-dispatcher"\nstart_command="true"\n')
            env = {key: val for key, val in os.environ.items()
                   if not key.startswith(("GC_", "BEADS_"))}
            env["GC_HOME"] = str(city / "gc-home")

            def cli(*args):
                result = subprocess.run(["gc", "--city", str(city), *args], cwd=city,
                                        env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout

            cli("formula", "cook", "omg-refine", "--var", "initiative=fixture",
                "--var", "operation=run-1", "--json")
            store = city / ".gc/beads.json"
            data = json.loads(store.read_text())

            def indexed():
                return {b.get("metadata", {}).get("gc.step_ref", b.get("metadata", {}).get("gc.step_id")): b
                        for b in json.loads(store.read_text())["beads"]}

            # Simulate workers finishing preparation, then recording a human
            # interruption in the first refinement writer. No controller runs
            # concurrently against this fixture; the real engine executes every
            # subsequent scope/control transition below.
            for bead in data["beads"]:
                meta = bead.get("metadata", {})
                ref = meta.get("gc.step_ref", "")
                if ref == "omg-refine.prepare":
                    bead["status"] = "closed"
                    meta["gc.outcome"] = "pass"
                if ref.endswith("refinement.iteration.1.assess-product"):
                    bead["status"] = "closed"
                    meta.update({"gc.outcome": "fail", "gc.failure_class": "hard",
                                 "omg.outcome": "needs-human", "omg.decision": "decision-fixture"})
                if ref == "omg-refine.refinement":
                    # complete-step ends the current check's retry budget
                    # before closing the human-blocked worker (unit-tested).
                    meta["gc.max_attempts"] = "1"
            store.write_text(json.dumps(data))
            rows = indexed()
            cli("convoy", "control", rows["omg-refine.prepare-scope-check"]["id"])
            cli("convoy", "control", rows["omg-refine.refinement.iteration.1.assess-product-scope-check"]["id"])
            rows = indexed()
            body = rows["refinement.iteration.1"]
            self.assertEqual(body["status"], "closed")
            self.assertEqual(body["metadata"]["gc.outcome"], "fail")
            control = cli("convoy", "control", rows["omg-refine.refinement"]["id"])
            rows = indexed()
            self.assertEqual(rows["omg-refine.refinement"]["status"], "closed", control + json.dumps(rows["omg-refine.refinement"]))
            self.assertEqual(rows["omg-refine.refinement"]["metadata"]["gc.outcome"], "fail")
            self.assertFalse(any("iteration.2" in (ref or "") for ref in rows))
            self.assertEqual(rows["refinement.iteration.1.review-product"]["metadata"]["gc.outcome"], "skipped")
            # Outer scope settlement skips ordinary work, preserves handoff.
            cli("convoy", "control", rows["omg-refine.refinement-scope-check"]["id"])
            rows = indexed()
            self.assertEqual(rows["omg-refine.documents"]["status"], "closed")
            self.assertEqual(rows["omg-refine.handoff"]["status"], "open")
            cli("convoy", "control", rows["omg-refine.workflow-finalize"]["id"])
            rows = indexed()
            self.assertEqual(rows["omg-refine"]["status"], "closed")
            self.assertEqual(rows["omg-refine"]["metadata"]["gc.outcome"], "fail")
            self.assertEqual(rows["omg-refine.handoff"]["status"], "open")


if __name__ == "__main__":
    unittest.main()
