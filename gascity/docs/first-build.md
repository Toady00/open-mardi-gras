# First live build

Use a small change in one rig to exercise conversation, documentation, approval,
implementation, review and the Hindsight-compatible report.

## Install

Import OMG and Hindsight as siblings using the [README](../README.md#importing-the-pack),
then run `gc import install`. Start or reload the city and use fresh agent sessions
so they receive the updated skills and prompts. OMG supplies its own builder,
tester and reviewer; no official methodology or role import is required.

The city needs an authenticated provider, working Beads, Git, Bash, jq, Mike Farah
yq v4, and Python 3 for the initiative ledger, native execution verification and
source-task settlement. Archify needs Node.js. Build verification installs nothing
and does not use PyYAML. The check command uses the tools on the PATH of the
process that runs it, controller or worker; it adds no directories of its own.

The target rig must have a clean Git checkout with a commit. All build stages use
that checkout; this trial supports local-host/tmux sessions sharing its filesystem.
Avoid overlapping builds in the same checkout. Code remotes are needed only for
requested publication. The docs repository needs its agreed remote publication path.

Configure Hindsight's actual bank and endpoint/profile as described by its pack:

```toml
[workspace]
env = { HINDSIGHT_BANK = "<your-bank>" }
```

Merge this into existing settings. Keep the city in Git if city-level agents own
initiative documents.

## Conversation, approval, build

```sh
gc session new app/omg.product-manager --alias omg-trial
```

Discuss the change. The agent retrieves relevant Hindsight context, maintains a
visual proposal and discussion summary, and records your approval of the exact
visual revision. It generates documents and runs shared refinement. Approve the
resulting specs through conversation, then give a separate instruction:

> Start the build for this initiative in app. Keep the code local for this trial.

The agent records your request, freezes the approved documents without rewriting
them, and launches `omg-build`. The architect plans and decomposes, the builder
implements each tracked item, and the tester and reviewer assess the integrated
change. Required findings trigger bounded repair/test/review attempts. The
architect reconciles requirements before finalization. Code push and PR creation
default to disabled; document publication follows its own agreed policy.

The approved specs must explicitly separate development from downstream execution
using the `omg-development` contract. Existing initiatives need focused refinement
and renewed acceptance when adding or changing that contract. Plans cannot invent
categories or infer them from B/O ID prefixes. The builder delivers required test
scripts and pipeline wiring, but their later environment-dependent results remain
pending. Terraform follows the same boundary as application code.

## When authoring needs a decision

The PM should present a concrete question, recommendation and affected scope in
your original conversation. Workers record the question and stop the remaining
authoring work instead of repeatedly starting agents to restate it. The command
sends mail and a queued nudge; notification receipts and failures appear in the
initiative record. Ask the PM to inspect that record if a message appears missing.

Answer in the conversation. The PM records the resolution, updates affected
documents and, when authorized, starts another refinement after the old operation
settles. If the initial pass stopped before all documents existed, that refinement
includes the missing authoring steps. Your answer is not spec approval or build
authorization. A dashboard's failed/interrupted native run can mean a deliberate
human handoff; consult the operation's semantic `result` for the distinction.

Use a fresh session or explicitly reload the updated `omg-initiative` skill when
continuing a conversation that predates these handoff rules. Earlier run records
remain historical; this update does not regrade or rerun them.

## Inspect the result

```sh
gc omg initiative show <initiative-bead-id>
```

The operation record contains the approval, artifact root and launch receipt.
Inspect its Gas City workflow graph and the files in that artifact root:

- Original-spec inventory and execution plan.
- Tracked work/convoy membership and per-item test receipts.
- Integrated test logs, review findings and requirement reconciliation.
- Actual code-publication outcome.

For diagnostics, the same checker the controller runs is available as:

```sh
gc omg verify --stage quality --root <absolute-artifact-root>
```

Run this diagnostic after the repair/test/review group finishes. Its workers do
not run the full gate before review; the controller does. A successful drain leaves
source tasks open. Quality checks exact native manifest membership, successful item
workflows and finalizers, and current passing receipts, rather than source closure.

After writing reconciliation.json and passing reconcile verification, the architect
may preview source-task settlement within the existing reconciliation step:

```sh
gc omg settle --root <absolute-artifact-root> --city <absolute-city-path> --rig <rig-name>
```

Preview is read-only and checks quality again. `--apply` checks for advertised
`gc bd update --if-revision` support and integer source revisions at run time.
A backend that does not advertise it makes apply return unsupported with exit 2
and no mutation.
Source tasks remain pending with that reason; this is bookkeeping, not a failed
code-quality check. Other conflicts or partial settlement must be reported without
claiming completion. Never close tasks unconditionally or retrofit
`gc.source_bead_id`. Failed runs preserve open source tasks and findings.

The final report belongs at `docs/initiatives/<id>/reports/<operation>.md` in the
original document repository. It distinguishes implemented, reviewed and published
code. Check the `omg-report` bead separately because it runs after root settlement,
including failed builds. A stalled infrastructure operation must settle or be
explicitly failed before its report can run.
Reconcile/finalize verification gates execution evidence, not source-task closure.
The report must list pending source IDs and settlement reasons. For this no-push
trial, describe code as local-only. The architect commits the report on its own
(`git commit --only -- <path>`, leaving your other changes and staged files alone)
in the document repository, records `status: local` in report.json and runs
`gc omg report publish`, which prints `local` and touches nothing; the checked
report step then completes without contacting any remote, and the local commit is
the durable artifact until you publish it yourself. The report is published only
when a passed build's own finalized publication receipt pushed code from that
same checkout, and only to that receipt's ref; a separate docs repository, or a
failed or canceled root, always keeps its report local. `report publish` runs in
the architect's session with its Git credentials (the controller check has none)
and refuses to push when an unrelated unpublished commit sits below the report or
the remote has moved; a blocker or failed push stays recoverable on the report
bead with its local commit and the exact Git error.

```sh
gc omg verify --stage report --root <absolute-artifact-root>
```

## Upgrading an earlier trial

New builds do not reference the old validator wrappers or cached environments.
Existing in-flight workflows retain their cooked graph and may still need them;
finish or explicitly retire those runs before removing their managed files.
The historical locations were `<city>/.gc/omg-build/runtimes/`,
`<rig>/.gc/scripts/checks/build-artifact-valid.sh` and its receipt, and
`<rig>/.gc/scripts/omg-build/bin/`. Inspect ownership before cleanup. OMG does not
delete existing runtime files during this update. Remove official-pack imports
from consuming config only if no other workflows there use them.

## Verification boundary

If a build fails, let its graph and report settle, fix the cause, and explicitly
request a retry. The agent uses `initiative start --retry <failed-operation>` for
unchanged approval, or normal `start` after approving revised docs. A retry is a
new operation with separate evidence, not an edited history of the failed run.

Automated tests compile OMG formulas with the actual Gas City CLI without an
official methodology import, check command/role discovery, and execute verification
using real Git/yq/jq under normal and restricted controller environments. Bead
transport is isolated in fixtures. Provider-driven execution and real Git/Hindsight
publication still need this live trial. Preserve workflow IDs, failing commands,
artifact paths and expected behavior when reporting feedback.
