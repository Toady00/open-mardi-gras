# Proposed OMG process

These charts began as working proposals for discussion and now include the
owner's implementation-session clarification: spec approval does not launch a
build. The human explicitly requests initiation through an agent. The pack's
[README](../../README.md) describes implementation and verification status.
The charts were generated with this pack's pinned Archify skill.
Open the HTML files locally; each is self-contained. The adjacent JSON files
are their editable sources.

For a new session, read the [discussion summary](discussion-summary.md) alongside
the three JSON IR files. The summary records rationale and open choices; the IR
remains primary.

## Start here

| View | HTML | Source | Question it answers |
| --- | --- | --- | --- |
| Workflow | [workflow.html](workflow.html) | [workflow.json](workflow.json) | When do we discuss, approve, author, build, and publish? |
| Agent collaboration | [collaboration.html](collaboration.html) | [collaboration.json](collaboration.json) | How does one agent involve the other and receive a durable result? |
| Artifact and memory flow | [artifacts.html](artifacts.html) | [artifacts.json](artifacts.json) | What enters Hindsight, and what remains outside it? |

The workflow is an overview. Its cards explain revision paths and failure
requirements that are not separate branches in the main drawing. The sequence
shows a PM-led example; an architect-led conversation is equally valid. Mail
and tracked review are distinct examples, not required steps on every turn.

## Requirements reflected in the charts

- Human conversation and visual iteration come before the documentation formula.
- The approved JSON IR is the primary record of agreed direction. The HTML is
  its visual representation; approval binds the exact IR revision rendered.
  The documentation formula reads that IR directly.
- Archify JSON and HTML are entirely outside Hindsight ingestion, even if stored
  in Git. Neither is retained indirectly as an attachment.
- An authored Markdown discussion summary is eligible for Hindsight. Raw chats,
  agent mail, and bead status chatter are not substitutes for that summary.
  Capture the summary alongside visual iteration, not as a replacement for the
  IR afterward. It fills gaps; conflicting claims cannot override approved IR.
  Ignore those conflicting claims and flag them for correction. If the IR leaves
  a material decision unspecified, ask rather than infer approval.
- PM and architect can retrieve relevant project and platform context from
  Hindsight. They still consult current documents and code when exact facts
  matter. Hindsight is derived memory; Git is the document authority.
- The documentation formula produces PRDs, HLDs, necessary ADRs, and specs.
  Initial generation occurs once per initiative and always enters the shared
  refinement process. Every later substantive edit uses that same process.
  Approved specs become the input to planning and work decomposition.
- Documents can ship repeatedly while draft and again after acceptance. Shipping
  and human approval are separate. Multiple initiatives can await approval for
  an arbitrary time without keeping their authoring agents occupied.
- The final build report explains what was actually built against the approved
  spec revision, what deviated, and why. It is eligible for Hindsight too.

This index is a review aid, not a formally published discussion record. No
Hindsight shipping configuration or ingestion action is added by these charts.

## Proposed collaboration contract

Use `gc mail send` for a lightweight question, clarification, or result pointer.
Mail is durable communication. It does not, by itself, establish a review
obligation with completion criteria.

For substantive delegated work, create a work bead with the artifact paths and
completion criteria, then route it with `gc sling`. The reviewer writes its
result to the designated artifact, records the result on the bead, and completes
the work. Slinging alone does not arrange a return notification to the requester.
The requesting managed session registers a durable bead wait and yields:

```sh
gc session wait "$GC_SESSION_ID" \
  --on-beads "$REVIEW" \
  --note "Review completed; inspect its verdict and artifact." \
  --sleep
```

Here `REVIEW` is the delegated work bead ID. Gas City's controller checks its
completion and queues a notification to resume the waiting session. The PM does
not poll. Registration also checks whether the bead already closed, so a fast
review does not lose the notification.

`--sleep` requires a managed controller. The command registers the wait and
returns; it does not block the shell until review completion. The resumed agent
checks the actual verdict and artifact, since bead closure does not mean the
review approved the proposal. Notification delivery can fail and has its own
durable state, inspectable through `gc wait inspect`.

