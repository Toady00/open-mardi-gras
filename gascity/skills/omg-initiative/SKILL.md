---
name: omg-initiative
description: Discuss, model, author, refine, approve and explicitly launch Gas City OMG initiatives through conversation.
---

# OMG initiatives

## Conversation and durable state

Either PM or architect can lead. The human speaks to agents, not a queue CLI.
Build context using the always-present Hindsight prompt guidance: list available
mental models and fetch the relevant ones, then reflect as soon as useful
background questions emerge. Reflect again as the conversation develops.
Use `gc <binding> initiative` to persist decisions between sessions. The default
binding is `omg`; resolve the installed binding rather than assume agent addresses.
`initiative list` lists durable city-wide records; `show <bead>` returns one.
Records are pinned, unrouted Beads entries. They are not work awaiting an agent.
The command records the originating managed manual or named session at init/launch.
Outside that context pass `--notify <conversation-session-id>`. Use `initiative
watch <bead> --notify <session-id>` when moving the conversation to another session.
Never use an ephemeral worker as the return address.

Start with `initiative init --slug <id> --title <title>`. A managed rig agent uses
its rig, a city agent uses the city. `--rig <name>` selects explicitly; `--rig ''`
selects the city. Documents live in `docs/initiatives/<id>` at that repository
root. Preserve this location when another agent/session resumes. Shared-city
records let either role find pending initiatives across rigs.

Create one living `discussion.md`, updated alongside JSON IR and rendered HTML.
Use Archify from this pack. Choose useful architecture, workflow, sequence,
dataflow or lifecycle views for the initiative; do not default every question to
a workflow diagram or create redundant views. Ask what an agent given only the diagram would build.
Check topology, containment, abstraction, authority and loop meanings. Shared
refinement contains cross-review. Prose cannot repair contradictory topology.
Correct IR and regenerate HTML before presenting it.
Keep JSON/HTML pairs under `visuals/`. Run visual checks on an exact copy of the
delivered HTML under `.omg/` so screenshots and diagnostic sidecars stay out of
the authored docs tree. Do not stash unrelated work or edit repository AGENTS.md
to work around a workflow error; record the error on the work bead or under `.omg/`.

Git provenance is not human acceptance. Older, archived or untracked documents
are reference candidates unless the human establishes their authority for this
initiative. Read the recorded resolutions before raising an already-settled issue.
Investigate discoverable facts before asking a human to supply them. Distinguish
specification decisions from deployment identifiers and external activation
prerequisites. Propose an explicit boundary instead of silently expanding scope.

Use `gc mail send <target> -s <subject> -m <message>` for lightweight clarification.
For substantive delegated review, create a work bead with exact artifact paths,
revision and completion criteria, then `gc sling <target> <bead>`. Persist a verdict
artifact and result path before closure. The requester registers:

```sh
gc session wait "$GC_SESSION_ID" --on-beads "$REVIEW" \
  --note "Review completed; inspect verdict and artifact." --sleep
```

Confirm registration, then yield. This requires a managed controller and does not
block the shell. Registration catches an already-closed bead. After notification,
read the actual result; closure is not approval. Inspect failed delivery with
`gc wait inspect`. Explicit wake/reset may cancel waits; reread state and register
again if necessary. Internal formula steps use targets/dependencies automatically.

## Direction approval

Keep candidates separate from approved files. Commit the exact IR and adjacent
same-stem HTML that the human inspected. Record approval with:

```sh
gc omg initiative direction <bead> --revision <full-commit-sha> \
  --file docs/initiatives/<id>/visuals/workflow.json \
  --file docs/initiatives/<id>/visuals/workflow.html \
  --authority '<human instruction and session/message reference>'
```

Repeat `--file` for every approved pair. Approval binds bytes and Git revision.
The record preserves every approved baseline and identifies its predecessor.
`materialize <bead>` returns frozen direction inputs under `.omg/`, outside docs.
Read approved JSON directly. Summaries fill gaps, never override IR; ignore and
flag conflicts. Ask the human about unspecified material decisions.

