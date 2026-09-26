# Publish an OMG build report

`gc omg report publish --root <artifact-root> [--preflight]`

Runs in the architect's own session with the worker's normal Git identity. It
first performs the same local artifact validation as `gc omg verify --stage
report` (the report commit, hash, frontmatter, cited revision and settled root),
then decides the publication disposition from the build's own finalized
`publication.json`: a passed root whose code was `pushed` (for `push`) or
`pr-open` (for `open_pr`) from this same checkout authorizes publishing the
report to exactly that receipt's `<remote>/<branch>`. A malformed or missing
`remote_ref` on such a receipt is an error, never a fall-back to local. Every
other case prints `{"status":"local","normalized":<bool>}` and touches no
remote; a stale `pushed`/`failed` disposition left by an earlier run (for
example after the root was canceled) is normalized atomically to `local`, with
`reason`, `error` and `publication` removed and every artifact field kept, while
an already clean local receipt is left byte-for-byte alone.

When authorized it first resolves one effective endpoint: the remote's fetch
URL, which must equal its single push URL (a different push URL or several push
URLs are rejected as `remote_config` before any read or write, rather than
widening the authority). It then reads that endpoint's branch tip (`git
ls-remote`, fetching it without tags or submodules if needed), requires the tip
to contain the finalized assessed revision, requires the report commit to
descend from it with only report-only commits in between (retries included,
never unrelated local code), then pushes the exact validated SHA as
`<sha>:refs/heads/<branch>` to that endpoint, guarded by `--force-with-lease`
on the inspected tip and with tag following and submodule recursion disabled so
no configuration can add a second write; it re-reads the endpoint and requires
it to read that SHA. The evidence is then written into `report.json`
(`status: pushed`, `remote_ref`, `publication.{remote,branch,url,base,pushed,
observed,revision,report_blob,at}`); the offline controller check inspects that
evidence and the local objects it names. URLs are recorded with any embedded
credentials removed. Success is printed only after that write is durable; if
the push succeeded but the receipt could not be written, the command prints
`status: receipt_failed` with the observed tip and exits 2, and a rerun records
the already published report.

`--preflight` performs the remote read and every check but prints the validated
destination, base tip and outgoing commits instead of pushing, and never writes
`report.json`: an unauthorized run reports `normalize` instead of doing it, and
a blocker or remote failure prints the same `failed` JSON with `preflight: true`
and exits 1 while leaving the existing receipt, including an earlier successful
publication, byte-for-byte intact.

Any blocker or remote failure records `status: failed` with a machine-readable
`reason` (`remote_config`, `remote`, `missing_branch`, `revision_not_published`,
`diverged`, `outgoing`, `push`, `unverified`) and the retained Git stderr in
`error`, prints the same as JSON and exits 1; if even that record cannot be
written the JSON carries `receipt_error` too. The local report commit is
preserved; the controller check then fails with that exact blocker until
publication is rerun. `--json`, `--city` and `--rig` are accepted. Requires
Bash, jq and Git.
