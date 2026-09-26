Load `omg-initiative`. This is post-settlement reporting for initiative
`{{initiative}}`, operation `{{operation}}`, including failed, partial and blocked
builds. Read the ACTUAL workflow root outcome, all available artifacts, assessed
code and publication evidence. Do not assume that normal reconciliation,
finalization or publication ran. Reconstruct requirement reconciliation from
`{{approved_root}}`, revision `{{approved_revision}}`, when the normal path failed.

Load `hindsight-shipping` for the authoritative format and publication contract.
Write a Hindsight-compatible `build-report` Markdown document under the initiative's
original repository at `docs/initiatives/<id>/reports/<operation>.md`. Use a stable
ID for this run, prefixed by its initiative identity. Include approved direction
and spec commit/digest, target rig, native workflow ID, assessed code SHA, every
requirement's implemented/partial/deferred/blocked outcome, evidence, deviations,
reasons, decision authority, unresolved risks and unfinished work. Explicitly
distinguish implemented, reviewed, and actually published/integrated code. Do not
infer post-merge verification. Follow Hindsight's rules for agent-authored records;
do not claim human review that has not occurred.

Separate native execution from source-task bookkeeping. Read the exact drain
manifest, item workflow/finalizer outcomes and receipts; open source tasks alone
do not mean code quality failed. Include settlement command output and any
settlement.json, listing pending source IDs and reasons. Unsupported revision CAS
is pending bookkeeping. Report other conflicts and partial closures precisely,
without claiming settlement or overall completion. Failed runs retain their source
tasks and findings; do not close them as successful while writing this report.

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
Use the `omg-development` contract to report verified development separately from
actual publication/integration and downstream execution. Include every pending
downstream ID, owner, stage and required evidence without treating it as unfinished
builder work. Identify delivered smoke tests and pipeline wiring separately from
their unexecuted downstream checks. Never infer PR approval, deployment or live
acceptance. Describe a local-only code handoff as local, not pushed or integrated;
CI/CD is not run by OMG. The current no-push report path can leave this reporting
bead blocked by its publication requirements. Preserve the local report and exact
publication blocker without claiming that reporting or Hindsight shipping finished.