For direction changes, show the baseline and separate complete candidate. Pinned
Archify comparison supports architecture only, with stable component/connection
IDs. Other types use separate before/after renders and a human-readable change
summary. Keep all comparison artifacts and receipts outside ingestion. Record
rationale, pending status and eventual decision in eligible Markdown. Rejection
keeps the baseline; reconcile drafts to it. Approval promotes the exact candidate
and invalidates readiness. Reconcile affected docs through shared refinement.

## Authoring and shared refinement

Load the `omg-development` skill before authoring or reviewing the document set.
It defines the shared application/IaC completion boundary and the approved
classification of requirements and acceptance criteria. Specs carry its
`omg-delivery` blocks; snapshot creation validates their exact committed content.
Refinement reconciles prose, ACs and classifications together. A classification
change is substantive and requires review and human acceptance before build.

After direction approval, invoke `generate <bead> --authority '<request>'` once.
For subsequent edits, invoke `refine <bead> --authority '<request>'`. These launch
native `omg-docs` and `omg-refine`. The first extends the second with initial
generation enabled. PM writes PRD, architect writes HLD/needed ADRs, then they
write specs successively. Both initial and later sets enter the SAME refinement.
After interrupted initial authoring, `refine` detects missing discussion/PRD/HLD/spec
types and includes the initial authoring steps to fill gaps and reconcile partial
drafts before review. It preserves existing content and stable IDs. Do not repeat
`generate` or manufacture a complete snapshot from incomplete documents.

Inside refinement, PM assesses whole-set product impact and revises affected
content, architect assesses technical impact and revises successively, then
both receive distinct whole-set cross-review assignments. One writer at a time.
Reviews do not edit documents. The native check repeats this complete process for
required findings. Three automatic passes bound unattended cost; exhaustion
returns the remaining decision to the human, never a false ready result. After
human resolution, start another refinement operation. No third coordinator or
reviewer persona is added.

Before live edits use `revise <bead>` to invalidate readiness. Edits stay draft
until refinement passes. Even unnoticed file changes are rejected by readiness
checks. Presentation-only changes may keep semantic approval only when explicitly
identified as such, but regenerate changed visual evidence before its approval.

## Document-step protocol and human handoff

For every ordinary `omg-docs`/`omg-refine` assignment:

1. Claim with `gc hook --claim --json`. Read the claimed bead, workflow root and
   initiative. Obtain the operation from the root's `gc.var.operation`. If that
   operation has an `interruption`, or the initiative is `needs-human`, skip
   further investigation/writing and go directly to step 4. A later human answer
   does not revive steps already interrupted in the old run.
2. Execute the assigned authoring/review work. Pass `--operation <operation>` to
   state-changing initiative commands. Ordinary required review findings belong
   in `review --verdict required`; the engine repeats revisions and both reviews.
3. If a human choice is actually necessary, run:

   ```sh
   gc omg initiative decision <initiative> --operation <operation> \
     --note '<specific question; evidence; options; recommendation; what it blocks>'
   ```

   A reviewer can instead use `review --verdict human --note ... --artifact ...`.
   Human review evidence can be recorded before a complete snapshot exists; it
   never counts as a passing review. The command records an identified pending
   decision, interrupts the operation and immediately sends mail plus a queued
   nudge to the originating conversation. Preserve an existing pending question
   rather than replacing it with each worker's restatement.
4. Finish ordinary work using:

   ```sh
   gc omg initiative complete-step <initiative> --operation <operation> --step <claimed-bead>
   ```

   For execution errors add `--outcome fail --note '<diagnostics>'`. This command
   derives human interruption from durable state and writes native failure before
   closing the step. Gas City aborts the current scope and preserves teardown.
   For human interruption inside a checked iteration, the command first limits
   the enclosing check's retry budget to the current attempt. The installed
   engine otherwise retries failed scopes even with a hard-failure marker.
   A completed `required` review keeps the ordinary bounded repair budget.
   Do not independently close blocked work as
   a passing no-op. Do not close control beads or the workflow root.