Waits belong to a session continuation. Explicitly waking or resetting the
session can cancel a stale wait. A resumed conversation must reread the review
bead and register a new wait if necessary. Optional mail can announce a result,
but it is not required for the normal completion path. A transient nudge alone
is not the record of the request or decision.

Inside the documentation formula, step targets and dependencies handle routing.
Launch the formula once; do not manually sling each internal step. No additional
TPM or coordinator agent is proposed. Exact agent addresses depend on the pack's
import binding and city or rig context.

## One shared refinement process

Initial generation is not a separate, weaker documentation standard. PM writes
the PRD, architect writes the HLD and necessary ADRs, and they write specs in
successive steps. That initial set always enters refinement, even when no change
request is supplied. Later substantive edits enter the same process directly;
they do not regenerate the initiative from scratch.

1. Review the whole set for impact, alignment, and completeness against the
   approved direction and binding requirements.
2. Identify justified corrections or propose a separate candidate IR when the
   direction needs to change. Keep pending proposals distinct from approved scope.
3. Revise the affected documents, with one writer at a time.
4. Assign distinct cross-review using both the PM's product lens and the
   architect's technical lens across the whole set, not just each role's own docs.
5. Resolve justified required findings through the same loop. Return an unresolved
   decision to the human, or mark the exact reviewed revision approval-ready.

Cross-review is a distinct assignment inside refinement, not a peer process or
a third dedicated reviewer persona. Separate-session isolation is not a committed requirement. Existing GC
targets and formula dependencies route the work; this adds no orchestrator and
does not require manually slinging each internal step.

PM and architect may edit candidate IR and draft documents live during discussion.
They may publish those drafts, but cannot call the revised set approval-ready
until shared refinement, including cross-review, passes. Readiness belongs only to the
exact reviewed revision. Any later substantive edit invalidates it and returns
the set to this same refinement process. Candidate IR approval also requires
reconciling affected documents before readiness can be established again.

## Instruction requirement: diagrams must express the intended process

The JSON IR is the primary collaboration artifact and record of approved
direction. Another agent must be able to interpret its visual representation
without this conversation correcting its meaning. Supporting prose may explain
omitted detail; it cannot contradict or repair the topology.

Keep each diagram at a consistent level of abstraction. A process and one of its
internal activities must not appear as peer stages. Show internal activities
inside their owning process, describe them in its details, or create a separate
expanded view when that detail earns its cost. Edges assert real relationships,
not merely reading order or visual convenience.

The observed failure here was drawing shared refinement and cross-review as
separate nodes with a revised-set arrow and a required-fixes return arrow. That
topology described two collaborating processes, despite our intent that review
is part of refinement. The correction is one refinement stage containing
assessment, revision, and cross-review.

Before presenting an IR revision, review what an agent given only that diagram
would build. Check process boundaries, containment, entry and exit conditions,
authority, and the meaning of loops. If that interpretation differs from the
intended workflow, correct the IR and regenerate the HTML. Do not explain away
the mismatch in a card or discussion summary.

Carry this observed failure and rule into the upcoming handoff summary and the
OMG instructions it calls for. This section records the instruction requirement;
it does not itself modify an agent or the vendored Archify skill.

## Cost and stop rule

The pack-wide governing requirement is to ship useful, sufficiently reliable
software. Every substantive recommendation must weigh the credible cost of
omission under expected conditions against implementation complexity, delay,
and ongoing maintenance. Apply the same test to this workflow's own review and
coordination overhead. Hypothetical possibility alone is not a blocker.

| Finding disposition | Obligation |
| --- | --- |
| Required before shipping | Justify against expected conditions and binding requirements; blocks refinement completion until resolved. |
| Optional, nonblocking | Useful improvement, not a condition of readiness or shipping. |
| Deferred | Record an observable revisit trigger in the relevant docs or ADRs. |
| Rejected | No implementation obligation. |

