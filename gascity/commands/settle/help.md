# Settle verified OMG source tasks

```sh
gc omg settle --root /absolute/path/to/artifacts --city /absolute/path/to/city --rig rig-name
gc omg settle --root /absolute/path/to/artifacts --city /absolute/path/to/city --rig rig-name --apply
```

The default is a read-only JSON plan. Both modes run the full quality verifier
and validate native execution evidence. Preview therefore requires passing
quality, including committed code and current passing tests and review.

The city must be an absolute path canonically matching `baseline.city`. The rig
is a registered rig name, or an absolute path that resolves to exactly one
registered rig, through a city-scoped `gc rig list --json`; either way the
registered rig's path must canonically match `baseline.repo`. Settlement checks
this binding before quality verification or bead access, then pins commands to
the canonical city path and the registered rig name (`gc --rig` resolves names
only, so a path is never forwarded). Relative paths and cwd inference are not
supported.

Apply requires `gc bd update --help` to advertise `--if-revision` and every source
to expose a signed 64-bit integer revision. Revisions are opaque equality tokens;
negative values and explicit zero are preserved exactly. Missing capability returns `status: unsupported`
and exit 2 without mutation. There is no unconditional-close fallback.

Sources must be plain `task` issues, belong to this artifact root and operation, be unassigned, and have
no exclusive drain reservation. Open tasks close in sorted manifest-index order.
Those indices must be topological for actual intra-batch `blocks` dependencies;
an invalid order is rejected before mutation. Closed tasks are accepted only
when their settlement workflow, drain, and item-root metadata match exactly.
Dependency edges must belong to the source. Only `blocks` edges are supported;
`waits-for`, `conditional-blocks`, and other edge types return unsupported.
External blockers must be `closed` when read during preflight. Before each
closure, all blockers are read again and must be closed, including earlier batch
members. Unresolved blockers stop settlement.

Apply revalidates quality and execution, then rereads each source and uses its
validated revision in one conditional update containing closure, settlement
metadata, and an evidence note. Conflicts stop the batch without retry. An atomic
`settlement.json` records the operation, workflow, drain, exact reviewed revision,
and per-item results. A partial failure records `failed`, never `settled`. Rerun
the same command to validate again and resume past matching completed closures.
Preview does not write a receipt. Exit 0 means a valid plan or completed apply;
exit 1 means validation or application failed. Output is always JSON.

The command declares JSON support for `GC_JSON_CONTRACT_STRICT=1`.
`gc omg settle --json-schema` exposes its result and failure contracts. The
failure schema covers settlement errors, partial receipts, and Gas City dispatch
errors; its settlement branch references the sibling `result.schema.json`.

The revision fence protects one source update, not the dependency graph. A blocker
can change after its last read; this command does not provide graph-wide atomicity.
If an unsupported gate appears during apply, the partial receipt is `failed` with
`failure_kind: unsupported`, and the command exits 2.
