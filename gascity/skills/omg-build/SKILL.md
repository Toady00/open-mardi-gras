---
name: omg-build
description: Execute a Gas City OMG build step or work item. Use when assigned an omg-build or omg-work formula bead, including planning, decomposition, implementation, testing, review, reconciliation, finalization and the post-settlement report.
---

# OMG build execution

Load `omg-development` for the unified application/IaC completion contract.
This is development, not a deployment/promotion workflow. Required downstream
test artifacts are deliverables; their later execution results are not build gates.

Gas City owns scheduling, convoy drains, retries and workflow settlement. Work only the
assigned plain work bead. Read its metadata and workflow root with `gc bd show
<id> --json`; claim with `gc bd update <id> --claim` and close with
`gc bd close <id>`. Mark the work bead
`gc.outcome=pass` or `gc.outcome=fail` before closing it. A passing review step
means the review was completed; its recorded verdict can still fail the check.
The controller reruns the checked group, at most three attempts, then fails the
build scope and schedules its report. Read `gc.attempt_log` for failed checks.

## Inputs and execution records

1. Read `<artifact_root>/baseline.json`. Its operation identifies a recorded
   human build request in the initiative ledger. Read the exact documents under
   `approved_root`, with their original paths and bytes. The spec is authoritative;
   the plan describes execution. Do not create a replacement requirements document.
2. Work in the baseline's `repo`. This first workflow uses a shared, single-lane
   drain and that checkout for code handoff. Do not put changes in another worktree
   and assume later stages can see them. Commit each finished implementation or
   repair before recording its revision and running verification. Keep unrelated
   changes intact; a dirty checkout blocks verification until resolved.
3. Keep private execution records under `artifact_root`, outside Hindsight's docs
   tree. Write JSON records atomically through a temporary file and rename. On
   retry, reuse this operation's beads, convoy and files; inspect existing records
   before creating anything. Save each created bead ID immediately so interrupted
   decomposition can adopt it rather than duplicate work.
4. Run `gc <binding> verify --stage <stage> --root <artifact_root>` for an assigned
   checked stage. Work items use `--stage work --work <id>`. Repair, test and review
   workers inside the quality group write their own evidence and complete their
   assigned steps without invoking the full `quality` gate. The controller runs
   that gate after review, when the group's receipts are ready. This checks records and source
   revisions, not application correctness. Run the project's actual checks and
   retain their command, exit code and complete output. Never change a failed
   command into a passing receipt without rerunning it successfully.

Use `gc bd update <id> --set-metadata key=value` for individual metadata fields.
Find the owning workflow through `gc.root_bead_id`. Query the engine's command
help when the current CLI differs; do not invent an orchestration loop.

## Record contract

These are OMG execution records, not published-document schemas. Every path below
is relative to `artifact_root`. SHA fields are SHA-256 of the exact file bytes,
obtainable with `shasum -a 256 <file>`. Published reports use `hindsight-shipping`.

- `baseline.json` is written by the launch command. Do not edit it.
- `plan.md` describes implementation order, affected components, risks, dependencies
  and verification. `plan.json` has `requirements`, one row per stable requirement
  ID in the approved specs: `{ "id": "R1", "source": "docs/initiatives/example/spec.md",
  "kind": "implementation", "quote": "R1: Preserve the requested behavior." }`.
  Copy `kind` and owning `source` from the approved `omg-delivery` blocks. Downstream
  rows also copy `owner` and `stage`. Quotes are exact source text.
  Include all requirements, acceptance criteria and constraints with stable IDs.
  If approved specs lack usable IDs or contradict each other, record the blocker
  and fail the step; resolve scope in conversation rather than inventing approval.
- `plan-review.json`: `verdict` is `pass` or `fail`, `inventory_complete` is boolean,
  `plan_sha256` hashes plan.json, `prose_sha256` hashes plan.md, and `findings` explains
  omissions or design problems. The reviewer checks completeness against the full
  original specs. Hash/quote checks alone cannot establish completeness.
