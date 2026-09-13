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

Both agents began as copies of the original OMG personas. They use tmux sessions
and omit `scope`, allowing city and rig instances. Their presence does not mean
the original OMG planning, build, and review workflow has been ported.

The pack includes the vendored [Archify skill](skills/archify/SKILL.md). It does
not yet contain its own Gas City commands, orders, or formulas. Hindsight
dependency wiring is still planned, not configured in `pack.toml` today.
Nothing here installs the sibling OpenCode product.

## Importing the pack

In your Gas City configuration, point an import at this pack root:

```toml
[imports.omg]
source = "/absolute/path/to/omg-pack"
```

While this pack remains inside the original repository, the source path must end
in `gascity`, not at the parent repository root. A city-level import supports
city instances and expands eligible agents across configured rigs; an explicit
rig import with the same binding takes precedence for that rig.

## Hindsight

OMG is intended to depend on the separate `hindsight` Gas City pack, also
maintained by Brandon Dennis. Its current development checkout is
`~/code/stacked-chips-v2/hindsight`.

Hindsight owns the document-memory integration:

- Commands and scheduled orders ship published documents to Hindsight.
- The archivist manages memory and arbitrates proposed knowledge.
- The surveyor produces a repository's `docs/current-state.md`, including
  periodic surveys when configured.

OMG should produce product and architecture documents and use these services,
not duplicate them. The Hindsight pack's README and operations documentation
define bank configuration, document schemas, publishing, and survey setup.
Document shipping reconciles the canonical Git branch; writing a local Markdown
file alone does not publish it to memory.

For now, configure Hindsight separately in the consuming city. The intended
pack dependency is a transitive `[imports.hindsight]` import once its portable
source and version policy are chosen. The development checkout path above is
not a distributable dependency declaration.

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