In the originating conversation, a decision notice means **present the question
and recommendation to the human in this turn**. Do not end with only "I'll check"
or a promise to contact another worker. Mail/nudge receipts establish dispatch,
not that the human read the message. Inspect `notifications` and use `initiative
notify <bead>` to retry failed delivery; do not restart the workflow to resend it.

Record the human's answer against the exact pending ID:

```sh
gc omg initiative resolve <initiative> --decision <decision-id> \
  --note '<answer and scope consequences>' --authority '<human message reference>'
```

For an older `needs-human` record without a pending ID, use `--decision legacy`.
Resolution archives the question/answer and clears the active question. It does
not approve direction/specs, edit documents, or restart execution. Reconcile the
discussion and affected IR; obtain new direction approval if the design changed.
Once the interrupted operation settles, use `refine --authority ...` for the
human-authorized continuation. `revise`, `snapshot`, and new launches cannot
silently clear a human gate. `show` exposes the exact state; `list` summarizes it.

Settlement records separate engine `outcome` and semantic `result` values such as
`needs-human`, `approval-ready`, `incomplete`, or `failed`. A finished graph is not
proof that the documents are ready. The final handoff notifies the conversation
with the result and next action; it cannot overwrite a newer decision or resolution.

Example: a missing backup destination first calls for source investigation. If
the real choice is whether backup provisioning belongs in this delivery, present
that scope choice and the proposed activation prerequisite. Record the answer,
revise the boundary and acceptance evidence, then repeat whole-set refinement.

## Document contract and publication

Before authoring, revising, approving or publishing an eligible Markdown document,
load `hindsight-shipping` from the city's separately imported Hindsight pack.
That skill and its `schemas/docs/derive` validator are the source of truth for
document format, frontmatter, identity, tagging, approval provenance, revision,
retirement and ingestion. Follow the installed Hindsight contract; do not invent
or maintain a separate OMG frontmatter dialect. If the reference is unavailable,
surface the missing dependency rather than guessing its requirements.

OMG defines the documents' purpose and substantive content:

- Discussion records rationale, constraints, open questions and current decisions.
- PRD defines users, problem, goals, scope/exclusions, stable requirements and
  acceptance evidence. Use measurable targets only when supported.
- HLD defines boundaries, components/interactions, data ownership, failure
  behavior, deployment, security constraints and consequential tradeoffs.
- ADR records a consequential decision, context, alternatives, rationale,
  consequences and any observable revisit trigger. Do not create one per trivial
  choice. Specs link relevant ADRs.
- Specs identify stable requirement IDs, observable behavior, interfaces, data
  shapes, errors, compatibility/migration, affected rigs and dependency order,
  exclusions and verification obligations. Preserve product intent from the PRD.
- Reports follow the build-report contract below.

Keep eligible authored Markdown directly in the initiative directory, with specs
and ADR subdirectories as useful, and reports under `reports/`. Keep raw reviews,
execution artifacts and receipts under `.omg/`, never `docs/`. JSON/HTML visuals
may live under `visuals/`; they are never attached to an ingestion request. Do not
copy raw chat, mail or bead chatter into a summary in place of authoring it.

Validate and ship using the procedures in `hindsight-shipping` and the Hindsight
pack's publication contract. Use the repository's agreed Git publication policy
to get the intended revisions onto its canonical remote ref. The existing
Hindsight pipeline owns ingestion and its completion receipts. Publication and
ingestion do not approve scope or initiate a build.

## Spec approval and explicit build initiation

`ready` requires passing product and technical reviews for the exact unchanged
snapshot. Tell the human where to read it; keep the record idle while they decide.
On explicit approval, use `accept <bead> --authority '<instruction/reference>'`.
Acceptance never launches work. Apply the human-approval frontmatter rules from
`hindsight-shipping` to the exact approved revisions, then validate and publish
them through that contract. Preserve document identity and substantive content;
metadata publication is not permission to rewrite approved requirements.

