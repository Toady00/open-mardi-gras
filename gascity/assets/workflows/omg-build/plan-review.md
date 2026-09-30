Load the `omg-build` skill. Independently compare every original approved spec under
`{{approved_root}}` with `{{artifact_root}}/plan.md` and plan.json. Review requirement
inventory completeness, implementation approach, dependencies and verification.
Check the plan's comparison with the existing initiative build report and actual
repository: retained work must still satisfy the approved snapshot, changed or
unassessed obligations need work, and current verification must cover reused code.
Check reuse decisions against current Hindsight conventions, not a historical
conventions list copied from the report; note missing memory context explicitly.
Write plan-review.json with current hashes and a truthful verdict. Do not edit the
plan. Completed review work may close with gc.outcome=pass even when its verdict
is fail; the native group check sends those findings back to the plan author.
Use `omg-development`. Check that categories match both approved prose and its
delivery blocks, that no development obligation was deferred to escape a check,
and that required test/pipeline artifacts are planned without demanding their
later staging/production execution. Apply the same standard to Terraform and app code.
