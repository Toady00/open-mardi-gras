# OMG for Gas City

OMG is a Gas City pack for software development workflows. It is moving from
an OpenCode-orchestrated workflow toward Gas City's native agents, packs,
commands, orders, and formulas. The intent is to use Gas City's mechanisms
where they fit rather than rebuild the old orchestration inside agent prompts.

This pack is early work. It currently lives in the `gascity/` directory of the
Open Mardi Gras repository, alongside the original OpenCode implementation.
This directory is the pack root and is intended to become a separate repository
later. Paths below are relative to this directory unless stated otherwise.

## Current contents

The schema-2 [pack manifest](pack.toml) declares `omg`, version `0.1.0`.

| Agent | Responsibility |
| --- | --- |
| [Product manager](agents/product-manager/prompt.template.md) | Product requirements, scope, decisions, and reviews. Writes documents, not implementation code. |
| [Architect](agents/architect/prompt.template.md) | System designs, architectural decisions, and reviews. Writes documents, not implementation code. |
| [Builder](agents/builder/prompt.template.md) | Implements tracked work and repairs findings in the target rig. |
| [Tester](agents/tester/prompt.template.md) | Verifies integrated behavior with reproducible evidence. |
| [Reviewer](agents/reviewer/prompt.template.md) | Independently reviews plans, code and required findings. |

PM and architect use tmux sessions and omit `scope`, allowing city and rig instances.
The build workers use tmux and rig scope.
Runtime session names use Gas City's per-session defaults. Keep friendly names
on conversation `--alias` values rather than a fixed agent `tmux_alias`: a manual
conversation and formula workers must be able to run from the same template at once.
Worker startup nudges explicitly claim routed work with `gc hook --claim --json`
and execute the claimed step, rather than beginning another discovery conversation.
They share the [initiative workflow](skills/omg-initiative/SKILL.md), pinned
[Archify](skills/archify/SKILL.md), and the
[shared Hindsight context fragment](template-fragments/omg-hindsight.template.md).

| Resource | Purpose |
| --- | --- |
| `gc omg initiative` | Revision records, conversation-facing approval state, and explicit workflow initiation |
| `gc omg verify` | Check approved baselines, execution records, test evidence and review outcomes |
| `gc omg settle` | Preview source-task bookkeeping; apply only with advertised revision CAS |
| `omg-docs` | Initial PRD, HLD, necessary ADRs and specs, followed by shared refinement |
| `omg-refine` | Whole-set assessment, successive revision and distinct product/technical cross-review |
| `gc omg report` | Publish a build report under the worker's Git identity only when the build's own publication receipt authorizes it |
| `omg-build` / `omg-work` | OMG-owned planning, tracked implementation, testing, review, reconciliation and post-settlement reporting |

Approval does not launch a build. After approving specs, the human separately
requests initiation through the agent. See the [implementation decisions](docs/implementation-decisions.md)
for the clarification to the original [visual proposal](docs/archify/README.md).

## Importing the pack

In your city's configuration, import OMG and Hindsight as siblings:

```toml
[imports.omg]
source = "/absolute/path/to/omg-pack"

[imports.hindsight]
source = "https://github.com/Toady00/hindsight-gc-pack.git"
version = "sha:1ca1807a3bd3df2866f8653a9492d0b83146b8a7"
```

While this pack remains inside the original repository, the source path must end
in `gascity`, not at the parent repository root. A city-level import supports
city instances and expands eligible agents across configured rigs; an explicit
rig import with the same binding takes precedence for that rig.

Run `gc import install` after configuration. OMG has no methodology-pack import.
The city owns the separate Hindsight import and its
version selection; the example uses the inspected revision. This keeps the
archivist at `hindsight.archivist`, outside OMG's namespace, and provides the
`gc hindsight` commands. Configure the build rig normally:

```toml
[[rigs]]
name = "app"
path = "/absolute/path/to/app"

```

Build routes use OMG's own agents; the Hindsight read fragment uses the `hindsight`
binding. OMG's own binding can change; pass
`--binding <name>` when launching through the initiative command so its formula
targets match. City-initiated documents stay in city `docs/initiatives/<id>`;
rig-initiated documents use that rig's same relative directory. The city must be
a Git repository to own published initiative documents. Select a target rig
explicitly for a city initiative's build. Starting one rig does not start others.

Runtime prerequisites are Gas City's formula compiler v2, scope teardown and
`gc beads metadata-cas`, a working shared Beads store, Git, Python 3, Mike Farah's
`yq` v4, Bash, jq, shasum, and Node.js for Archify. Configure the provider and Hindsight bank in the
consuming city. This pack does not start a custom controller or retainer.

