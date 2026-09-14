Load `omg-initiative`. This build was explicitly requested for initiative
`{{initiative}}`, operation `{{operation}}`. Read its durable record and verify
the operation's explicit human launch authority. This is not a spec-approval step.

Approved inputs are frozen under `{{approved_root}}`, from commit
`{{approved_revision}}`. Read every spec and its PRD/HLD/ADR context directly.
Verify the frozen files against the Git revision and digest pinned on this
operation, not a newer acceptance another conversation may have recorded. The
requested rig must implement only its requirements and satisfy documented
cross-rig prerequisites. Return unresolved dependency/scope decisions as blocked,
never authorize other rigs implicitly.

For this trial, OMG supplies a `gc.build.requirements.v1` adapter to the official
planning chain. Canonical documents follow Hindsight's contract. Write the adapter at
`{{requirements_path}}` under `{{artifact_root}}`, outside docs/. Follow the
installed `gc.build.requirements.v1` schema and validator. Include its required
frontmatter and sections, preserve every stable requirement ID, and link each
claim to the exact approved spec revision and file hash. Carry all acceptance
criteria, exclusions, constraints, uncertainty and verification obligations.
Carry OMG's cost/stop rule as a governing constraint for all native planning,
implementation and review assignments: credible omission cost under expected use
versus implementation cost, delay and maintenance; only justified required
findings block, and existing requirements bind until the human changes scope.
This adapter is not a new approved spec or a document to ingest into Hindsight.

Record `gc.build.requirements_path` and its hash on the workflow root along with
the source revision/digest. Do not rewrite canonical OMG docs. The next native
step writes a distinct implementation plan. Set `gc.outcome=pass` before closing
on success; otherwise persist why and set `gc.outcome=fail`. Every scoped build
step must record pass/fail explicitly before closure.
