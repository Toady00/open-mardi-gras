Load `omg-initiative`. This is post-settlement work for initiative `{{initiative}}`,
operation `{{operation}}`. Read the actual workflow root, errors and initiative.
Write a concise handoff under `.omg/` with produced files, review verdicts, engine
outcome and the next action. A native pass is not document readiness. Human
interruptions use native failure to stop work but are reported as `needs-human`.

Run:

    gc {{omg_binding}} initiative settle {{initiative}} --operation {{operation}} --workflow <actual-root-id>

This records the operation's semantic result and sends mail plus a queued nudge
to its originating conversation. Check the `notifications` receipt for
`settled-{{operation}}`. If delivery is pending, use `initiative notify {{initiative}}`
after addressing the recorded error. Missing return addresses can be repaired
with `initiative watch {{initiative}} --notify <original-session-id>`. Do not
substitute a worker session or pretend a queued nudge has already been read.

Never overwrite a newer resolution or operation with this run's old question.
Only `resolve` closes a recorded human decision; preserve that audit history.
Record the handoff path on this work bead. Close the handoff with gc.outcome=pass
once its artifact and notification receipts are recorded. Failed delivery leaves
this assignment recoverable; it does not regrade the settled root. This cleanup
uses ordinary native update/close, not the document `complete-step` command.
