# OMG implementation decisions

This records the owner's clarification after the September 13 workflow handoff.

- Conversation is the human interface. Pack commands support the agents; humans
  do not need to operate an approval CLI.
- A rig agent keeps initiative documents in its rig's
  `docs/initiatives/<id>`. A city agent uses the city's same relative directory,
  typically for cross-rig initiatives.
- Direction approval binds the inspected visual revision. Spec approval binds
  the reviewed document set. Neither launches implementation.
- The human explicitly requests the build workflow. An agent may suggest it
  after approval, but may not interpret approval as a launch request.
- Hindsight ingestion is independent of approval and build initiation.
- The city imports Hindsight directly as a sibling of OMG. OMG does not import
  it transitively. The archivist belongs to `hindsight.archivist`; OMG's shared
  prompt guidance uses the city-provided `gc hindsight read` commands.
- The September 14 follow-up replaces the official methodology pack with OMG-owned
  formulas and workers. Gas City still owns dispatch, convoy draining, checks,
  retries, scope failure and post-settlement reporting.
- Planning reads the pinned approved specs directly. There is no translated
  requirements document or dependency on official build-artifact schemas.
- `gc omg verify` uses Bash, yq and jq for execution-record checks. Build launch
  installs no Python environment, packages or compatibility entrypoints. The
  initiative ledger command continues to use Python's standard library.
- Implementation uses a shared single-lane convoy drain in the target rig checkout.
  Integrated verification and independent review run after implementation, with
  up to three repair/test/review attempts. Exhaustion fails the build and still
  schedules its Hindsight report. A successful reconciliation accounts for every
  approved requirement; scope changes return to approval in conversation.

These instructions supersede the original automatic approval-to-build proposal
and the subsequent official-pack inheritance and managed-validator decisions.
The Archify proposal and discussion summary remain historical records.

## First-trial corrections

- Friendly conversation identities must coexist with worker pools. Agent-wide
  fixed runtime aliases caused collisions; default session naming and explicit
  conversation aliases are used until the chat/worker session design is revisited.
- Startup nudges claim routed work. A formula worker executes its assignment
  rather than starting another discovery conversation.
- Human decisions interrupt document execution through native scope failure.
  The command limits the enclosing check to the current attempt before closing
  the worker: the installed engine still retries failed scopes even when their
  failure class is hard. Gas City owns graph skipping and settlement.
- Decision IDs, recorded resolutions, captured return addresses and retryable
  mail/nudge receipts make the handoff explicit. A human answer does not revive
  interrupted work, and a stale handoff cannot overwrite a newer resolution.
- Operation results distinguish readiness, human interruption, incomplete work
  and execution failure from the engine's pass/fail. A resumed refinement fills
  missing initial documents before whole-set reviews.
- Historical document provenance does not establish current acceptance. External
  activation prerequisites are explicitly scoped rather than silently pulled into
  the collector implementation. Diagnostic files stay outside the docs inventory.

City-centralized documents, named chat sessions, phase shortcut commands, and an
HTML document reader with annotation-to-revision handoff remain future design
topics. These corrections do not select or implement those designs.

## Development versus downstream execution

The first build exposed a contradiction: the specs allowed local builder
acceptance while operator checks remained pending, but the verifier required
every ID to be implemented. The correction spans docs, refinement and build.

The common omg-development skill defines one application/IaC boundary. Owning
specs classify each requirement in a reviewed omg-delivery block; snapshots and
build checks share one parser. Decomposition assigns only development obligations,
while reconciliation preserves pending downstream IDs and ownership. Required
smoke tests or pipeline jobs are development artifacts; executing them after
promotion is not development acceptance. CI/CD remains the deployment mechanism.

Publication follows the chosen repository policy: local handoff, direct-branch
push, or PR submission. The workflow never assumes that a PR is required or that
submission establishes approval. A checked finalization records the authorized
handoff without deployment claims. A settled failed build has an explicit,
deduplicated retry path with separate artifacts; revised specs require new approval.
