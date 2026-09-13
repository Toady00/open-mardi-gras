---
schema_version: 2
id: discussion.omg.visual-docs-workflow
type: discussion
title: OMG visual collaboration, document refinement, and build handoff
status: draft
source: agent
scope: platform
created_at: 2026-09-13T20:27:28Z
updated_at: 2026-09-13T20:27:28Z
---

# OMG visual collaboration, document refinement, and build handoff

> Historical handoff, followed by implementation-session clarification. The owner
> subsequently specified that conversation is the approval interface, initiative
> docs live in the initiating rig or city's `docs/initiatives/<id>`, and builds
> start only on a separate explicit human request. Approval does not launch work.
> See [implementation decisions](../implementation-decisions.md) and the
> [pack README](../../README.md). The accompanying IR now reflects that clarification.

## Purpose and standing

This is an agent-authored summary of the owner's discussion about the Gas City
OMG pack. It accompanies the JSON IR for a different session to design and
implement the agreed capabilities. It records agreements, rationale, known
limitations, and unresolved implementation choices. It is not a completed spec,
a build report, or evidence that the proposed workflow exists.

Read these primary artifacts with this summary:

- [Workflow IR](workflow.json) and [rendered workflow](workflow.html).
- [Collaboration IR](collaboration.json) and [rendered sequence](collaboration.html).
- [Artifact-flow IR](artifacts.json) and [rendered dataflow](artifacts.html).

**The JSON IR is primary.** This summary fills gaps; it does not override the IR.
If a statement conflicts with the IR, disregard the conflicting statement and
surface the discrepancy for correction. Do not use prose to quietly reinterpret
the diagram. The latest artifacts remain working proposals; this summary does
not manufacture a formal approval of their exact revisions.

## Problem and intended outcome

The owner wants to discuss an initiative with a PM and/or architect, inspect
visual models until the direction is understood, and then have the agents
produce buildable documents. Approved specs should feed Gas City's native work
planning and execution. Durable documents and outcome reports should inform
future work through Hindsight.

The process must support many initiatives and conversations without requiring
immediate human approval. It must also favor shipping useful software over
endless agent-generated improvements.

Success means the owner can recognize and approve the intended behavior in the
visuals; a new session can continue without the original chat; initial and later
document changes meet the same review standard; and a final report explains
what was built versus what was specified. No numerical performance targets for
this workflow were agreed.

## Repository context and current state

`gascity/` is the OMG Gas City pack root. It may become a standalone repository
later, so its resources should not depend on this parent repository. The older
OpenCode product in `opencode/` is reference material, not the workflow to port
mechanically. `.opencode/` is the local harness, not the product destination.

The Gas City pack currently contains PM and architect personas, pinned Archify,
pack documentation, licenses, and these exploratory charts. The documentation,
refinement, approval, and build-report workflows discussed here are not yet
implemented. Neither are the pack's Hindsight dependency and agent read wiring.

Relevant local sources:

| Source | Location |
| --- | --- |
| Gas City engine | `~/code/clones/gascity/main` |
| Official methodology pack found during inspection | `~/code/clones/gascity-packs/gascity` |
| Hindsight pack | `~/code/stacked-chips-v2/hindsight` |

Verify these checkouts and their current contracts before implementation. Prefer
native Gas City conventions. Do not recreate an OpenCode foreman or introduce a
custom orchestration layer merely to preserve the old workflow.

## Agreed process

### 1. Human-led visual exploration

The owner talks to the PM or architect. Either role can lead and involve the
other. Continuity belongs to the initiative's artifacts and durable work state,
not to the survival of one session.

Both agents need read access to relevant project and platform context in
Hindsight. Recalled context does not replace checking current code and documents
when exact facts matter. A current-state survey is useful evidence, not an
automatic prerequisite for every conversation.

Agents author JSON IR, render it to HTML, and capture a supplementary Markdown
discussion summary during the conversation. The summary records rationale,
constraints, unresolved questions, and context not fully expressed by the IR.
It is not a replacement input invented after the visuals are approved.

The human inspects HTML representing an exact JSON revision. Approval of that
direction binds the corresponding IR revision, which the documentation formula
must read directly.

### 2. Initial generation, then one shared refinement process

