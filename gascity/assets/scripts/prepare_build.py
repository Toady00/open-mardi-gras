#!/usr/bin/env python3
"""Prepare the local-host compatibility path used by native build sub-formulas."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile


MARKER = "# Managed by OMG prepare-build v1\n"
PYYAML_VERSION = "6.0.3"
REQUIRED_ROLES = ("gc.run-operator", "gc.design-author", "gc.review-synthesizer",
                  "gc.task-decomposer", "gc.implementation-worker",
                  "gc.implementation-reviewer", "gc.publisher")


def run(args, env=None):
    result = subprocess.run(args, capture_output=True, text=True, env=env)
    if result.returncode:
        raise ValueError(f"{shlex.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def gc(*args):
    return json.loads(run([os.environ.get("GC_BIN", "gc"), *args, "--json"]))


def gate_environment(city):
    # Match the inspected engine's ConditionEnv PATH/HOME policy. In particular,
    # do not accidentally validate against a provider's PYTHONPATH or user site.
    dirs = []
    for tool in ("bd", "gc", "dolt", "jq"):
        path = shutil.which(tool)
        if path and str(Path(path).parent) not in dirs:
            dirs.append(str(Path(path).parent))
    for directory in ("/usr/local/bin", "/usr/bin", "/bin"):
        if directory not in dirs:
            dirs.append(directory)
    return {"PATH": os.pathsep.join(dirs), "HOME": str(city), "TMPDIR": tempfile.gettempdir()}


def ensure_runtime(city):
    """Own the dependency runtime; callers never select or configure Python."""
    city = Path(city).resolve(strict=True)
    root = safe_target(city, ".gc/omg-build/runtimes")
    root.mkdir(parents=True, exist_ok=True)
    identity = {"schema": 1, "base": os.path.realpath(sys.executable),
                "version": sys.version, "machine": platform.machine(), "pyyaml": PYYAML_VERSION}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
    directory = safe_target(city, f".gc/omg-build/runtimes/{key}")
    lock = safe_target(city, ".gc/omg-build/runtimes/.lock")
    env = gate_environment(city)
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        directory.mkdir(exist_ok=True)
        marker = directory / "owner.json"
        if marker.is_symlink():
            raise ValueError(f"unexpected runtime marker symlink: {marker}")
        if marker.exists():
            if json.loads(marker.read_text()) != identity:
                raise ValueError(f"unrecognized managed runtime: {directory}")
        elif any(directory.iterdir()):
            raise ValueError(f"refusing to replace an unrecognized runtime directory: {directory}")
        else:
            atomic_write(marker, json.dumps(identity, sort_keys=True) + "\n", 0o644)
        venv = safe_target(city, f".gc/omg-build/runtimes/{key}/venv")
        python = str(venv / "bin/python3")
        probe = [python, "-I", "-c", f"import yaml; assert yaml.__version__ == {PYYAML_VERSION!r}"]
        if Path(python).is_file():
            try:
                run(probe, env)
                return python
            except (OSError, ValueError):
                pass  # Repair only this recognized tool-owned environment.
        print("Preparing OMG build dependencies for this city...", file=sys.stderr)
        try:
            run([sys.executable, "-I", "-m", "venv", "--clear", str(venv)], env)
            # Honor network settings, but never let ambient pip target/prefix/
            # user settings redirect an install into an application or system.
            network = {"PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_NO_INDEX", "PIP_FIND_LINKS",
                       "PIP_TRUSTED_HOST", "PIP_CERT", "PIP_CLIENT_CERT", "PIP_PROXY",
                       "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                       "http_proxy", "https_proxy", "all_proxy", "no_proxy",
                       "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "SSL_CERT_FILE", "SSL_CERT_DIR"}
            install_env = {**{k: v for k, v in os.environ.items() if k in network},
                           **env, "PIP_CONFIG_FILE": os.devnull}
            run([python, "-I", "-m", "pip", "--disable-pip-version-check", "--no-input",
                 "--retries", "1", "--timeout", "30", "--cache-dir", str(safe_target(city, ".gc/omg-build/runtimes/wheel-cache")),
                 "install", "--only-binary=:all:", f"PyYAML=={PYYAML_VERSION}"], install_env)
            run(probe, env)
        except (OSError, ValueError) as error:
            raise ValueError("OMG could not prepare its internal build dependencies. "
                             "First use needs access to the configured Python package index; "
                             f"retry after resolving the reported installation error. {error}") from error
        return python


def verify_validator(checker, city, python):
    checker = Path(checker).resolve(strict=True)
    validator = checker.parent.parent / "validate_build_artifact.py"
    if not checker.is_file() or not os.access(checker, os.X_OK) or not validator.is_file():
        raise ValueError("native checker or its adjacent Python validator is missing/not executable")
    env = gate_environment(city)
    # Use the native CLI and its bundled schemas, not a copied validator. This
    # temporary probe is operational input, never a published document.
    probe = """---
