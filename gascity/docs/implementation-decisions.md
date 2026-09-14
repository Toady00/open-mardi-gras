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

These instructions supersede the automatic approval-to-build release described
in the original proposal. The original discussion summary remains a historical
record of that proposal.