For a first live run, follow [the trial guide](docs/first-build.md). Build checks
use Bash/yq/jq and Python's standard library and install no runtime dependencies.
Python also runs the initiative ledger and source-task settlement command.

## Working through conversation

Ask either role to explore an initiative. The agent records a living discussion
summary while iterating visuals, then records your approval of the exact IR and
rendered revision. Document generation always enters shared refinement. When it
finishes, the agent leaves an idle durable record for later review.

In another session, ask "What's waiting for my review?" The agent lists those
records and presents the relevant documents. Discuss changes or approve selected
specs. The agent publishes accepted statuses separately. Say "Start the build for
this initiative in app" when you want implementation to begin.

`initiative start` checks local tools and freezes the original approved Git blobs.
It writes a baseline inventory and supplies an operation-specific absolute runtime
artifact root. The architect reads those specs and the maintained initiative build
report, compares spec/code baselines with the actual repository, and consults current
Hindsight conventions when planning changes and verification of reusable work. OMG owns
the execution-record contract in the [build skill](skills/omg-build/SKILL.md).
There is no requirements translation or official build-artifact schema dependency.

The shared [development contract](skills/omg-development/SKILL.md) applies to app
code and IaC. Specs explicitly classify implementation, development checks,
downstream verification artifacts to deliver, and downstream checks to execute
later. The classification lives in fenced `omg-delivery` YAML in the owning specs
and is approved with their Git snapshot. Build records must match it exactly.
CI/CD owns promotion/deployment; downstream failures create new work rather than
holding development open. A local-only result, direct-branch push and opened PR
are distinct handoffs; none proves PR approval, deployment or production acceptance.

Commands are supporting tools for agents, not a required human interface. See
[command help](commands/initiative/help.md) for the exact operations and recovery.
Records use native atomic metadata updates in the city work store. Launch intent
is persisted before external dispatch. Repeated build requests for the same rig
and approved snapshot return its receipt. Lost acknowledgements require inspecting
the native workflow and binding its existing root, not blindly repeating dispatch.
For a failed launch that created no workflow, `initiative abandon` records an
operator-authorized abandoned attempt after the launcher has exited and an
exact-store check finds no workflow evidence. A new explicit request can then
retry. Closed/partial workflow evidence and store errors prevent abandonment.
After an actual failed build settles, an explicit `start --retry <operation>`
creates a separate attempt for the same approval. New approved revisions use a
fresh normal start. Repeated retry requests deduplicate and old artifacts remain.
City launches with relocated graph storage require native storage inspection;
the current CLI cannot prove absence there with an exact-store list.

An authoring workflow gets three automatic refinement attempts. An unresolved
required finding or decision then returns to conversation. This bounds unattended
cost without weakening requirements. A later resolved decision can start another
refinement run. Human wait time consumes no authoring agent.

A human decision interrupts authoring immediately rather than consuming the
remaining review attempts. Workers finish through `initiative complete-step`,
which ends the current check's retry budget and closes the work as failed; native
scope dispatch skips the rest and retains the handoff. Ordinary required review
findings still get bounded repair attempts. The engine's pass/fail is stored
separately from the initiative operation's `result`, so a human interruption is
shown as `needs-human` and a passed graph without passing document reviews is
`incomplete`, not approval-ready.

The initiating conversation is captured at launch. Decisions and final results
send mail plus a queued nudge, prompting the PM to present the question or next
action. Delivery errors and receipts remain visible on the initiative; `notify`
retries delivery, and `watch --notify <session-id>` repairs or changes the return
address. Human answers use `resolve` against the exact decision ID. Resolution
does not restart execution or approve documents. After settlement, a requested
`refine` fills missing initial documents before cross-reviewing the complete set.

Older or untracked documents are reference candidates unless their current
authority is established. Authors separate design decisions from external
activation prerequisites. Useful Archify views are chosen by question, rather
than defaulting to workflow charts; visual-check sidecars live under `.omg/`.

