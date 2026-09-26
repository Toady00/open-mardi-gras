Load the `omg-build` skill. Read `{{artifact_root}}/review.json`, tests.json and
checker diagnostics if present. On the first attempt, inspect the implementation
handoff; when no findings exist, record that no repair was needed. On later
attempts fix required findings and failing tests in the baseline repository.
Commit repairs and document evidence on finding beads. Keep findings open for
the independent reviewer to verify and close. Do not rewrite review verdicts or
reuse old test receipts as proof of repaired code.