schema: gc.build.implementation-summary.v1
workflow: {id: omg-preparation, formula: omg-build}
methodology: {pack: omg, name: omg-build}
producer: {formula: omg-build, stage: preparation, attempt: 1}
status: draft
trace: {upstream: [], coverage: []}
---
## Summary
Validator preparation probe.
## Intended Behavior
Validate the installed artifact contract.
## Changed Files
None.
## Verification
Native validator invocation only.
## Remaining Risks
This probe does not verify a live agent workflow.
"""
    with tempfile.TemporaryDirectory(prefix="omg-validator-") as tmp:
        path = Path(tmp) / "probe.md"
        path.write_text(probe)
        try:
            run([python, str(validator), "--schema", "gc.build.implementation-summary.v1", "--path", str(path)], env)
        except ValueError as error:
            raise ValueError(f"native validator failed in OMG's managed runtime: {error}") from error
    return str(checker), python, env["PATH"]


def safe_target(root, relative):
    target = root
    for part in Path(relative).parts:
        target /= part
        if target.is_symlink():
            raise ValueError(f"refusing to replace or write through symlink: {target}")
    return target


def atomic_write(path, content, mode):
    fd, name = tempfile.mkstemp(prefix=".omg-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def install_bridge(rig_root, checker, python, gate_path):
    root = Path(rig_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("rig root is not a directory")
    directory = safe_target(root, ".gc/scripts/checks")
    directory.mkdir(parents=True, exist_ok=True)
    wrapper = safe_target(root, ".gc/scripts/checks/build-artifact-valid.sh")
    python_bin = safe_target(root, ".gc/scripts/omg-build/bin")
    python_bin.mkdir(parents=True, exist_ok=True)
    python_wrapper = safe_target(root, ".gc/scripts/omg-build/bin/python3")
    receipt = safe_target(root, ".gc/scripts/checks/.omg-build-artifact.json")
    lock = safe_target(root, ".gc/scripts/checks/.omg-build-artifact.lock")
    content = ("#!/usr/bin/env bash\n" + MARKER + "set -euo pipefail\n"
               + "export GC_RIG_ROOT=" + shlex.quote(str(root)) + "\n"
               + "export PATH=" + shlex.quote(str(python_bin) + os.pathsep + gate_path) + "\n"
               + "exec /bin/bash " + shlex.quote(str(checker)) + ' "$@"\n')
    python_content = ("#!/usr/bin/env bash\n" + MARKER + "exec " + shlex.quote(python) + ' "$@"\n')
    digest = hashlib.sha256(content.encode()).hexdigest()
    python_digest = hashlib.sha256(python_content.encode()).hexdigest()
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        # Recheck after acquiring the lock; another preparation may just have
        # completed. A hash receipt protects operator edits to managed files.
        safe_target(root, ".gc/scripts/checks/build-artifact-valid.sh")
        safe_target(root, ".gc/scripts/checks/.omg-build-artifact.json")
        safe_target(root, ".gc/scripts/omg-build/bin/python3")
        old = json.loads(receipt.read_text()) if receipt.exists() else {}
        outputs = [(wrapper, content, "sha256"), (python_wrapper, python_content, "python_sha256")]
        for target, desired, hash_key in outputs:
            if target.exists():
                existing = target.read_text()
                if existing != desired and (not existing.startswith("#!/usr/bin/env bash\n" + MARKER)
                        or old.get(hash_key) != hashlib.sha256(existing.encode()).hexdigest()):
                    raise ValueError(f"existing checker is not an unchanged OMG-managed wrapper: {target}")
        for target, desired, _ in outputs:
            if not target.exists() or target.read_text() != desired:
                atomic_write(target, desired, 0o755)
            else:
                target.chmod(0o755)
        record = {"schema": 1, "sha256": digest, "checker": str(checker), "python": python,
                  "rig_root": str(root), "wrapper": str(wrapper), "check_path_env": gate_path,
                  "python_wrapper": str(python_wrapper), "python_sha256": python_digest}
        serialized = json.dumps(record, sort_keys=True, indent=2) + "\n"
        if not receipt.exists() or receipt.read_text() != serialized:
            atomic_write(receipt, serialized, 0o644)
    return record


def prepare(rig, binding, city_path=None):
    info = gc("rig", "list", *(["--city", city_path] if city_path else []))
    city = str(Path(info["city_path"]).resolve(strict=True))
    rigs = {item["name"]: item["path"] for item in info["rigs"] if not item.get("hq")}
    if not rig or rig not in rigs:
        raise ValueError("select a configured build rig with --rig")
    root = Path(rigs[rig])
    if not root.is_absolute():
        root = Path(city) / root
    root = root.resolve(strict=True)
    repository = Path(run(["git", "-C", str(root), "rev-parse", "--show-toplevel"]).strip()).resolve()
    if repository != root:
        raise ValueError("configured rig path must be a Git repository root")
    run(["git", "-C", str(root), "remote", "get-url", "origin"])
    agents = gc("agent", "list", "--city", city)
    names = {agent["qualified_name"] for agent in agents["agents"]}
    required = [f"{rig}/{role}" for role in (*REQUIRED_ROLES, binding + ".architect")]
    missing = [name for name in required if name not in names]
    if missing:
        raise ValueError("missing build roles; import the official roles pack on the rig and OMG at city scope: "
                         + ", ".join(missing))
    recipe = gc("formula", "show", "omg-build", "--city", city, "--rig", rig)
    # Match the native asset-layer rule exposed by formula show: search_paths
    # are lowest-to-highest priority, and the last existing asset wins.
    candidates = [Path(layer).parent / "assets/scripts/checks/build-artifact-valid.sh"
                  for layer in recipe["search_paths"]]
    checker = next((path for path in reversed(candidates) if path.is_file()), None)
    if checker is None or not checker.is_absolute():
        raise ValueError("loaded formula layers do not provide the native build-artifact checker")
    python = ensure_runtime(city)
    checker, python, gate_path = verify_validator(checker, city, python)
    record = install_bridge(root, checker, python, gate_path)
    return {"ready": True, "rig": rig, **record}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig", default=os.environ.get("GC_RIG", ""))
    parser.add_argument("--binding", default="omg")
    parser.add_argument("--city", default=os.environ.get("GC_CITY_PATH", os.environ.get("GC_CITY", "")))
    parser.add_argument("--json", action="store_true", help="output is always JSON")
    args = parser.parse_args()
    print(json.dumps(prepare(args.rig, args.binding, args.city), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print(f"omg prepare-build: {error}", file=sys.stderr)
        sys.exit(1)