Build reporting runs as native post-settlement work, including on failure. Its
completion is separate from the build root's terminal status. One cumulative report
at `docs/initiatives/<slug>/reports/build-report.md`, with stable ID
`build-report.<initiative-bead-id>`, distinguishes implemented, reviewed and actually
published code against each rig's assessed spec revision/digest and code SHA.
Later passes edit it in place, preserving valid assessments, updating changed
requirements and removing resolved gaps. Attempt history remains in operation
artifacts, not the report.
Initiative metadata CAS serializes report writers with `begin-report`/`finish-report`;
the verifier checks the prior report blob, and pending reports block new launches.
The report step is checked: the architect commits only the report (`git commit
--only`) in the initiative repository and records its receipt. That local commit
completes the step as `local`, neither published nor shipped, unless a passed
build's own finalized publication receipt published code from the same checkout;
then `gc omg report publish`, run under the worker's Git identity, pushes exactly
the validated report SHA to that receipt's ref after proving the remote holds the
assessed revision and that only report commits are outgoing, and records the
evidence the offline controller check inspects. A blocker or failed push stays
recoverable on the report bead.

## Hindsight

OMG uses the separately city-imported `hindsight` Gas City pack; it does not
import Hindsight transitively. PM and architect always
receive OMG's shared Hindsight context fragment through `append_fragments` in
their agent configuration. The consuming city supplies
`HINDSIGHT_BANK` and the API/profile configuration; the pack assumes no bank.
The prompt fragment belongs to OMG and has no dependency on Hindsight's template
fragments. Its `gc hindsight read` calls and document shipping require the city's
direct `hindsight` import shown above.

The fragment tells both agents to list available mental models when building
conversation context and fetch the content of models they judge relevant. They
reflect as soon as a useful background question emerges and may reflect again
as the conversation develops. This replaces Hindsight's generic
once-per-task brief for these agents. The instructions are part of their rendered
prompts, not dependent on an optional skill load, and are maintained in one file.

Hindsight owns the document-memory integration:

- Commands and scheduled orders ship published documents to Hindsight.
- The archivist manages memory and arbitrates proposed knowledge.
- The surveyor produces a repository's `docs/current-state.md`, including
  periodic surveys when configured.

OMG produces product and architecture documents and uses these services.
The Hindsight pack's README and operations documentation
define bank configuration, document schemas, publishing, and survey setup.
Document shipping reconciles the canonical Git branch; writing a local Markdown
file alone does not publish it to memory.

Authored Markdown uses Hindsight schema 2 and stable document IDs. Drafts and
accepted revisions ship repeatedly through the existing pipeline. IR, HTML,
comparison evidence and receipts are excluded, including indirect attachments.
Raw review and execution artifacts live under `.omg/`, outside the scanned docs
tree. Accepted documents express approved direction; reports provide implementation
evidence at a stated code revision. Ingestion never approves or launches a build.

For document format, frontmatter and approval provenance, `omg-initiative` directs
authors to the separately installed `hindsight-shipping` skill and its validator.
OMG defines document purpose, scope approval and build initiation; Hindsight owns
the document-format and ingestion contract.

## Verification

Use the standard-library tests, with no extra test framework:

```sh
python3 -m unittest discover -s test -p 'test_*.py' -v
```

With `gc` installed, the tests also compile formulas and discover commands and
agents in a temporary city with only OMG imported. They do not start agents,
publish documents, or write to a real memory bank.

The initial verification covers Git revision/readiness checks, separate approval
and launch, guarded abandonment/retry, and native formula compilation. It also
executes the refinement checker with a stubbed GC transport and no `yq` on PATH,
and verifies that OMG's compiled check entry paths resolve to executable pack assets.
Build tests run the shipped Bash checker with real Git/yq/jq and isolated bead
reads. They cover altered baselines, missing requirement coverage, wrong convoy
membership, failed or stale verification, unresolved findings and incomplete
reconciliation, including changed HOME and restricted PATH.
The development-boundary cases cover pending downstream evidence, required
downstream test artifacts, local-check coverage, forbidden reclassification,
and local/push/PR publication claims. Report tests commit a report on top of
local code in a dirty checkout with pre-staged changes and cover local
completion, path-only commits, every terminal root outcome plus missing ones,
commits that sweep in other files, stale or false receipts, initiative-directory
validation, frontmatter and content checks, unauthorized publication, a distinct
docs repository, retained receipts on non-passed roots, and `report publish`
against a real bare remote: exact-SHA push with recorded evidence, idempotent
reruns, an offline controller check with the remote unreachable, tampered
evidence, an unrelated outgoing commit blocked without remote mutation,
report-only retries, a moved remote, a remote that lost the assessed revision,
and authentication, missing-branch and rejected-push failures whose Git stderr
is retained; plus mismatched or multiple push URLs rejected before any write,
no tag or submodule side effects, credential redaction, malformed authorized
refs treated as errors, receipt-persistence failure after a successful push,
normalization of stale dispositions once authority lapses, and preflight
failures that leave a prior successful receipt untouched. Failed-build retry tests preserve prior
attempts and reject live, successful, foreign or differently approved roots.
Handoff tests cover exact-decision resolution, pre-snapshot human reviews,
notification retries, concurrent state updates, authoring recovery and semantic
results. A native-runtime test cooks the actual refinement formula into an
isolated file store and runs Gas City's control transitions, proving that a
human interruption skips remaining work without a second iteration and retains
the final handoff.
A live managed-city rehearsal is still required to establish end-to-end provider,
controller, publication and Hindsight behavior in a consuming installation.

