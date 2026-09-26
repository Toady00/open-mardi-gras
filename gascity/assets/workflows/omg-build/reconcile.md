Load the `omg-build` skill. Reconcile the actual implementation at the baseline
repository HEAD with every approved requirement under `{{approved_root}}`, revision
`{{approved_revision}}`. Read the tests, review and work receipts in
`{{artifact_root}}`. Write reconciliation.json with one row per requirement,
implementation status and specific file/test evidence, plus any deviations and
their authority. Verify --stage reconcile. All development obligations must be
implemented; verification-artifact rows name their committed source paths.
Downstream-check rows remain pending-downstream with their approved owner/stage.
That does not block development completion and is not a claim of live verification.
Do not revise the approved classification or omit any IDs. The post-settlement
report preserves the development outcome and downstream handoff separately.

After reconciliation.json is written and verify --stage reconcile passes, follow
the omg-build skill's source-task bookkeeping procedure within this step. Preview
`gc {{omg_binding}} settle --root {{artifact_root}} --city <city-path> --rig <rig-name>`
using the actual build city and rig. Apply only through that command's advertised
revision-CAS capability check. Unsupported settlement leaves source tasks pending
with its reason; it does not invalidate verified code. Report other conflicts and
partial results explicitly without claiming completion. Reconcile/finalize gates
check execution evidence, not source closure. Keep settlement output for the report.
