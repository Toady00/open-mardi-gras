# initiative

Durable records behind OMG conversations. Agents use this command on the human's
behalf; approval and explicit build initiation are separate.

```text
gc omg initiative init --slug SLUG [--title TITLE] [--rig RIG] [--notify SESSION]
gc omg initiative list
gc omg initiative show BEAD
gc omg initiative direction BEAD --revision SHA --file IR --file HTML --authority TEXT
gc omg initiative generate BEAD --authority TEXT
gc omg initiative refine BEAD --authority TEXT
gc omg initiative revise BEAD
gc omg initiative snapshot BEAD --revision SHA
gc omg initiative review BEAD --role product|technical --verdict pass|required|human --artifact PATH
gc omg initiative ready BEAD
gc omg initiative decision BEAD --note TEXT
gc omg initiative resolve BEAD --decision ID --note ANSWER --authority TEXT
gc omg initiative complete-step BEAD --operation KEY --step STEP [--outcome fail --note ERROR]
gc omg initiative watch BEAD --notify SESSION
gc omg initiative notify BEAD
gc omg initiative accept BEAD --authority TEXT
gc omg initiative start BEAD --rig RIG --authority TEXT [--push true] [--open-pr true]
gc omg initiative start BEAD --rig RIG --retry FAILED_OPERATION --authority TEXT
gc omg initiative materialize BEAD [--input specs]
gc omg initiative recover BEAD --operation KEY --workflow ROOT --authority TEXT
gc omg initiative abandon BEAD --operation KEY --launcher-stopped --note REASON --authority TEXT
gc omg initiative settle BEAD --operation KEY --workflow ROOT
```

Use the actual import binding in place of `omg`. For launch operations under a
different binding also pass `--binding <name>`. All output is JSON except
`materialize`, which prints the absolute frozen-input directory. Its default is
approved direction; `--input specs` selects the accepted document snapshot.

`--authority` records the human's actual instruction and a session/message
reference. It is an audit record, not authentication. Agents must not invent it.
`direction` requires adjacent same-stem JSON/HTML pairs at an exact commit. It
preserves earlier approved baselines. `accept` records approval without changing
files or launching work; apply and publish the approval metadata specified by
`hindsight-shipping` separately. `start` requires
explicit build authority and returns an existing receipt for repeated requests
against the same accepted revision and rig. The newest attempt is found by
following `retry_of` links, not by key order; a forked history is reported as
ambiguous rather than guessed.

Before recording a new build launch, `start` checks local tools and freezes the
approved Git blobs without translating them. It records the launch intent with
the metadata CAS first, then persists the operation-specific baseline inventory
under an absolute artifact root exactly once, then dispatches. A losing
concurrent caller therefore never writes a baseline, an existing different
baseline is never overwritten, and a baseline write failure leaves a `launching`
operation for `abandon`. Omitted `--push`/`--open-pr` mean no code publication.
The standalone OMG formula uses [verify](../verify/help.md) for mechanical checks
and OMG's builder, tester and reviewer for implementation evidence.

Init infers the initiating rig from `GC_RIG`, otherwise uses the city. An explicit
empty `--rig ''` selects city scope. The owner repository must be a Git root.
Records use the city work store and native metadata CAS; publication uses the
owner repository's normal Git policy. Runtime requires `gc`, Git, Python 3,
Mike Farah's `yq`, Bash, jq, shasum, and a working city Beads backend with metadata CAS support.

Snapshots parse the exact committed spec bodies' `omg-delivery` blocks through the
shared delivery-contract checker. The approved classification is part of the
hashed documents. Altering it requires renewed whole-set review and acceptance.

If launch acknowledgement is lost, the record remains `launching`. Inspect native
state and `recover` the matching workflow. If launch failed before creating a
workflow, first confirm the original launcher AND its child processes have
exited. Then use `abandon` with that confirmation, the reason, and the human's
instruction. Never use it while the original launch could still complete.

Abandonment checks all beads, including closed and partial work, in the exact
launch store. Existing workflow evidence, an unavailable store, or a concurrent
record change prevents abandonment. City launches with a relocated graph store
are refused because the current native CLI cannot provide an exact-store absence
check there; inspect native storage and recover existing work instead. Federated
listings that silently omit unavailable stores are not sufficient proof.

An abandoned operation remains in history with its authority, reason and source
bead. Abandonment does not launch anything. A subsequent explicit `generate`,
`refine`, or `start` request creates a fresh operation. Repeating that request
reuses the new active build receipt. Successfully launched or settled operations
cannot be abandoned; use native workflow recovery for those.

A settled failed build can instead be retried with `start --retry <operation>`
and explicit authority. The command checks the matching native root is closed
with outcome fail and the rig/approved snapshot match. It creates a new operation,
source bead and artifact directory, linked through `retry_of`. Repeating that
request returns the retry receipt; retrying another failed attempt names that
new attempt explicitly. Concurrent or unresolved attempts block retries. Successful
runs cannot be retried this way. Changed approved documents use ordinary `start`
after fresh acceptance. Neither path reopens the old graph or rewrites its report.
A retry keeps the prior attempt's `push`/`open_pr` authorization: omitted flags
inherit it, an equal explicit flag is accepted, and a different one is refused,
because changing code publication is a separate request that a retry never
grants.

## Decisions and notifications

Init and launch capture `GC_SESSION_ID` for manual or named sessions; workers
retain the existing conversation address. Pass `--notify` outside that context,
or use `watch` to establish a return address. Formula workers pass `--operation`
to `decision`, `review`, `revise`, `snapshot`, and `ready`.

`decision` records one identified pending question and interrupts the active
operation. Its note should contain the question, evidence, options, recommendation
and consequence. It immediately sends mail and queues a `wait-idle` session nudge.
`review --verdict human` requires that same `--note`; human evidence is accepted
without a complete snapshot, but never satisfies readiness.

`complete-step` validates a claimed ordinary document step against its workflow
and operation. If interrupted, it ends the enclosing check's retry budget at the
current attempt, writes native failure and closes only the work step. Gas City
skips the remaining scope and preserves the final handoff. Required review
findings keep the normal three-attempt repair budget. Control/root beads and
teardown are not valid complete-step targets.

`resolve` requires the exact pending decision ID and the human's answer/authority.
It archives the resolution, clears the active question, and leaves drafts for
revision. For pre-update needs-human records without an ID, use `--decision legacy`.
It does not restart a run. After the old operation settles, `refine` automatically
includes missing initial authoring steps if the discussion/PRD/HLD/spec inventory
is incomplete. Existing drafts must be reconciled rather than overwritten.

Settlement preserves the native `outcome` separately from `result`:
`needs-human`, `approval-ready`, `incomplete`, `failed`, or build `development-verified`.
It sends a final result notice. Native failure is how a human interruption stops
work; native pass alone is not document approval.

`notifications` holds separate mail/nudge receipts and any delivery error. Queued
does not mean read. Failures leave the decision/result durably recorded and are
retryable with `notify`, without re-launching. Ordinary retries reuse receipts;
a crash after an external send but before receipt persistence can duplicate a
notice, identifiable by its event ID. A metadata/transport failure on the state
change itself exits nonzero; a notification failure is recorded and reported on
stderr without undoing the successful state change.

Readiness checks compare Git bytes and inventory to the reviewed snapshot, so
the controller does not require `yq`. Agent-invoked snapshot creation and accepted
document comparison still require it. `ready` refuses unresolved human decisions.
`check` fails on needs-human rather than reporting a passing verification.
No custom dispatcher is started.
