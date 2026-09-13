Load `omg-initiative`. This is post-settlement reporting for initiative
`{{initiative}}`, operation `{{operation}}`, including failed, partial and blocked
builds. Read the ACTUAL workflow root outcome, all available artifacts, assessed
code and publication evidence. Do not assume that normal reconciliation,
finalization or publication ran. Reconstruct requirement reconciliation from
`{{approved_root}}`, revision `{{approved_revision}}`, when the normal path failed.

Write a Hindsight schema-2 `build-report` Markdown document under the initiative's
original repository at `docs/initiatives/<id>/reports/<operation>.md`. Use a stable
ID for this run, prefixed by its initiative identity. Include approved direction
and spec commit/digest, target rig, native workflow ID, assessed code SHA, every
requirement's implemented/partial/deferred/blocked outcome, evidence, deviations,
reasons, decision authority, unresolved risks and unfinished work. Explicitly
distinguish implemented, reviewed, and actually published/integrated code. Do not
infer post-merge verification. Source remains agent and initial status is draft.

Validate with the Hindsight pack schema and publish the report through the
initiative repository's agreed canonical Git publication path, independently of
whether code publication succeeded. The existing Hindsight pipeline ships it.
Do not send IR/HTML/comparison artifacts or raw bead chatter to the bank.

Record report path, content hash, assessed code revision, publication commit/ref
or publication failure, and any PR URL on this work bead and workflow root. Record
`gc {{omg_binding}} initiative settle {{initiative}} --operation {{operation}}
--workflow <actual-root-id>` once the workflow is terminal. Report publication
failure must remain recoverable on this reporting bead with its local artifact
and error; do not close as a successful publication. A failed build root does not
excuse omitting this report.