- `decomposition.json`: `workflow`, `convoy`, and `items`, each containing `id` and
  `requirements` as an array of development requirement IDs. Their union matches
  all plan IDs except `downstream-check`. A separate `downstream` array retains
  every downstream ID with its approved `owner` and `stage`, even when no builder
  work is assigned to it. Use `downstream: []` when there are none.
  Work bead descriptions hold precise scope, dependency IDs and test expectations.
  Each member has `omg.operation` and `omg.artifact_root` metadata.
- `work/<bead-id>.json`: `operation`, `work`, `revision`, and `checks` as below.
- `tests.json`: `operation`, `revision`, and `checks` for integrated development
  verification. Each check's `requirements` array names what it verifies; their
  union covers all `development-check` IDs and contains no downstream-check IDs.
- `review.json`: `revision`, `tests_sha256`, `verdict`, and `findings`. Each finding
  has `required` boolean, `status` (`open` or `resolved`), a `bead` for required
  findings, and an explanation/evidence. Keep resolved findings in later reviews.
  Stamp required finding beads with `omg.operation` and `omg.required=true`.
  The verifier checks the bead inventory as well as the review file, so omitting
  an unresolved finding from a later review cannot make it pass.
  Required findings pass only after the reviewer verifies their fixes and closes
  their beads. All required findings must resolve; nonrequired findings remain
  explicit follow-up work. Tests and review must refer to the current commit.
- `reconciliation.json`: `revision`, `review_sha256`, and `requirements`, exactly
  one row per plan ID with `id`, `status`, and `evidence`. Development requirements
  must be `implemented`. Verification-artifact rows also list committed source
  paths in `artifacts`. Downstream rows must be `pending-downstream` with approved
  `owner`/`stage`; explain where later evidence will be collected. This is a valid
  development outcome, not a waiver or a claim that downstream verification ran.
  Unfinished development obligations still fail. Reclassification requires a new
  approved spec snapshot.
