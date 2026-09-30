Load the `omg-build` skill. Resolve the single member of convoy `{{convoy_id}}` with
`gc convoy status {{convoy_id}} --json`, then read its description and metadata.
Use its omg.artifact_root to read the baseline, plan and decomposition. Implement
only that member in the baseline repository, commit the changes, run its focused
checks, and save work/<member-id>.json and full test logs. If an earlier attempt
already changed code, inspect and repair it rather than duplicating the work.
For verification/reuse of already-compliant code, run the assigned checks and
record the work receipt at current HEAD without manufacturing a code change or commit.
Run the verify command with --stage work and --work <member-id>. Mark the assigned
work step outcome before closing. Gas City settles the item workflow but leaves
the source member open; retain it for reconciliation's source-task bookkeeping. Unresolved
scope or unavailable verification fails the item and is reported by the parent.
