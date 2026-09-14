# prepare-build

```sh
gc omg prepare-build --rig <rig> [--binding omg]
```

Prepare the local-host build validator compatibility path without starting a
workflow. `initiative start` runs this before saving launch intent. The build's
first work step repeats it for direct formula launches and recovery.

The command verifies the rig's official build roles and OMG architect, resolves
the native checker through the loaded `omg-build` recipe, and exercises its Python
validator with the controller's restricted HOME policy. OMG automatically creates
a private runtime under `<city>/.gc/omg-build/runtimes/` using the Python already
running its tools and installs pinned PyYAML there. It does not install packages
into the system or the application environment. The runtime is cached across
rigs and builds; missing or incomplete dependencies are repaired automatically.

First use needs access to the Python package index. Index/proxy environment
settings are honored; pip settings that could redirect installation outside OMG's
runtime are excluded. A lock serializes provisioning. Failed installs
remain retryable and never mark preparation ready. There is no user-facing Python
selection or dependency setup step. This command is an optional diagnostic tool;
the normal conversational build path invokes it automatically.

It then writes a managed wrapper at
`<rig>/.gc/scripts/checks/build-artifact-valid.sh`. The wrapper sets the durable
rig root and validation PATH, then executes the original checker in the installed pack, so
that checker finds its own Python validator and schemas. The command returns the
resolved paths and interpreter as JSON. Native nested `do-work`, `do-work-item`
and repair checks can keep their existing paths.

A companion `python3` shim under `<rig>/.gc/scripts/omg-build/bin/` selects the
verified interpreter for both metadata parsing and schema validation. OMG's own
build checks reach the same wrapper through a pack-resolved entry script. Runtime
artifact paths supplied by `initiative start` are absolute, so controller and
worker current-directory differences do not change the selected document.

Repeating preparation with the same configuration is idempotent. A receipt and
short filesystem lock protect managed updates. Unrelated scripts, modified
managed wrappers and symlinks are refused instead of overwritten. Resolve the
reported conflict before retrying. Runtime versions are keyed by the underlying
Python and dependency version, so an update provisions a new environment without
deleting the one an older build may still use.

This prepares the local filesystem for the pack's host/tmux execution. It does
not provision a separate container or remote worker filesystem, verify provider
login, launch agents, commit code, or publish documents to Hindsight.