Only justified required findings block completion, not every imaginable
improvement. Existing requirements remain binding unless the human changes scope;
the cost rule does not silently waive them. A required issue that needs a scope
decision goes back to the human rather than being relabeled to claim readiness.

Document deferrals and their rationale in relevant documents or ADRs and ship
that prose through Hindsight. There is no mandatory bead for each hypothetical.
Use quantified thresholds only when evidence supports them. A trigger calls for
reassessment, not automatic implementation. These rules bound the review loop;
they do not promise risk-free software or unlimited review.

## Proposed approvals and publication

The two main human checkpoints are approval of direction and approval of specs.
Between them, initial generation and all later edits use shared refinement. Proposed
changes to the agreed IR have their own visual approval loop; they do not
silently change the baseline or bypass the final spec checkpoint.

### Proposed IR changes during documentation

During discussion or refinement, PM and architect may discover missing
interactions, constraints, or other justified changes to the visual model. They
may edit a separate, complete candidate JSON IR and draft docs live, explaining
the proposed changes. They do not overwrite approved IR or bypass shared review.

Preserve the exact original IR revision approved to start the formula. The
human can compare that baseline with the candidate, inspect its rendered view,
and approve or reject the change. Approval records the exact candidate revision
as the new approved baseline while retaining the original. Rejection keeps the
existing baseline; the agents revise the proposal or bring the docs back into
agreement with it. Each review must identify which approved baseline it changes.

After approval, reconcile affected docs against the new baseline. Approving an
IR change is not approval of the finished specs and does not dispatch a build.
Draft documents may discuss pending changes and ship to Hindsight while awaiting
review, but must distinguish those proposals from the approved direction.

Pinned Archify v2.16 supports a visual Before / Delta / After viewer through
`compare architecture`. It compares two complete architecture IRs and requires
stable IDs on both components and connections. It does not infer implementation
impact or whether a change is safe.

That comparison command does not support workflow, sequence, dataflow, or
lifecycle diagrams. For those types, including the three charts in this directory,
the proposed fallback is separate before/after renders plus a human-readable
change summary. There is no custom diff implementation in this pack.

All baseline/candidate JSON, rendered HTML, and all diff evidence, including
comparison HTML, receipts, and screenshots, remain outside Hindsight. Capture the substantive proposed change,
rationale, and eventual decision in eligible Markdown so memory can distinguish
a pending proposal from an accepted change without reading the diagrams.

### Repeated shipping and delayed approval

The discussion summary can publish during exploration and refinement. Each generated document
can publish with `status: draft`, and every subsequent published revision can
ship again under the same stable document ID. Hindsight replaces that document's
representation rather than treating each revision as a separate document.

The documentation formula ends in a persistent human approval queue once shared
refinement passes for the exact revision. An unresolved decision instead returns
to the human, not a false approval-ready result. The human may later batch selected
revisions across different sessions and initiatives, without keeping agents busy.
Acceptance updates the selected documents to
`status: accepted` and republishes them. The human separately requests initiation
of the corresponding build workflows through an agent. Approval and Hindsight
ingestion do not launch a build.

Publication means eligible Markdown reaches the configured remote canonical Git
ref, not merely a local commit. The existing Hindsight pack handles shipping and
receipts. Approval is independent of ingestion; publication throughout refinement
does not approve a candidate, establish readiness, or authorize a build.

The intended retrieval distinctions are:

| Published evidence | What agents should learn |
| --- | --- |
| Draft document | A tentative proposal touches this area; do not mistake it for settled direction. |
| Accepted document | There is an approved direction, not proof of implementation. |
| Build report | Evidence of what was implemented at the stated revision, including deviations and unfinished work. |

A missing report leaves implementation unconfirmed; it does not prove no code
exists. A report also does not prove its code is still the latest state forever.
Current code and survey evidence remain relevant. These are retrieval
requirements, not a claim that the shipper enforces exact response wording.

## Build-report contract

