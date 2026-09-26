# Verify OMG build evidence

`gc omg verify --stage contract|plan|decompose|work|quality|reconcile|finalize --root <artifact-root>`

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
