Load `omg-initiative`. Read `gc {{omg_binding}} initiative show {{initiative}}`.
This is operation `{{operation}}`, initial generation `{{initial}}`.

Resolve the initiative's absolute repository and document directory from the
record. Work there, not in a disposable per-step worktree. Materialize the
approved direction with `gc {{omg_binding}} initiative materialize {{initiative}}`.
Read every approved JSON IR directly from that frozen directory and read the
current discussion summary. Identify the original and current approved baselines.
Flag conflicting summary claims; they do not override IR. Missing material
decisions return to the human.

Validate Hindsight frontmatter with its installed `schemas/docs/derive` when
publishing. Keep all visual evidence and review receipts out of ingestion.
Check that no other document workflow is writing this initiative. Generation
must not replace existing authored documents. If a prior generation partially
completed, recover its own work rather than regenerate the initiative.

Apply the skill's document-step protocol. An unresolved decision uses
`initiative decision {{initiative}} --operation {{operation}} --note ...`, then
`initiative complete-step {{initiative}} --operation {{operation}} --step <claimed-id>`.
That closes this work as interrupted so Gas City skips the remaining scope and
runs the handoff. Never mark a human-blocked assignment as successful authoring.
