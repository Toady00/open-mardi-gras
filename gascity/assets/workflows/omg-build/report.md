Load `omg-initiative` and `omg-build`. This is post-settlement reporting for
initiative `{{initiative}}`, operation `{{operation}}`, including failed, partial,
canceled and blocked builds. Read the ACTUAL workflow root outcome from
`gc.root_bead_id`, all available artifacts, assessed code and publication evidence.
Do not assume that normal reconciliation, finalization or publication ran.
Reconstruct requirement reconciliation from `{{approved_root}}`, revision
`{{approved_revision}}`, when the normal path failed.

Load `hindsight-shipping` for the authoritative format contract. Write a
Hindsight-compatible `build-report` Markdown document under the initiative's
original repository at `docs/initiatives/<slug>/reports/{{operation}}.md`, with a
stable ID `build-report.<slug>.{{operation}}`, `status: draft` and `source: agent`.
Include approved direction and spec commit/digest, target rig, native workflow ID,
the launch operation key, assessed code SHA, every requirement's
implemented/partial/deferred/blocked outcome, evidence, deviations, reasons,
decision authority, unresolved risks and unfinished work. Explicitly distinguish
implemented, reviewed, and actually published/integrated code. Do not infer
post-merge verification. Follow Hindsight's rules for agent-authored records; do
not claim human review that has not occurred.

Separate native execution from source-task bookkeeping. Read the exact drain
manifest, item workflow/finalizer outcomes and receipts; open source tasks alone
do not mean code quality failed. Include settlement command output and any
settlement.json, listing pending source IDs and reasons. Unsupported revision CAS
is pending bookkeeping. Report other conflicts and partial closures precisely,
without claiming settlement or overall completion. Failed runs retain their source
tasks and findings; do not close them as successful while writing this report.

Validate with the Hindsight pack schema, then commit the report in the initiative
repository with a path-only commit: `git add -- <report-path>` followed by
`git commit --only -- <report-path>`. That commits the report alone and leaves
every other tracked, untracked or already staged change in that checkout exactly
as it was; never run a plain `git commit`, `git add -A` or `git stash` there. A
dirty checkout does not block this step. That commit is the durable local artifact.
Do not send IR/HTML/comparison artifacts or raw bead chatter to the bank.

Record `gc {{omg_binding}} initiative settle {{initiative}} --operation {{operation}}
--workflow <actual-root-id>` once the workflow is terminal, before verification.
Write `report.json` under `{{artifact_root}}` using the fields in the `omg-build`
skill, with `status: local` and `remote_ref: null`: operation, workflow, the
root's exact terminal `gc.outcome` as build outcome (`unknown` when it is missing
or unrecognised, never a guessed pass), assessed revision (the publication
receipt's revision for a passed build, otherwise the rig HEAD you assessed),
report path, document ID, content hash and report commit.

Then run `gc {{omg_binding}} report publish --root {{artifact_root}}` from this
session. It validates the local artifact exactly as the controller check does
and decides publication from the build's own finalized publication.json. The
report has no publication authority of its own: only a passed root whose code
was actually `pushed` (for `push`) or `pr-open` (for `open_pr`) from this same
checkout authorizes it, and the destination is exactly that receipt's
`remote_ref` (an `open_pr` build's PR branch, never the default branch). A
distinct initiative repository, a failed, canceled or skipped root, a build
without `push`/`open_pr`, or a missing receipt prints `status: local` and touches
nothing: the report stays `local`, that passes the check and completes this
step, and the report is neither pushed, published nor shipped; publishing it
later is a separate human action. Never push, open a PR, or create a separate
branch or worktree for it yourself, and never push `HEAD`. If a previous run
left `status: failed` or `pushed` and publication is no longer authorized, the
command normalizes the receipt back to `local`. When publication is authorized,
the command resolves one endpoint (the remote's fetch URL, which must equal its
only push URL; anything else is rejected as ambiguous), reads that branch under
your Git identity, requires it to contain the finalized assessed revision,
allows only report-only commits between that tip and the report commit (retries
included; an unrelated unpublished code commit blocks it), pushes the exact
validated report SHA to that endpoint with a lease on the inspected tip and no
tag or submodule side effects, re-reads it, and records that evidence in
report.json before printing success. Exit 2 means the push succeeded but the
receipt could not be written: rerun the command. Then run `gc {{omg_binding}}
verify --stage report --root {{artifact_root}}`: it is offline and checks the
artifact plus that evidence.
The existing Hindsight pipeline ships canonical revisions.

Also record report path, hash, revision, commit, ref or publication failure, and
any PR URL on this work bead. Mark gc.outcome=pass and close the assigned step when
the check passes; report completion is separate from the build outcome and from
publication. If `report publish` reports a blocker or a remote failure, it has
already recorded `status: failed` with a machine-readable `reason` and the exact
Git error in report.json; keep the local commit, read that reason (an
authentication or network error is not a wrong commit; an `outgoing` blocker
means an unrelated unpublished commit sits below the report), and mark
gc.outcome=fail: the check keeps the blocker recoverable on this step without
claiming publication or Hindsight shipping. A failed build root does not excuse
omitting this report.
Use the `omg-development` contract to report verified development separately from
actual publication/integration and downstream execution. Include every pending
downstream ID, owner, stage and required evidence without treating it as unfinished
builder work. Identify delivered smoke tests and pipeline wiring separately from
their unexecuted downstream checks. Never infer PR approval, deployment or live
acceptance. Describe a local-only code handoff as local, not pushed or integrated;
CI/CD is not run by OMG.
