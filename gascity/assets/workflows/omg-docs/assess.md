Load `omg-initiative`; read initiative `{{initiative}}` and the whole document set,
approved IR directly, earlier review artifacts and the human's change request if
one exists. Initial refinement needs no supplied change request.

This is the product assessment/writing assignment inside shared refinement.
Assess whole-set alignment, completeness, and impact. Apply the cost/stop rule.
Revise affected product content only; do not rewrite unaffected documents merely
to demonstrate activity. Keep one writer per artifact. Record remaining technical
corrections for the successive architect assignment.

If the record is `needs-human`, preserve it and end without further revision.
Otherwise invalidate earlier readiness before editing with
`gc {{omg_binding}} initiative revise {{initiative}}`. A candidate IR or unresolved
scope decision uses `initiative decision --note ...`; explain the needed decision
and keep pending proposals separate. An agent cannot approve its own scope change.
Set `gc.outcome=pass` before closing; execution errors use `fail` and diagnostics.
