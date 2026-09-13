Finalize this continuation using the installed `gc.build.final-report.v1` schema,
the native build artifacts, and the required OMG reconciliation at
`{{artifact_root}}/spec-reconciliation.md`. Follow the official build finalization
contract: validate requirements, implementation plan, plan-review, decomposition,
implementation evidence and review verdict; record paths/hashes on the root;
write the native final report under `{{artifact_root}}`; record
`gc.build.final_report_path`. The existing build-artifact check validates it.

Do not pass if review is `blocked` or `changes_required`, any implementation drain
failed, required implementation evidence is absent, or `gc.build.repair_status`
is anything other than `not_needed` or `approved`. Record `status: blocked`,
`gc.outcome=fail`, `gc.build.status=blocked`, a machine-readable
`gc.failure_class`, and restart entrypoint/reason/artifact paths in those cases.
Record the continuation entrypoint and which upstream stages were reused rather
than executed. Preserve native publish intent and recovery metadata.

Include the reconciliation's approved spec revision, assessed code SHA,
requirement outcomes, deviations, reasons and authority in that report. A missing
or failing reconciliation cannot finalize as a pass. Respect `{{push}}` and
`{{open_pr}}`; actual publication belongs to the next native step. Never claim
publication or post-merge verification before it occurs. Set `gc.outcome=pass`
only on successful finalization; otherwise record failure and diagnostics.
