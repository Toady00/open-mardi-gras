# First live build

This trial exercises conversation, documentation, approval, native implementation,
and the final Hindsight-compatible report. Use a small change in one rig so the
first result is easy to inspect.

## Install and prepare

Use the sibling OMG/Hindsight city imports and per-rig official build roles in
the [README](../README.md#importing-the-pack), then run `gc import install`.
The city must be running with a configured, authenticated provider and a working
Beads backend. The target rig must be a Git repository with a reachable `origin`
and a published default branch: native workers start from that remote branch.

Configure the actual Hindsight bank in the city's existing workspace environment,
along with its endpoint/profile settings as described by the Hindsight pack:

```toml
[workspace]
env = { HINDSIGHT_BANK = "<your-bank>" }
```

Merge this into existing workspace settings rather than replacing other env vars.
Keep the city itself in Git if city-level agents will own initiative documents.

The native artifact validator requires PyYAML. A dedicated local Python environment
is useful because controller checks use the city directory as HOME, which can hide
packages installed only in your normal user site. For example:

```sh
python3 -m venv /absolute/path/to/omg-build-python
/absolute/path/to/omg-build-python/bin/python3 -m pip install 'PyYAML>=6,<7'
```

From your city directory, prepare the chosen rig:

```sh
gc omg prepare-build --rig app --python /absolute/path/to/omg-build-python/bin/python3
```

Use your actual rig name in place of `app`. You can omit `--python` if the default
check interpreter already has PyYAML. The command remembers a selected interpreter;
`OMG_BUILD_PYTHON` in the workspace environment can also select it explicitly.

Success returns JSON containing `ready: true`, the rig root, original checker,
installed wrapper and interpreter. It verifies configured build roles and runs a
temporary document through the actual native validator. It does not start a build
or contact Hindsight. If preparation fails, fix the reported issue and rerun it.

## Start a conversation

Create a rig-level PM conversation, or use an existing one:

```sh
gc session new app/omg.product-manager --alias omg-trial
```

Ask for the small change you want and discuss its behavior and scope. The agent
should retrieve relevant Hindsight context, build the visual proposal and living
discussion summary, and record your approval of the exact visual revision.
It then generates documents and runs shared refinement. The initiative lives at
`<rig>/docs/initiatives/<id>`; a city-level conversation uses the city's same path.

When the documents are ready, inspect them and approve the selected specs through
conversation. The agent applies Hindsight's approval and publication contract.
Then give the separate build instruction, for example:

> Start the build for this initiative in app. Keep the code local for this trial.

The agent uses `initiative start`. Local preparation runs again before launch,
and the workflow repeats its preparation step before producing native artifacts.
Code push/PR creation defaults to disabled. Document publication follows the
repository's agreed policy independently of those code-publication flags.

## Inspect the result and capture feedback

Ask the agent for the initiative ID and native workflow root. The initiative's
record is available with:

```sh
gc omg initiative show <initiative-bead-id>
```

It contains the pinned approvals, preparation details and launch receipt. Inspect
the code changes and reported test evidence. The architect's final report belongs
at `docs/initiatives/<id>/reports/<operation>.md` in the original document repository.
It should reconcile every requirement with implementation evidence, deviations,
unfinished work and actual publication status.

Check the `omg-report` assignment separately: the build root can settle before
post-settlement reporting finishes. A failed build still needs a report. A workflow
stalled on infrastructure needs that error resolved or its failure recorded before
the post-settlement assignment can proceed.

For feedback, preserve the initiative/workflow IDs, the failing step or command
and its error, relevant artifact paths, and the behavior you expected. Useful
questions are whether the requirements adapter added value, whether review findings
earned their cost, and whether conversation resumed with enough context. Those
observations will inform how much of the native methodology OMG should retain.

## What preparation installs

`<rig>/.gc/scripts/checks/build-artifact-valid.sh` is an OMG-managed forwarding
wrapper, with an adjacent hash receipt. A companion Python launcher under
`<rig>/.gc/scripts/omg-build/bin/` selects the verified interpreter. The wrapper
sets the durable rig root and executes the checker in the installed official pack.
The original checker still finds its own validator and schemas and still rejects
malformed artifacts. Nothing is patched in the upstream checkout.

The setup preserves unrelated or locally modified files, and serializes its own
updates with a short filesystem lock. Refresh it between builds after changing
dependency installations or Python environments. This is local-host/tmux support;
separate container and remote-worker filesystems need their own provisioning.

## Verification boundary

Automated checks cover native formula compilation, namespacing, command discovery,
legacy check paths, real native validation through the wrapper, revision guards,
and launch/recovery behavior. Bead reads in validator tests are stubbed. A live
provider-driven implementation and publication to your real Git/Hindsight services
are what this trial is intended to establish.
