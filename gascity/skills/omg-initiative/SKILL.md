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

Start with `initiative init --slug <id> --title <title>`. A managed rig agent uses
its rig, a city agent uses the city. `--rig <name>` selects explicitly; `--rig ''`
selects the city. Documents live in `docs/initiatives/<id>` at that repository
root. Preserve this location when another agent/session resumes. Shared-city
records let either role find pending initiatives across rigs.

Create one living `discussion.md`, updated alongside JSON IR and rendered HTML.
Use Archify from this pack. Ask what an agent given only the diagram would build.
Check topology, containment, abstraction, authority and loop meanings. Shared
refinement contains cross-review. Prose cannot repair contradictory topology.
Correct IR and regenerate HTML before presenting it.

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

After direction approval, invoke `generate <bead> --authority '<request>'` once.
For subsequent edits, invoke `refine <bead> --authority '<request>'`. These launch
native `omg-docs` and `omg-refine`. The first extends the second with initial
generation enabled. PM writes PRD, architect writes HLD/needed ADRs, then they
write specs successively. Both initial and later sets enter the SAME refinement.

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

Record an unresolved decision with `decision <bead> --note ...`; never keep an
authoring session busy awaiting the human. Formula handoff persists the outcome.
When the human returns, retrieve it and resume discussion. A human can review
several initiatives and accept selected exact revisions separately.

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
the native build defaults leave code local.

Start first runs `prepare-build` to verify the build roles and native validator
and install its local compatibility wrapper. If it fails, surface the preparation
error; no launch intent or source bead was created. The human can select a Python
environment with PyYAML using `gc omg prepare-build --rig <rig> --python <path>`.
That selection is remembered for later preparations. Use the preparation command
instead of copying upstream scripts or bypassing their checks.

After preparation, start freezes the approved spec inputs, records durable intent, then slings the
native OMG build continuation to the target rig. It plans implementation,
decomposes, builds and reviews using official Gas City roles. Repeated starts for
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
Persist and publish the Markdown report even when the build failed; if report
publication fails, preserve the artifact, error and recoverable reporting bead.
Hindsight retrieves accepted direction separately from implementation evidence.
