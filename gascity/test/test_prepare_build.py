"""Exercise native validator delegation without launching agents or a real build."""
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


PACK = Path(__file__).resolve().parents[1]
REAL_GC = shutil.which("gc")
spec = importlib.util.spec_from_file_location("prepare_build", PACK / "assets/scripts/prepare_build.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.rig = self.root / "rig checkout"
        self.rig.mkdir()
        self.checker = self.root / "native checker's path.sh"
        self.checker.write_text('#!/bin/bash\nprintf "%s\\n" "$GC_RIG_ROOT" "$1"\nexit 7\n')
        self.checker.chmod(0o755)

    def install(self):
        return p.install_bridge(self.rig, str(self.checker), sys.executable, "/usr/bin:/bin")

    def test_bridge_preserves_arguments_exit_status_and_quoted_paths(self):
        receipt = self.install()
        worker = self.root / "worker"
        worker.mkdir()
        result = subprocess.run([receipt["wrapper"], "argument with spaces"], cwd=worker,
                                capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout.splitlines(), [str(self.rig), "argument with spaces"])

    def test_preparation_is_idempotent_and_can_refresh_unchanged_managed_wrapper(self):
        first = self.install()
        wrapper = Path(first["wrapper"])
        before = wrapper.stat().st_mtime_ns
        self.assertEqual(self.install(), first)
        self.assertEqual(wrapper.stat().st_mtime_ns, before)
        other = self.root / "updated-checker.sh"
        shutil.copyfile(self.checker, other)
        self.checker = other
        updated = self.install()
        self.assertNotEqual(updated["sha256"], first["sha256"])
        self.assertIn(str(other), wrapper.read_text())

    def test_unrelated_and_modified_scripts_are_preserved(self):
        wrapper = Path(self.install()["wrapper"])
        for content in ["#!/bin/bash\n# Operator-owned checker\n", wrapper.read_text() + "# Local edit\n"]:
            wrapper.write_text(content)
            with self.assertRaisesRegex(ValueError, "unchanged OMG-managed"):
                self.install()
            self.assertEqual(wrapper.read_text(), content)

    def test_symlinks_are_not_followed_for_installation(self):
        target = self.root / "outside"
        target.mkdir()
        (self.rig / ".gc").symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.install()
        self.assertEqual(list(target.iterdir()), [])

    def test_missing_preparation_is_an_explicit_check_failure(self):
        result = subprocess.run([str(PACK / "assets/scripts/checks/omg-build-artifact.sh")],
                                env={"PATH": "/usr/bin:/bin", "GC_STORE_PATH": str(self.rig)},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("prepare-build", result.stderr)


@unittest.skipUnless(os.environ.get("GC_BASE_PACK"), "set GC_BASE_PACK to exercise the real native validator")
class NativeValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.city = self.root / "city"
        self.rig = self.city / "rig checkout"
        self.worker = self.city / "worktree"
        self.rig.mkdir(parents=True)
        self.worker.mkdir()
        self.native = Path(os.environ["GC_BASE_PACK"]).resolve()
        self.checker = self.native / "assets/scripts/checks/build-artifact-valid.sh"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.state = self.root / "beads.json"
        shim = self.bin / "gc"
        shim.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
args = sys.argv[1:]
if args[:2] != ["bd", "show"]:
    sys.exit("unexpected gc call: " + repr(args))
with open(os.environ["PROBE_BEADS"]) as f:
    beads = json.load(f)
if args[2] not in beads:
    sys.exit("missing bead " + args[2])
print(json.dumps(beads[args[2]]))
''')
        shim.chmod(0o755)
        # The native safe PATH puts bd's directory first. Keep that directory
        # inside the fixture too, so the real checker never reaches a live gc.
        bd_shim = self.bin / "bd"
        bd_shim.write_text("#!/bin/sh\nexit 99\n")
        bd_shim.chmod(0o755)
        self.environment = patch.dict(os.environ, {"PATH": str(self.bin) + os.pathsep + os.environ["PATH"]})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.report = self.rig / ".omg/build/summary.md"
        self.report.parent.mkdir(parents=True)
        self.valid = """---
schema: gc.build.implementation-summary.v1
workflow: {id: root, formula: do-work}
methodology: {pack: gascity, name: omg-build}
producer: {formula: do-work, stage: implement, attempt: 1}
status: approved
trace:
  upstream: [{path: docs/spec.md, hash: 'git:revision', ids: [R1]}]
  coverage: [{id: R1, status: covered}]
---
## Summary
Fixture only.
## Intended Behavior
Account for R1.
## Changed Files
Fixture only.
## Verification
| ID | Status |
| --- | --- |
| R1 | covered |
## Remaining Risks
No application implementation is claimed by this fixture.
"""
        self.report.write_text(self.valid)
        self.beads = {
            "item": {"id": "item", "metadata": {
                "gc.root_bead_id": "root", "gc.build.artifact_schema": "gc.build.implementation-summary.v1",
                "gc.build.artifact_path_keys": "gc.implementation.summary_path"}},
            "root": {"id": "root", "metadata": {"gc.implementation.summary_path": ".omg/build/summary.md"}}}
        self.state.write_text(json.dumps(self.beads))

    def test_real_checker_succeeds_and_rejects_bad_artifacts_from_rig_and_worktree(self):
        managed = p.ensure_runtime(self.city)
        checker, python, path = p.verify_validator(self.checker, self.city, managed)
        receipt = p.install_bridge(self.rig, checker, python, path)
        env = {**p.gate_environment(self.city), "GC_BEAD_ID": "item", "GC_STORE_PATH": str(self.rig),
               "GC_DIR": str(self.city), "GC_WORK_DIR": str(self.worker), "PROBE_BEADS": str(self.state)}
        # Both worker manual checks and controller checks execute this installed
        # path. The wrapper pins the durable rig root despite the worker cwd.
        for cwd in [self.rig, self.worker]:
            with self.subTest(cwd=cwd):
                result = subprocess.run([receipt["wrapper"]], cwd=cwd, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertIn("build artifact valid", result.stdout)
        cases = {"missing-section": self.valid.replace("## Verification", "## Wrong heading"),
                 "wrong-schema": self.valid.replace("gc.build.implementation-summary.v1", "gc.build.plan.v1"),
                 "missing-coverage": self.valid.replace("coverage: [{id: R1, status: covered}]", "coverage: []")}
        for name, content in cases.items():
            with self.subTest(failure=name):
                self.report.write_text(content)
                result = subprocess.run([receipt["wrapper"]], cwd=self.worker, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertIn("failed validation", result.stderr)
        self.report.unlink()
        result = subprocess.run([receipt["wrapper"]], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not exist", result.stderr)

    def test_preparation_resolves_installed_asset_and_fails_before_writes_for_missing_roles(self):
        p.run(["git", "-C", str(self.rig), "init", "-q"])
        p.run(["git", "-C", str(self.rig), "remote", "add", "origin", "https://example.invalid/repo.git"])
        info = {"city_path": str(self.city), "rigs": [{"name": "app", "path": str(self.rig)}]}
        agents = {"agents": [{"qualified_name": "app/" + role} for role in (*p.REQUIRED_ROLES, "omg.architect")]}
        recipe = {"search_paths": [str(self.native / "formulas")]}
        with patch.object(p, "gc", side_effect=[info, {"agents": []}]):
            with self.assertRaisesRegex(ValueError, "missing build roles"):
                p.prepare("app", "omg")
        self.assertFalse((self.rig / ".gc").exists())
        with patch.object(p, "gc", side_effect=[info, agents, recipe]):
            result = p.prepare("app", "omg")
        self.assertTrue(result["ready"])
        self.assertEqual(result["checker"], str(self.checker))
        self.assertTrue(Path(result["wrapper"]).is_file())

    def test_validator_failure_does_not_install_bridge(self):
        validator = self.native / "assets/scripts/validate_build_artifact.py"
        self.assertTrue(validator.is_file())
        with patch.object(p, "run", side_effect=ValueError("PyYAML is required")):
            with self.assertRaisesRegex(ValueError, "PyYAML"):
                p.verify_validator(self.checker, self.city, sys.executable)
        self.assertFalse((self.rig / ".gc").exists())

    def test_managed_runtime_is_automatic_and_reused(self):
        outside = self.root / "application-packages"
        config = self.root / "pip.conf"
        config.write_text(f"[global]\ntarget = {outside}\n")
        with patch.dict(os.environ, {"PIP_TARGET": str(outside), "PIP_PREFIX": str(outside),
                                     "PIP_USER": "1", "PIP_CONFIG_FILE": str(config)}), patch.object(p, "run", wraps=p.run) as commands:
            python = p.ensure_runtime(self.city)
            self.assertEqual(p.ensure_runtime(self.city), python)
            installs = [call for call in commands.call_args_list if "install" in call.args[0]]
            self.assertEqual(len(installs), 1)
        self.assertFalse(outside.exists())
        self.assertTrue(Path(python).is_relative_to(self.city / ".gc/omg-build/runtimes"))
        self.assertEqual(p.run([python, "-I", "-c", "import yaml; print(yaml.__version__)"],
                               p.gate_environment(self.city)).strip(), p.PYYAML_VERSION)

    def test_failed_dependency_install_is_retried_automatically(self):
        original = p.run
        attempts = []
        def fail_install_once(args, env=None):
            if "install" in args:
                attempts.append(args)
                if len(attempts) == 1:
                    raise ValueError("package index unavailable")
            return original(args, env)
        with patch.object(p, "run", side_effect=fail_install_once):
            with self.assertRaisesRegex(ValueError, "internal build dependencies"):
                p.ensure_runtime(self.city)
            self.assertFalse((self.rig / ".gc/scripts/checks/build-artifact-valid.sh").exists())
            python = p.ensure_runtime(self.city)
            self.assertTrue(Path(python).is_file())
        self.assertEqual(len(attempts), 2)

    def test_missing_cached_dependency_is_repaired_automatically(self):
        python = p.ensure_runtime(self.city)
        module = Path(p.run([python, "-I", "-c", "import yaml; print(yaml.__file__)"],
                            p.gate_environment(self.city)).strip()).parent
        shutil.rmtree(module)
        self.assertEqual(p.ensure_runtime(self.city), python)
        p.run([python, "-I", "-c", "import yaml"], p.gate_environment(self.city))

    @unittest.skipUnless(REAL_GC, "gc is required to exercise command discovery and nested formulas")
    def test_native_command_prepares_paths_for_all_nested_checks(self):
        p.run(["git", "-C", str(self.rig), "init", "-q"])
        p.run(["git", "-C", str(self.rig), "remote", "add", "origin", "https://example.invalid/repo.git"])
        pack = self.root / "omg-pack"
        pack.mkdir()
        for name in ["agents", "assets", "commands", "formulas", "template-fragments"]:
            (pack / name).symlink_to(PACK / name, target_is_directory=True)
        manifest = json.loads(p.run(["yq", "-p=toml", "-o=json", ".", str(PACK / "pack.toml")]))
        manifest["imports"]["gc"] = {"source": str(self.native)}
        # Only the local dependency location differs from the shipped manifest.
        result = subprocess.run(["yq", "-p=json", "-o=toml", "."], input=json.dumps(manifest),
                                text=True, capture_output=True, check=True)
        (pack / "pack.toml").write_text(result.stdout)
        (self.city / "city.toml").write_text(
            '[workspace]\nname="validator-probe"\n'
            f'[imports.omg]\nsource={json.dumps(str(pack))}\n'
            f'[[rigs]]\nname="app"\npath={json.dumps(str(self.rig))}\n'
            f'[rigs.imports.gc]\nsource={json.dumps(str(self.native / "roles"))}\n')
        legacy = p.install_bridge(self.rig, str(self.checker), sys.executable,
                                  p.gate_environment(self.city)["PATH"])
        # Old interpreter settings must not govern the managed runtime either.
        env = {**os.environ, "GC_BIN": REAL_GC, "OMG_BUILD_PYTHON": "/does-not-exist"}
        command = [REAL_GC, "--city", str(self.city), "omg", "prepare-build", "--rig", "app", "--json"]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["ready"])
        self.assertNotEqual(receipt["python"], legacy["python"])
        self.assertTrue(Path(receipt["python"]).is_relative_to(self.city / ".gc/omg-build/runtimes"))
        help_result = subprocess.run([*command, "--help"], env=env, capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertNotIn("--python", help_result.stdout)
        # Repeated preparation reuses the automatic runtime and installed bridge.
        repeated = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(repeated.returncode, 0, repeated.stderr + repeated.stdout)
        self.assertEqual(json.loads(repeated.stdout), receipt)
        for formula in ["omg-build", "do-work", "do-work-item", "review", "implement", "fix-loop-base"]:
            result = subprocess.run([REAL_GC, "formula", "show", formula, "--city", str(self.city),
                                     "--rig", "app", "--json"], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            checks = [step["metadata"]["gc.check_path"] for step in json.loads(result.stdout)["steps"]
                      if "gc.check_path" in step.get("metadata", {})]
            self.assertTrue(checks)
            for path in checks:
                target = Path(path) if Path(path).is_absolute() else self.rig / path
                self.assertTrue(target.is_file(), f"{formula}: {target}")
                self.assertTrue(os.access(target, os.X_OK), f"{formula}: {target}")
        runtime_env = {**p.gate_environment(self.city), "PROBE_BEADS": str(self.state), "GC_BEAD_ID": "item",
                       "GC_STORE_PATH": str(self.rig), "GC_WORK_DIR": str(self.worker), "GC_DIR": str(self.city)}
        result = subprocess.run([receipt["wrapper"]], cwd=self.worker, env=runtime_env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        result = subprocess.run([str(PACK / "assets/scripts/checks/omg-build-artifact.sh")],
                                cwd=self.worker, env=runtime_env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
