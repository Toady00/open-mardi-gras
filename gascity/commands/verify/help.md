# Verify OMG build evidence

`gc omg verify --stage contract|plan|decompose|work|quality|reconcile|finalize|report --root <artifact-root>`

Work verification also takes `--work <bead-id>`. Formula checks call the same
implementation directly through Gas City's asset resolution; without arguments
it reads the stage and run from `GC_BEAD_ID`. `--json`, `--city`, and `--rig` are
accepted. Exit zero means the mechanical contract passed. Nonzero reports the
failed check. This command never runs application tests or installs dependencies.

Requires Bash, jq, Mike Farah yq v4, Git and shasum. See the `omg-build` skill for
the execution-evidence contract. Hindsight remains the published-document authority.

`contract` validates the exact approved spec classifications without requiring a
plan. Plans must match the `omg-delivery` blocks in those specs. Decomposition
assigns development obligations and retains downstream checks separately. Local
test evidence covers development-check IDs; required verification artifacts must
exist in the reviewed commit. Reconciliation permits pending-downstream results
only for IDs already approved as downstream-check, with their owner/stage intact.
Finalization checks the finalizer's publication.json attestation against the
authorized local, direct-push, or PR-open handoff and rejects deployment or
PR-approval claims. It is offline and never contacts a remote: it verifies that
the receipt is consistent, not that the push or PR happened, and it cannot show
that nothing was pushed. It does not run CI/CD.

`report` runs after the build root settles, for failed, canceled and skipped
builds too, and needs no plan, work, quality or finalization record (a passed
build must still have its publication receipt). It checks report.json against
the settled operation and terminal root, whose exact `gc.outcome` the receipt
repeats (`unknown` when the root has none): the initiative directory is
`docs/initiatives/<slug>`, the report commit contains only
`<directory>/reports/<operation>.md`, matches the recorded hash and the working
copy, carries schema 2 agent-authored `build-report` frontmatter with a unique
ID, and cites the assessed revision and operation. Publication is required only
for a passed root in the same checkout whose build requested `push`/`open_pr`;
its finalized publication.json must then record the matching handoff for the
assessed revision with a well-formed `<remote>/<branch>` `remote_ref` (checked
with `git check-ref-format`), and anything else is an error rather than a local
result. Then the report receipt must be `pushed` there
with the evidence `gc omg report publish` recorded, and the check requires that
evidence to name this commit, blob, revision and destination, its `base` to be a
local commit containing the assessed revision, and every commit in
`base..commit` to be report-only. This stage never contacts a remote: it runs in
the controller sandbox without the worker's Git credentials, so remote reads and
the push belong to `report publish`. Otherwise the receipt must be `local`.
`--plan` (report stage only, used by `report publish`) performs the local checks
and prints the resolved destination instead of enforcing the disposition.
