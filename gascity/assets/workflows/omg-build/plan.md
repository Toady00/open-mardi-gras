Load the `omg-build` skill. For initiative `{{initiative}}`, operation `{{operation}}`,
read `{{artifact_root}}/baseline.json` and the original approved specs under
`{{approved_root}}` at revision `{{approved_revision}}`. Write plan.md and plan.json
under `{{artifact_root}}` using the execution-record contract. Inspect the target
repository before choosing implementation order and verification. On retries,
address plan-review.json findings and checker diagnostics without altering scope.
Use `omg-development` to preserve the exact approved classification of every ID.
Plan implementation and local checks for development obligations, including any
required downstream verification artifacts. Retain downstream execution separately
with its owner/stage. Never assign live acceptance as a builder completion gate.