Initial document generation runs once per initiative. It produces the appropriate
PRD, HLD, necessary ADRs, and specs, then always enters refinement. Later
substantive changes enter that same refinement process without recreating the
whole document set.

Refinement includes all of the following:

- Assess whole-set alignment, completeness, and the impact of changes.
- Identify justified corrections and decisions requiring human input.
- Revise affected documents and propose candidate IR when needed.
- Cross-review with the PM's product judgment and architect's technical judgment.
- Resolve justified required findings or return an unresolved decision to the
  human. Only then call the exact reviewed set approval-ready.

**Cross-review is internal to refinement, not another peer process after it.**
Both lenses apply across the document set, not just the modified files. This is
an impact review followed by focused corrections, not mandatory rewriting of
every document. Use one writer per artifact at a time.

There is no third dedicated reviewer or TPM persona in the agreed starting
design. Review should be a distinct assignment within refinement. Fresh-session
isolation may be useful, but was not committed as a requirement.

PM and architect may directly edit candidate IR and draft documents during a
conversation. They may not claim the changed document set is approval-ready
until it has passed shared refinement. Substantive edits invalidate earlier
readiness. Presentation-only changes may avoid document reconciliation if they
truly change no meaning; make that distinction explicit.

### 3. Candidate IR and human change review

Document work may reveal missing behavior or a better proposal. Agents write a
separate full candidate IR rather than overwrite the approved baseline. Preserve
the original revision approved to start generation and identify the baseline
against which each later proposal is reviewed.

The human reviews the candidate's rendering and changes, discussing issues with
the PM or architect leading the initiative. That conversation can revise the
candidate and the documents. Approval promotes the exact reviewed candidate to
the new approved baseline; rejection retains the existing baseline.

Affected documents must be reconciled through the shared refinement process.
Candidate IR approval does not approve the finished specs or authorize a build.
Pending proposals may appear in published drafts, but must be distinguished from
approved direction. A summary cannot override IR, and an unspecified material
decision is not permission for an agent to invent approval.

### 4. Deferred human approval and build release

Once refinement passes, authoring can finish and leave a durable approval-ready
record. It must not keep agents busy waiting for the owner. The owner may return
much later and approve selected revisions from multiple sessions or initiatives.

Final spec approval is separate from visual direction approval and intermediate
IR-change approval. Acceptance publishes the selected documents with
`status: accepted` and releases the corresponding native build workflows.
Draft publication alone never authorizes execution.

The exact approval interface, record, and duplicate-dispatch prevention are not
designed yet. Do not assume a metadata status change by itself is already an
implemented build trigger.

## Cost and stopping rule: ship good software

This is a pack-wide instruction requirement, not an architect-only preference:

> Optimize for shipping useful, sufficiently reliable software. Every proposed
> change has an implementation cost, an ongoing cost, and a cost of omission.
> Require justification proportionate to those costs. A conceivable failure is
> not, by itself, a reason to prevent shipping.

For a substantive recommendation, explain what happens if nothing changes,
why that consequence is credible under expected conditions, what addressing it
costs, and why it warrants action now. Keep the explanation proportional; this
is not a demand for another formal document per finding.

| Disposition | Effect |
| --- | --- |
| Required before shipping | A justified requirement violation or unacceptable credible risk blocks readiness until resolved. |
| Optional improvement | Does not block approval or shipping. |
| Deferred with a trigger | Record why the current approach suffices and when to reconsider. |
| Rejected | Does not earn its cost; no obligation to implement later. |

Only justified required findings keep refinement running. The process does not
wait for reviewers to exhaust every imaginable improvement. Existing requirements
remain binding unless the human changes scope; agents cannot relabel a violation
as optional to manufacture a pass.

Record useful deferrals in the relevant document or ADR. For example, reconsider
a capacity measure when observed traffic reaches a justified threshold or agreed
latency targets are repeatedly missed. Do not invent precise thresholds without
evidence. A trigger prompts reassessment, not automatic implementation of the old
suggestion. Do not create a mandatory backlog bead for every hypothetical.

Apply this same test to added agents, documents, gates, scripts, and review passes.
The owner rejected the newly introduced Bats tests and recipe for the vendoring
helper. They were removed. Do not reintroduce an unfamiliar framework or extra
machinery without evidence it earns its cost; use established pack conventions.

