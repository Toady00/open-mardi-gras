Load `omg-initiative`. Compare the implementation and review evidence to the
actual approved specs at `{{approved_root}}`, revision `{{approved_revision}}`,
for initiative `{{initiative}}`, operation `{{operation}}`.

Write `{{artifact_root}}/spec-reconciliation.md`, outside ingestion. Identify the
assessed code SHA. Account for EVERY stable requirement: implemented, partial,
deferred, or blocked, with code and verification evidence. Explain deviations,
reasons and decision authority. A report cannot retroactively authorize deviation.
Distinguish implementation from review and actual publication/integration; this
step occurs before final publication and cannot imply post-merge verification.

Apply the cost/stop rule. Only justified required violations block finalization;
optional improvements do not. Preserve agreed deferrals and their observable
revisit triggers. A new scope decision goes to the human. Record reconciliation
path and hash on the root as `omg.reconciliation_path` and
`omg.reconciliation_sha256`. Set `gc.outcome=pass` or `fail` honestly. Failure
still reaches the post-settlement report assignment.
