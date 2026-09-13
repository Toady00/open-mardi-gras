This is post-settlement work for initiative `{{initiative}}`, operation
`{{operation}}`. Read the actual workflow root, outcomes, errors and initiative
state. If refinement exhausted its three automatic attempts or authoring failed,
record `initiative decision --note ...` with the unresolved required findings or
execution error. Never report approval-ready merely because a bead closed.

Record settlement with:

    gc {{omg_binding}} initiative settle {{initiative}} --operation {{operation}} --workflow <actual-root-id>

Return a concise durable result pointer through `gc mail send` to the originating
conversation if its address is recorded; otherwise leave it discoverable through
the initiative record. A managed requester can wait on this handoff bead with
`gc session wait --on-beads ... --sleep`. Waiting for the root alone does not prove
post-settlement handoff finished. Finish the assignment; the human may return later
from any session. Do not start a build. Record the handoff artifact and completion.