## Native collaboration and durable completion

The proposed division of tools, grounded in the inspected engine, is:

- `gc mail send` for lightweight questions, clarification, and result pointers.
  Mail is durable communication, not a tracked review obligation.
- A work bead routed with `gc sling` for substantive delegated work with artifact
  paths and completion criteria.
- Formula targets and dependencies for internal workflow steps. Launch the
  formula, rather than manually sling every internal handoff.

For an ad hoc review, sling alone does not arrange the requesting PM's return.
The proposed managed-session pattern registers a durable wait and yields:

```sh
gc session wait "$GC_SESSION_ID" \
  --on-beads "$REVIEW" \
  --note "Review completed; inspect its verdict and artifact." \
  --sleep
```

`REVIEW` is the delegated bead ID. The controller reconciles the dependency and
queues a completion notification; the PM does not poll. Registration checks for
an already-completed bead. The reviewer persists its result and path before
closing the work. The resumed PM reads the verdict and artifact, because closure
does not mean approval.

`--sleep` requires a managed controller and registers a wait rather than blocking
the shell. Waits are tied to a session continuation; explicit wake/reset can
cancel them. Recovery rereads work state and re-registers when needed. Notification
delivery has its own inspectable status. A transient nudge is not the authoritative
work record. These mechanics were source-inspected, not exercised as a live OMG
end-to-end workflow in this session.

## Hindsight scope, identity, and repeated publication

Eligible authored Markdown includes discussion summaries, PRDs, HLDs, ADRs, specs,
and final build reports. JSON IR, rendered HTML, comparison HTML, screenshots,
and other visual evidence or receipts are entirely outside Hindsight, including
indirect retention as attachments. Raw chat, mail, and bead chatter are not the
discussion summary.

The working recommendation is one living summary per initiative with a stable
ID, updated during exploration and refinement. Keep current conclusions distinct
from rejected or superseded proposals; preserve lasting decisions in appropriate
ADRs rather than only in the summary. Do not create a new summary for every turn.
This record uses `discussion.omg.visual-docs-workflow`; retain that ID on updates.

Documents can ship as drafts as soon as published and ship again after every
subsequent published content/status change. The current Hindsight pack uses the
same document ID to replace the memory representation, not create duplicate
documents for each revision. Git retains the source history.

Shipping depends on eligible Markdown reaching the configured remote canonical
Git ref, not merely a local commit. It is independent of human approval and may
occur throughout generation and refinement. Use the Hindsight pack's existing
pipeline and receipts rather than duplicating ingestion in OMG.

The intended retrieval distinction is:

| Published evidence | What a future agent should understand |
| --- | --- |
| Draft | A tentative proposal touches this area. |
| Accepted | An approved direction exists, not proof it was implemented. |
| Build report | What was built at the stated revision, including divergence from intent. |

A missing report means implementation is unconfirmed, not proof no code exists.
A report is also not a forever-current description; current code and survey
evidence still matter. These are retrieval requirements, not claims that the
shipper itself guarantees particular response wording.

Use the current Hindsight pack's schema. Its statuses include `draft`, `accepted`,
`superseded`, and `deprecated`; it supports `discussion`, `prd`, `hld`, `adr`,
`spec`, and `build-report`. Older OMG templates have incompatible schema/status
conventions and must not be copied unchanged. This summary is `source: agent`
and `status: draft` because this authored record has not yet been human-reviewed.
It has not been shipped to Hindsight by this session.

## Native build reuse and final report

Approved specs are the execution contract. Native Gas City planning may still
need to produce an implementation plan before decomposition; a spec and a plan
are not automatically interchangeable.

Reuse official build components where they fit. The owner explicitly permits an
OMG-derived formula if needed, including inheritance from `build-from-plan-base`
or another appropriate continuation. The exact base and extension are open.

A final build report is required, not merely a list of changed files. It should:

- Identify the approved spec baseline and the code revision assessed.
- Account for implemented, partial, deferred, and blocked requirements.
- Explain deviations, reasons, and decision authority.
- Reference implementation and verification evidence and unresolved risks.
- Distinguish work implemented, reviewed, and actually published or integrated.