- `publication.json`: assessed `revision`, `development: "verified"`, and actual
  `status`: `local`, `pushed`, or `pr-open`, according to baseline publication
  authorization. Published outcomes include `remote_ref`; PR outcomes also include
  `pr_url`. Local outcomes omit both. Set `deployed: false`, `pr_approved: false`.
  A PR is optional; a direct-branch push follows the repository's agreed policy.
  An opened PR is awaiting its approval process. None of these records claims
  deployment. Failed publication records its error and fails finalization.
  This receipt is the finalizer's own attestation of what it did. `verify
  --stage finalize` checks it for consistency with the baseline authorization
  and the assessed revision; it runs offline, contacts no remote, and neither
  proves that the push or PR happened nor that nothing was pushed.
- `report.json` is the post-settlement report receipt, checked by `verify --stage
  report` after the build root settles and `initiative settle` has recorded it:
  `operation`; `workflow` (the settled root, as recorded on the operation);
  `build_outcome` (the root's exact terminal `gc.outcome`: `pass`, `fail`,
  `skipped` or `canceled`, or `unknown` when the root carries none of these;
  distinct from this step's own outcome); `revision` (the assessed code commit;
  for a passed build this must equal publication.json's revision); `path` (the
  initiative-repository path `docs/initiatives/<slug>/reports/<operation>.md`);
  `id` (the document ID, `build-report.<slug>.<operation>`); `sha256` of the
  committed report; `commit` (the report commit in the initiative repository,
  made with `git commit --only -- <path>`, which must change only that path); and
  `status`. Publication authority comes only from the build's own finalized
  publication.json for a PASSED root, and only when the initiative repository is
  the rig checkout it published from: `pushed` for `push`, `pr-open` for
  `open_pr`, with the report's destination being exactly that receipt's
  `remote_ref` (the PR branch for `open_pr`, never the default branch); once
  those conditions hold, a missing, malformed or contradicting receipt is an
  error, never a local result. In every other case (no `push`/`open_pr`, a
  failed, canceled, skipped or unknown root even with a retained receipt, or a
  distinct initiative repository) `status: "local"` with `remote_ref: null` is
  the complete, passing outcome, not a blocker, and nothing is pushed; `report
  publish` normalizes a stale `pushed`/`failed` disposition back to that shape
  and keeps the artifact fields.
  Remote work is never done by the controller check, which runs offline in a
  sandbox without the worker's Git credentials. `gc <binding> report publish
  --root <artifact_root>` runs in the worker session: it repeats the local
  validation, then when authorized resolves one endpoint (the remote's fetch
  URL, which must equal its single push URL), reads that tip, requires it to
  contain the assessed revision, requires only report-only commits between that
  tip and the report commit, pushes the exact report SHA to that endpoint with a
  lease and with tag following and submodule recursion disabled, re-reads it
  and records `status: "pushed"`, `remote_ref`, and `publication`
  `{destination, remote, branch, url, base, pushed, observed, revision,
  report_blob, at}`. The controller check then requires that evidence to name
  this commit, blob, revision and destination, `base` to be a locally available
  commit containing the revision, and every commit in `base..commit` to be
  report-only. That is the trust boundary: the worker attests the remote
  observation; the controller verifies its consistency and the local objects,
  not the live remote. A blocker or remote failure records `status: "failed"`,
  `reason` and the retained Git `error`; the check fails with that blocker and
  the local commit stays recoverable on the report step. Success is printed
  only after the receipt write is durable; a push that succeeded without a
  persisted receipt exits 2 (`receipt_failed`) and is recorded by a rerun. Unrelated dirty,
  untracked or pre-staged files in the initiative repository are neither required
  to be clean nor allowed into the report commit.

Example verification receipt:

```json
{
  "operation": "build-app-<digest>",
  "work": "app-123",
  "revision": "<full-tested-commit>",
  "checks": [{
    "command": "npm test -- checkout.test.ts",
    "requirements": ["B01"],
    "exit_code": 0,
    "log": "logs/app-123-tests.txt",
    "sha256": "<sha256-of-log>"
  }]
}
```

Use at least one meaningful executable check. If no automated test applies,
record a reproducible executable inspection and explain its limitations. Missing
development prerequisites and required development tests that cannot run are
blockers. Downstream execution remains pending and never requires live credentials
or a promotion cycle in this run. Do not fabricate its results.

## Native convoy handoff

The architect creates a new implementation convoy using `gc convoy create`,
adds runnable work beads with `gc convoy add`, and sets both
`gc.input_convoy_id` and `omg.implementation_convoy` on the build workflow root.
Never include the launch source or workflow-control beads as implementation work.
Use dependency edges for implementation order. The engine drains this convoy
through `omg-work`, one item at a time, stopping after a failed item. Item work
inherits the drain's builder target. Each item resolves its one source member
from `gc convoy status <convoy_id> --json` at `.children[0].id`, then reads the
member metadata to find the shared artifact root. Do not manually close the
source member: the drain leaves source tasks open even after successful item
execution. Quality requires the exact decomposition inventory in a successful native
drain manifest, matching successful item workflows and finalizers, finished item
execution, and passing work/test/review receipts. Source closure is not execution
proof. The parent quality group runs repair → tester → reviewer, repeating
through the engine's check mechanism when review or integrated tests fail.

## Source-task bookkeeping

Reconcile and finalize gate verified execution and receipts, not source-task
closure. After writing reconciliation.json and passing `verify --stage reconcile`,
the reconciler may preview `gc <binding> settle --root <artifact_root> --city
<city-path> --rig <rig-name>`. This is part of reconciliation, not another graph
step. Preview is read-only, reruns quality and native execution validation, and
returns a plan without writing settlement.json. Exit 0 for a preview means only
that the plan is valid.

Use the same command with `--apply` only for revision-fenced settlement. The command
checks whether `gc bd update --help` advertises `--if-revision` and whether every
source exposes an integer revision. That run-time probe decides; on a backend
that does not advertise it, `--apply` returns `status: unsupported`, exit 2,
without mutation. Record source
IDs and this reason as pending bookkeeping, not a code-quality failure. Do not
substitute unconditional closure or retrofit `gc.source_bead_id` onto workflows.

On a supporting backend, apply revalidates evidence and closes sources in manifest
dependency order using revision CAS. Ownership, assignment, reservation, revision
or other validation/application conflicts return exit 1. Report the exact error
and any partial settlement.json results; do not claim settlement or overall
completion. Bookkeeping may remain pending while separately verified development
proceeds to its authorized handoff. Failed execution or quality never permits
closing source tasks as successful. Preserve failed receipts and review findings.
