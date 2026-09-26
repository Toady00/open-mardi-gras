Load `omg-initiative`; read initiative `{{initiative}}` and the whole document set,
approved IR directly, earlier review artifacts and the human's change request if
one exists. Initial refinement needs no supplied change request.

This is the product assessment/writing assignment inside shared refinement.
Assess whole-set alignment, completeness, and impact. Apply the cost/stop rule.
Revise affected product content only; do not rewrite unaffected documents merely
to demonstrate activity. Keep one writer per artifact. Record remaining technical
corrections for the successive architect assignment.
Use `omg-development` to reconcile the requirement and AC boundary across all
documents, not just relabel execution records. Preserve product behavior while
making development obligations, downstream artifacts and later execution explicit.

Apply the skill's document-step protocol. Otherwise invalidate earlier readiness before editing with
`gc {{omg_binding}} initiative revise {{initiative}} --operation {{operation}}`. A candidate IR or unresolved
scope decision uses `initiative decision --operation {{operation}} --note ...`; explain the needed decision
and keep pending proposals separate. An agent cannot approve its own scope change.
Complete through the document-step protocol, including on a human interruption.