You may now suggest a build. Only an explicit human request permits:

```sh
gc omg initiative start <bead> --rig <build-rig> \
  --authority '<explicit build request and session/message reference>'
```

City initiatives stay in city docs. Select the rig being built; launch other
rigs only when the human requests them, respecting approved dependency ordering.
Do not infer that starting one rig authorizes every rig. Hindsight ingestion is
independent. Discuss `--push true` and `--open-pr true` separately when applicable;
the build defaults leave code and the build report local.

Start checks the required local tools and freezes the approved spec bytes. It
writes baseline.json under an operation-specific absolute artifact root, records
durable intent, then slings the standalone OMG build to the target rig. The
`omg-build` skill defines planning, decomposition, builder, tester and reviewer
assignments. `gc omg verify` checks execution records using Bash, yq and jq.
Hindsight continues to own published document formats. Repeated starts for
the same rig and approved snapshot return the saved operation. An ambiguous launch
is not retried blindly. Inspect its source bead/native graph and use `recover`
with the matching existing workflow. If no workflow exists, investigate the
recorded error and confirm the launcher and all its child processes have exited.
Only then, on the human's instruction, run:

```sh
gc omg initiative abandon <bead> --operation <key> --launcher-stopped \
  --note '<why the launch failed; how its termination was confirmed>' \
  --authority '<human instruction and session/message reference>'
```

The command checks the exact launch store, including closed and partial work.
Existing workflow evidence requires recovery, not abandonment. Store errors or
concurrent state changes prevent abandonment. For a city with a relocated graph
store, it refuses to infer absence from a partial or cached listing; inspect the
native storage state instead. Keep any orphan source bead identified in the
abandoned operation for inspection; it is not authorization to implement work.

The abandoned attempt remains in history. A subsequent explicit human launch
request can create a new operation; abandonment itself never dispatches work.
Do not abandon an operation while its original launcher could still complete.
Never use force replacement to hide uncertainty. Native state owns graph
execution; OMG stores decision and launch receipts only.

For a settled failed build against unchanged approved specs, an explicit
`initiative start <bead> --retry <failed-operation> --authority '<human retry request>'`
creates a new attempt with separate artifacts. It verifies the prior native root
is terminal and failed. Repeating the same retry request returns its receipt;
it never reopens the old graph or overwrites its evidence. If the approved snapshot
changed, use ordinary `start` after the new acceptance instead. A retry inherits
the failed attempt's `--push`/`--open-pr` authorization; asking for a different
publication on a retry is refused. Present that as a separate request to the human.

## Build report

Reconcile implementation against pinned specs before native finalization.
After settlement, the architect writes the report for successful, partial, failed
and blocked outcomes, including when native finalization or publication failed.
The report identifies initiative, launch operation, approved direction and spec
commit/digest, assessed code SHA, and each stable requirement's implemented,
partial, deferred or blocked outcome. Cite implementation and verification
evidence. Explain deviations, reasons and decision authority; reporting an
unauthorized deviation does not approve it. Name unresolved risks and follow-up.

Distinguish implemented, reviewed, and actually published/integrated code. Do not
imply merge or post-merge verification without evidence. A build root may close
before post-settlement reporting finishes. Check the report work bead separately.
Commit the Markdown report alone (`git commit --only -- <path>`) in the initiative
repository even when the build failed; the report step is checked (`verify --stage
report`) and completes with that local commit. Report publication is authorized
only by a passed build's own finalized publication receipt, to exactly its
published ref, and only when the initiative repository is the rig checkout that
receipt published; a distinct docs repository or an unpublished, failed or
canceled build keeps the report local. `gc omg report publish` does the remote
work under the worker's Git identity; the controller check is offline. If
authorized publication fails, preserve the local commit, error and recoverable
reporting bead. Hindsight retrieves accepted direction separately from
implementation evidence.