The report should identify the approved spec baseline and the code revision it
assesses. For each requirement, it should distinguish implemented, partial,
deferred, and blocked outcomes, with supporting implementation and verification
evidence. Every deviation needs a reason and its decision authority; describing
an unapproved deviation does not retroactively approve it.

The current standalone `omg-build` formula owns planning, implementation, testing,
review and reconciliation. Gas City schedules its post-settlement report even
when the build fails before finalization. The original diagrams are proposal
artifacts; the current executable flow is mapped in the repository-root
`omg_flowchart.md` and generated HTML.

The normal path in the workflow chart shows reconciliation before finalization
and report publication. Partial, blocked, and failed outcomes also need a report.
The implementation must provide that path even when normal finalization cannot
complete. A report must distinguish implemented, reviewed, and actually published
code; it must not imply post-merge verification that never happened.

## Implementation choices

- Conversation is the human review interface; pinned city-work-store Beads records
  retain exact revisions across sessions. Pack commands support agent operations.
- Initiative documents live in the initiating rig or city's
  `docs/initiatives/<id>`. Existing Hindsight scans those canonical Git docs trees.
- Lightweight clarification uses mail; substantive delegated review uses a work
  bead and durable result artifact. Internal steps route through native formulas.
- Initial generation and later changes use one native checked refinement scope,
  with three automatic attempts before an unresolved decision returns to the human.
- Separate-session isolation remains optional. Both roles receive distinct
  whole-set review assignments; no third persona is introduced.
- Spec approval does not launch implementation. A separate explicit human request
  records launch intent before native dispatch. Repeated starts reuse the saved
  operation; ambiguous acknowledgement requires native-state inspection/recovery.
- `omg-build` plans directly from pinned specs using OMG-owned worker instructions
  and Bash/yq/jq checks. The architect authors the post-settlement report for every
  outcome. See [implementation decisions](../implementation-decisions.md) for the
  September 14 replacement of the earlier official-pack integration.
- Non-architecture comparison still uses before/after renders and authored change
  rationale. Known renderer defects remain as documented in the historical summary.

See the pack README for verification coverage and the live-city rehearsal boundary.

## Evidence behind the proposal

The mechanisms were checked against these local sources, rather than inferred
from the old OpenCode workflow:

- Gas City engine, `~/code/clones/gascity/main`: communication tutorial,
  `cmd/gc/cmd_sling.go`, `cmd/gc/cmd_wait.go`, and the formula v2 specification.
- Official pack, `~/code/clones/gascity-packs/gascity`:
  `formulas/build-from-plan-base.formula.toml`, the inherited build/review
  formulas, finalization instructions, and `schemas/build/final-report.v1.yaml`.
- Hindsight pack, `~/code/stacked-chips-v2/hindsight`: shipping contract,
  `schemas/docs/validate.py`, Git Markdown snapshot collector, and shared
  Hindsight read-access fragments.

All three charts passed Archify's nine showcase artifact checks with no errors
or warnings. Browser checks passed at 1440×900, 1600×1000, 1920×1080, and
2048×1320 without overflow after one card-copy correction round. Image review
covered light and dark screenshots at the smallest and largest sizes. Browser
receipts bind temporary copies to the exact SHA-256 of the delivered HTML.
Those checks do not establish perceptual clarity or your approval of the process.
The owner subsequently found tangled connectors and overlapping node icons.
One workflow detour was corrected, but routing and icon defects remain; see the
discussion summary's known visual limitations. Earlier visual-pass claims were
too generous.

Generation and validation use `gascity/skills/archify/bin/archify.mjs`, not a
globally installed Archify runtime. For each source, run `validate` with its
diagram type and `--quality showcase --json`, then `deliver` to the adjacent
HTML with those same options. Run `visual-check` on an exact temporary HTML copy
to keep screenshots and receipts outside this documentation directory.

These documents capture the process and its discussion handoff. The pack now
implements the workflow with native formulas and conversational initiative
records; see the pack README for setup, commands and verification limits.