The standalone build formula uses Gas City's shared single-lane convoy drain for
implementation and checked repair/test/review groups. Scope failure aborts remaining
build work; teardown preserves the final report. Both command and formula checks
execute the same shipped verify.sh through supported pack asset paths. The current
workflow requires a shared local rig checkout.

The drain leaves implementation source tasks open. Quality validates the exact
successful native manifest, item workflows and finalizers, plus current passing
receipts. Repair/test/review workers complete their own steps; the controller runs
the full quality gate after review. Reconcile and finalize gate execution evidence,
not source-task closure.

Within reconciliation, after reconciliation.json and passing reconcile verification,
`gc omg settle --root <artifact-root> --city <city-path> --rig <rig-name>` previews
source-task settlement without mutation. `--apply` checks for advertised
`gc bd update --if-revision` support and integer source revisions before applying
revision CAS. That run-time probe is authoritative: a backend that does not
advertise it returns unsupported/exit 2 without mutation. Record pending source
IDs and that reason separately from code
quality. Other conflicts and partial closures also remain explicit, with no
settlement or overall-completion claim. There is no unconditional-close fallback
or `gc.source_bead_id` retrofit. Failed runs preserve tasks and findings. See the
[build skill](skills/omg-build/SKILL.md#source-task-bookkeeping) for the procedure.

## Archify

[Archify](https://github.com/tt-a1i/archify) is an upstream skill for generating
architecture and workflow diagrams as standalone HTML and exported images.
Its distributable skill lives in the upstream repository's `archify/` directory,
not at that repository's root.

### Distribution decision

The complete upstream directory is vendored at `skills/archify/`.
Gas City discovers pack-level `skills/<name>/SKILL.md` directories and
materializes skill-directory links into the provider's project skill directory.
Keeping the CLI, renderers, schemas, references, and assets together preserves
Archify's relative resource paths.

These are ordinary Git-tracked files, not a submodule or a link to a global skill
installation. No download is needed at runtime. The initial snapshot is Archify
`v2.16.0`; [upstream/archify.json](upstream/archify.json) records the authoritative
full commit SHA, repository URL, and source subtree.

This is an unmodified source snapshot, not upstream's filtered release package.
It includes development files. Some `package.json` scripts, including the full
`npm test`, expect scripts outside this subtree in the upstream repository.
Run those in an upstream checkout, not inside this skill. The runtime CLI needs
Node.js 18 or later and does not require an `npm install`.

### Keeping up with upstream

Maintainer prerequisites are `just`, Bash, Git, `jq`, and `tar`, plus network
access to upstream. Run from the pack root:

```sh
just archify-sync
```

The parent repository also forwards `just archify-sync` to this pack's recipe.
The pack-local command and script do not depend on that parent repository.

The command reads the pin, deletes all of `skills/archify/`, fetches that exact
commit, and extracts its complete `archify/` subtree into place. Local edits
are deliberately discarded. Whole-directory replacement removes files upstream
deleted or renamed. Repeating a successful sync with the same pin produces
identical contents and executable bits.

A fetch or extraction failure exits nonzero and leaves the destination absent
or incomplete. There is no rollback. Fix the failure and rerun, or restore the
snapshot from Git. The command never changes the pin or makes a commit.

To update:

1. Choose a release using upstream's [stable update manifest](https://tt-a1i.github.io/archify/skill-updates/archify/stable.json)
   or release history, and resolve its tag to a full commit SHA.
2. Edit `commit` in `upstream/archify.json`, then run `just archify-sync`.
3. Review the snapshot and license changes. Keep OMG-specific integration
   outside `skills/archify/` so subsequent syncs cannot overwrite it.
4. Test the selected release and commit the pin and snapshot together.

There is no scheduled update check. Archify's own update notification does not
change this pack's pin; maintainers update it through the process above.

## License

OMG's own code and documentation are licensed under the [MIT License](LICENSE),
copyright 2026 Brandon Dennis.

Archify is independently authored and retains its own copyright and license.
See [third-party notices](THIRD_PARTY_NOTICES.md) for attribution and the
additional license considerations that apply to its bundled assets.