The inspected native chain already summarizes implementation, reviews/repairs,
finalizes, and publishes. Adding reconciliation before finalization is a candidate
extension point, not the settled design. Reporting must also cover unsuccessful
or blocked outcomes where normal finalization cannot complete. Do not imply
post-merge verification without evidence or treat a report as retroactive approval
of an unauthorized deviation. Publish the Markdown report through Hindsight.

## Archify packaging and capability limits

Archify is vendored as the unmodified upstream `archify/` subtree in
`gascity/skills/archify/`, pinned through `gascity/upstream/archify.json`. The
initial pin is upstream `v2.16.0`, commit
`c826e6c3a7abad19c0f3cd1ca57207d54b1ad8de`.

The maintainer edits the pin and runs `just archify-sync`. It deletes the existing
skill directory before fetching and replaces the entire subtree, removing stale
files and local edits. Failures leave it absent or incomplete for a manual rerun
or Git restoration. There is no rollback, auto-update, or auto-commit. This order
was explicitly chosen for a maintainer's Git-tracked development checkout.

Keep OMG-specific instructions outside the upstream snapshot. Preserve upstream
licenses and review bundled asset terms; not every brand asset shares the code's
MIT license. The subtree includes development files whose full test commands
depend on the parent upstream repository. Do not claim it is upstream's filtered
release package or run installations into it casually.

Pinned Archify supports `compare architecture` with complete before/after IRs,
stable component and connection IDs, and a Before / Delta / After viewer.
It does not compare workflow, sequence, dataflow, or lifecycle diagrams. For
those types, separate before/after renders plus a change summary were proposed.
No custom comparison implementation was requested or built.

## Instruction lesson: visual semantics are the contract

The owner repeatedly emphasized that agents will implement what the IR depicts,
not the intentions hidden in this conversation. Keep abstraction levels consistent.
A process and one of its internal activities must not appear as peer stages.
Show internal detail inside its owner or in a separate expanded view when useful.

The concrete mistake was drawing refinement and cross-review as separate nodes
with a revised-set arrow and required-fixes return loop. That represented two
processes. The corrected workflow has one refinement stage containing assessment,
revision, and cross-review. The summary must not reintroduce the old distinction.

Future OMG authoring instructions should require this check: **What would an agent
build if this diagram were its only input?** If the answer differs from intended
behavior, correct the IR and regenerate the HTML. Prose cannot repair conflicting
topology. Review containment, authority, entry/exit conditions, and loop meanings
as well as visual polish. This rule is to be implemented in pack-owned instructions,
not silently patched into the vendored Archify skill.

## Known visual limitations at handoff

The owner identified tangled routes near refinement/human review and icons
overlapping node labels. A direct initial-generation-to-refinement route removed
one detour. The rest is not fully resolved.

The pinned workflow renderer exposes routing and sizing controls but no supported
icon visibility, icon padding, or label-position controls. Wider nodes and alternate
routes/layouts tried during this session caused other readability or containment
problems and were reverted. The artifact chart also has an icon overlap.

The charts pass nine automated showcase checks and desktop containment checks,
yet these visible defects remain. Earlier claims of a visual-review pass were too
generous. Automated acceptance must not be described as proof of perceptual clarity.
No renderer patch or hand-edited generated HTML was introduced. An upstream fix,
an explicit maintained patch, or a less compact layout remains a separate decision.

## Open choices for the implementation session

- The concrete formula composition for initial generation and reusable refinement.
- Initiative document locations, stable identity rules, and revision/approval records.
- Human approval-queue interaction and duplicate-safe release of selected builds.
- The threshold between lightweight mail and tracked review during exploration.
- Whether fresh review sessions earn their cost; no third persona is required now.
- Binding-specific routing and Hindsight dependency/read configuration.
- Whether build dispatch waits for ingestion completion or only for approval.
- Native build continuation, final report author, and failure-path reporting.
- Presentation of comparisons for non-architecture diagrams and treatment of the
  remaining renderer defects.

Before implementing, inspect the current native contracts, read all three IRs,
and flag any material conflict with this summary. Preserve the agreed boundaries
without treating unspecified mechanics as already decided. Do not expand scope
to reproduce the old OpenCode workflow or add infrastructure that fails the cost
test. No code change, memory shipment, commit, or push is authorized by this
summary alone.
