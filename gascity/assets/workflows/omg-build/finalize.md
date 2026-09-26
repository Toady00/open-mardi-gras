Load the `omg-build` skill. Run `gc {{omg_binding}} verify --stage reconcile --root
{{artifact_root}}` before finalizing. Preserve the verified code revision. Write
publication.json under `{{artifact_root}}` with the actual revision and publication
outcome. Push code only if `{{push}}` is true; create a PR only if `{{open_pr}}` is
true, using the repository's agreed target. A PR request authorizes the branch
push needed to open it. Capture remote/ref/PR receipts and failures. Neither flag
authorizes merging. When neither is true, record local completion explicitly.
Use the publication.json fields in the `omg-build` skill and run
`gc {{omg_binding}} verify --stage finalize --root {{artifact_root}}` after recording
the receipt; that check is offline and validates your attestation, so record
only what actually happened. A direct-branch push is valid under the agreed repository policy;
a PR is optional. Neither an opened PR nor a successful push proves PR approval,
deployment or downstream acceptance. Later CI/CD findings create new tasks.
Mark gc.outcome=fail if requested publication failed, otherwise pass, then close
the assigned step. The engine settles the build and runs the Hindsight report.
