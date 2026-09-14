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

Both agents use tmux sessions and omit `scope`, allowing city and rig instances.
They share the [initiative workflow](skills/omg-initiative/SKILL.md), pinned
[Archify](skills/archify/SKILL.md), and the
[shared Hindsight context fragment](template-fragments/omg-hindsight.template.md).

| Resource | Purpose |
| --- | --- |
| `gc omg initiative` | Revision records, conversation-facing approval state, and explicit workflow initiation |
| `omg-docs` | Initial PRD, HLD, necessary ADRs and specs, followed by shared refinement |
| `omg-refine` | Whole-set assessment, successive revision and distinct product/technical cross-review |
| `omg-build` | Official native planning/build/review continuation, spec reconciliation and post-settlement reporting |

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

Run `gc import install` after configuration. OMG's manifest pins the official
Gas City methodology pack. The city owns the separate Hindsight import and its
version selection; the example uses the inspected revision. This keeps the
archivist at `hindsight.archivist`, outside OMG's namespace, and provides the
`gc hindsight` commands. Build rigs also need the official role agents, as in
the official pack's installation:

```toml
[[rigs]]
name = "app"
path = "/absolute/path/to/app"

[rigs.imports.gc]
source = "https://github.com/gastownhall/gascity-packs.git//gascity/roles"
version = "sha:b43abe633283a7769346d32360ff747d561fa0a4"
```

Native build routes use `gc.*`; the Hindsight read fragment uses the `hindsight`
binding. Keep those dependency bindings. OMG's own binding can change; pass
`--binding <name>` when launching through the initiative command so its formula
targets match. City-initiated documents stay in city `docs/initiatives/<id>`;
rig-initiated documents use that rig's same relative directory. The city must be
a Git repository to own published initiative documents. Select a target rig
explicitly for a city initiative's build. Starting one rig does not start others.

Runtime prerequisites are Gas City's formula compiler v2, scope teardown and
`gc beads metadata-cas`, a working shared Beads store, Git, Python 3, Mike Farah's
`yq`, and Node.js for Archify. Configure the provider and Hindsight bank in the
consuming city. This pack does not start a custom controller or retainer.

## Working through conversation

Ask either role to explore an initiative. The agent records a living discussion
summary while iterating visuals, then records your approval of the exact IR and
rendered revision. Document generation always enters shared refinement. When it
finishes, the agent leaves an idle durable record for later review.

In another session, ask "What's waiting for my review?" The agent lists those
records and presents the relevant documents. Discuss changes or approve selected
specs. The agent publishes accepted statuses separately. Say "Start the build for
this initiative in app" when you want implementation to begin.

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
City launches with relocated graph storage require native storage inspection;
the current CLI cannot prove absence there with an exact-store list.

An authoring workflow gets three automatic refinement attempts. An unresolved
required finding or decision then returns to conversation. This bounds unattended
cost without weakening requirements. A later resolved decision can start another
refinement run. Human wait time consumes no authoring agent.

Build reporting runs as native post-settlement work, including on failure. Its
completion is separate from the build root's terminal status. Reports distinguish
implemented, reviewed and actually published code against the pinned spec revision.

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

Set `GC_BASE_PACK` and `HINDSIGHT_PACK` to local checkout pack roots to also compile
the formulas using the installed `gc` binary. Tests use temporary Git repositories,
a local methodology dependency, and a sibling city-level Hindsight import. They
also verify that the archivist resolves as `hindsight.archivist`. They do not
start agents, publish documents, or write to a real memory bank.

The initial verification covers Git revision/readiness checks, separate approval
and launch, guarded abandonment/retry, and native formula compilation. It also
executes the refinement checker with a stubbed GC transport and no `yq` on PATH,
and verifies all compiled check paths resolve to executable pack assets.
A live managed-city rehearsal is still required to establish end-to-end provider,
controller, publication and Hindsight behavior in a consuming installation.

The build formula extends `build-from-plan-base`. Gas City replaces whole steps
on override, so scoped steps explicitly preserve the pinned native dependencies,
routes, checks and drains. Their descriptions resolve from the dependency's asset
layers. Check executables also resolve through those layers using `../assets/`
paths, rather than depending on an obsolete `.gc/scripts` installation shim.
The controller compares Git bytes for readiness; `yq` is needed for agent-side
snapshot creation and accepted-document comparison. Review the overrides when
updating the official pack pin.

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
