Load the `omg-build` skill. Independently review the code at the current baseline
repository HEAD against the original specs, work receipts and tests.json in
`{{artifact_root}}`. Check correctness, regressions, failure handling and evidence
quality. Write review.json for that commit and the current tests.json hash. File
each required finding as a bead stamped omg.operation=`{{operation}}` and
omg.required=true; retain its
ID across attempts. Verify repairs and close resolved finding beads. Keep unresolved
required findings in the report and set verdict=fail. Complete the review work
with gc.outcome=pass so the native group check can trigger repair. Do not modify
production code or waive a requirement to obtain a passing verdict.
Leave the full verify --stage quality gate to the controller after this step;
complete the review even when its verdict fails and preserve prior findings.
Review required downstream test artifacts and pipeline integration as code.
Their later execution is not a missing development check. Use `omg-development`
to distinguish incomplete implementation from intentionally pending downstream
evidence; reject any unauthorized reclassification or deployment claim.
