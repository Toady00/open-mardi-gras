# Hindsight Tagging Guidance

This repo ships durable project memory to the `omg` Hindsight bank. The bank is
memory for the Open Mardi Gras workflow and its supporting architecture: OMG
agents and skills, Beads work tracking, Hindsight integration, document
frontmatter, and the repo-specific operating conventions that make those pieces
work together.

This file is tagging intent for authors. It is not the bank's authoritative
vocabulary, and it must not be treated as a committed copy of the bank template.
The running bank remains the source of truth for legal strategy and tag values.
Use this guidance to choose the `hindsight.tags` and `hindsight.strategy` values
for documents authored in this repo.

## Policy

A document that should be retained in Hindsight carries a `hindsight` block in
frontmatter. For authored documents in this repo, include these tags unless the
document has a clear reason not to:

- `source:<value>` for provenance and trust.
- `domain:<value>` for the bounded context, mechanically matching the document's
  top-level `domain` field and the second segment of its `id`.
- `discipline:<value>` for the functional discipline or kind of work.
- `memory_type:<value>` for the document shape.

The tags are judgment guidance, not a schema. If the live bank's vocabulary
changes, prefer the live bank and refresh this file.

## `source:` — Provenance And Trust

`source:` records where the memory came from and how the reflect layer should
treat its authority. This is the most trust-sensitive dimension: it separates
authored design records from source-document ingestion, voice memo opinion, and
conversation traces.

Use `source:authored` for durable documents intentionally authored in this repo:
ADRs, specs, product docs, design docs, and repo operating guidance. This is the
normal value for new documents created through the OMG workflow.

Use `source:document-ingest` for source-of-record documents preserved from
elsewhere without turning them into a repo-authored decision. These are facts
about an external or upstream source, not necessarily decisions made here.

Use `source:voice-memo` for transcribed voice memos. Treat these as owner input
or opinion unless another authored document later turns the point into a durable
decision.

Use `source:harness-conversation` for retained session or conversation records.
These can explain context and discovery, but should not outweigh authored ADRs or
specs when there is a conflict.

Historical note: older guidance used `source:canon`. Do not use it for new
documents; use `source:authored` instead.

## `domain:` — Bounded Context

`domain:` identifies the product, platform, or workflow area the document is
about. It is the Domain-Driven Design sense of domain: a bounded context such as
`platform`, `notifications`, `subscriptions`, `web`, or another project area.

For documents in this repo, the `domain:` tag value is mechanical:

- It equals the top-level `domain` frontmatter field.
- It equals the second segment of the dotted document `id`.

For example, `adr.platform.tag-taxonomy.0001` has top-level
`domain: platform`, so its Hindsight tag is `domain:platform`.

Do not use `domain:` for the functional discipline. That meaning lives under
`discipline:`.

## `discipline:` — Functional Discipline

`discipline:` records what kind of work the document primarily serves or which
discipline owns the decision. Choose this by judgment.

Use `discipline:engineering` for implementation architecture, code behavior,
agent/skill design, workflow mechanics, Beads integration, Kubernetes or runtime
operations, and technical ADRs. Most current docs in this repo use this value.

Use `discipline:product` for PRDs, user stories, product behavior, acceptance
criteria, and prioritization tradeoffs.

Use `discipline:business` or `discipline:strategy` for mission, vision,
positioning, business-plan, or high-level direction documents.

Use more specific values such as `discipline:legal`, `discipline:operations`,
`discipline:marketing`, or `discipline:infrastructure` when the document is
clearly owned by that discipline. These examples are illustrative, not a complete
enum.

## `memory_type:` — Document Shape

`memory_type:` tells the bank what kind of memory shape it is retaining. It often
tracks the top-level document `type`, but it is still a bank tag and should be
chosen for recall quality rather than blindly copied.

Use `memory_type:adr` for architecture decision records: one decision, the
context and options considered, the choice, and consequences.

Use `memory_type:spec` for technical specifications: intended behavior,
interfaces, workflows, implementation shape, and verification criteria.

Use `memory_type:prd` for product requirements documents: product problem,
goals, users, requirements, non-goals, and success criteria.

Use `memory_type:roadmap` for sequencing and planning documents.

Use `memory_type:user-story` for individual user stories or acceptance slices.

Use `memory_type:handoff` for handoff records: obligations that must happen but
are not this repository's to discharge, and who owns each.

Use `memory_type:strategy` for mission, vision, principles, business strategy,
or other durable direction-setting documents.

The examples above reflect the current project conventions. They are not an
authoritative list of values accepted by the bank.

## `strategy`

The live `omg` bank currently exposes `spec-or-adr` as its retain strategy for
authored ADRs and specs. Use it for new ADRs, specs, and related design records
unless the bank gains a more specific strategy.

`spec-or-adr` uses verbose extraction and is intended to preserve durable
decisions, requirements, constraints, rationale, tradeoffs, rejected alternatives,
open questions, dependencies, and implementation implications. It is a good fit
for this repo's design and workflow documents because future agents need the
reasoning, not just the conclusion.

Some existing documents in this repo still show `strategy: design-record`. Treat
that as historical drift from older guidance unless the live bank is updated to
expose that strategy. For new documents, prefer the live bank strategy.

If a document is retained without a named strategy, Hindsight uses the bank's
default extraction behavior. Prefer naming a strategy when one fits so the intent
is visible in the document.

## Examples

### Authored ADR About Workflow Architecture

For `adr.platform.multi-repo-canon.0001`:

```yaml
hindsight:
  strategy: spec-or-adr
  tags:
    - source:authored
    - domain:platform
    - discipline:engineering
    - memory_type:adr
```

### Authored Technical Spec For A Platform Workflow

For `spec.platform.some-workflow.0001`:

```yaml
hindsight:
  strategy: spec-or-adr
  tags:
    - source:authored
    - domain:platform
    - discipline:engineering
    - memory_type:spec
```

### Product Requirements Document

For `prd.notifications.delivery-controls.0001`:

```yaml
hindsight:
  strategy: spec-or-adr
  tags:
    - source:authored
    - domain:notifications
    - discipline:product
    - memory_type:prd
```

### Strategy Or Vision Document

For `strategy.platform.workflow-principles.0001`:

```yaml
hindsight:
  strategy: spec-or-adr
  tags:
    - source:authored
    - domain:platform
    - discipline:strategy
    - memory_type:strategy
```

### Ingested Source Document

For an external source-of-record document retained mostly as-is:

```yaml
hindsight:
  tags:
    - source:document-ingest
    - domain:platform
    - discipline:business
    - memory_type:strategy
```

Use a specific retain strategy only if the live bank exposes one that fits
source-document ingestion.
