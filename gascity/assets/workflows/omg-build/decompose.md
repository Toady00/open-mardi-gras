Load the `omg-build` skill. Read the passing plan and review in `{{artifact_root}}`.
Create or adopt this operation's runnable work beads and implementation convoy.
Record every bead immediately in decomposition.json before adding the next. Link
dependencies in Beads; each description must name its approved requirement IDs,
scope, expected changes and meaningful verification. Stamp omg.operation with
`{{operation}}` and omg.artifact_root with `{{artifact_root}}` on every work bead.
Set gc.input_convoy_id and omg.implementation_convoy on the actual build workflow
root to this convoy, then verify --stage decompose. Retry by adopting the recorded
IDs and repairing membership or coverage, never replacing the convoy after drain
execution has begun. The launch source and graph-control beads are not work items.
Assign only development obligations to builders. Preserve every downstream-check
in decomposition.json's separate downstream array with its approved owner/stage.
Do not create builder work to obtain downstream execution evidence. Required
verification artifacts and their pipeline wiring remain development deliverables.
