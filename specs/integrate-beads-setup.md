# Integrate Existing Beads Setup

## Overview

Ship the existing beads workflow — currently a local `.opencode/plugins/beads.ts`
plugin plus a collection of commands, agents, skills, and prompts in `.opencode/` —
as part of the `@toady00/open-mardi-gras` npm package. This gives anyone who
installs the package access to the full beads-powered spec → decompose → work → review
workflow without manually copying files.

The integration also requires resolving a known conflict between the BeadsPlugin
and the ThenChainingPlugin. Both plugins hook into `session.idle` and `chat.message`
events, and the beads context injection races with then-chain advancement, causing
interleaved messages and broken chains. This must be fixed before the two plugins
can ship together.

### Why

The beads workflow is currently only usable in this repo because the commands,
agents, skills, and plugin code live in `.opencode/` (local development files).
Packaging them means:

1. Other projects can use the full spec/decompose/work/review workflow by
   installing a single npm package and running a setup command.
2. The two plugins (ThenChaining and Beads) are tested and validated to work
   together without interference.
3. The HelloWorldPlugin placeholder is removed.

### What Changes

- New `BeadsPlugin` export in `src/plugins/beads.ts`
- New `omg-build` agent shipped with the package
- New CLI setup command: `npx @toady00/open-mardi-gras setup`
- All shipped commands/agents/skills renamed from `bd-` prefix to `omg-` prefix
- HelloWorldPlugin removed
- Local `.opencode/plugins/beads.ts` converted to a thin import wrapper
- Plugin conflict between BeadsPlugin and ThenChainingPlugin resolved

---

## Requirements

### R1: BeadsPlugin runtime (`src/plugins/beads.ts`)

Port the existing `.opencode/plugins/beads.ts` into `src/plugins/beads.ts` as an
exported plugin factory function, matching the pattern of `ThenChainingPlugin`.

**R1.1** Export `BeadsPlugin` as a named export from `src/index.ts`.

**R1.2** On first user message per session (`chat.message` hook), run `bd sync`
then `bd prime` and inject the output as a synthetic user message wrapped in
`<beads-context>` tags, followed by a `<beads-guidance>` block. If `bd prime`
returns empty output, skip injection silently.

**R1.3** On `session.compacted` event, re-inject beads context (same as R1.2).

**R1.4** On `session.idle` event, run `bd sync` quietly (no context injection).

**R1.5** Skip injection if beads context already exists in the session
(handles plugin reload/reconnection). Check by scanning recent messages for
the `<beads-context>` tag.

**R1.6** The plugin must accept zero configuration for now. The factory function
signature should be `BeadsPlugin(): Plugin` (no config parameter yet).

**R1.7** All `bd` and shell invocations must be wrapped in try/catch. On error,
log via `client.app.log` and continue. The plugin must never crash OpenCode.

### R2: Plugin conflict resolution (BeadsPlugin × ThenChainingPlugin)

The BeadsPlugin and ThenChainingPlugin both subscribe to `session.idle` and
`chat.message`. When both are active, the beads context injection races with
then-chain advancement, causing:

- Beads context injected mid-chain as a visible user message, causing the model
  to respond to beads state instead of advancing the chain
- Then-chain steps interleaved with beads responses
- Chain commands failing silently (observed: `undefined is not an object
  (evaluating 'command2.agent')` when dispatching chained commands during
  concurrent plugin activity)

**R2.1** The two plugins must coordinate so that beads context injection
(`bd prime` via `client.session.prompt`) never fires while a then-chain is
actively executing. "Actively executing" means from the moment a command with
a `then` key starts until the chain fully completes or is interrupted.

**R2.2** The beads `session.idle` sync (`bd sync`) is safe to run concurrently
with then-chains because it produces no visible output. This must remain
unchanged — `bd sync` always runs on idle regardless of chain state.

**R2.3** The beads `chat.message` injection (first message per session) fires
before any command has been executed and is guarded by the `injectedSessions`
set (R1.5), so it cannot conflict with then-chains on subsequent messages.

**R2.4** The beads `session.compacted` re-injection must also be deferred if
a then-chain is active. The context should be injected once the chain completes
or is interrupted.

**R2.5** Implementation: introduce a `PluginCoordinator` singleton in
`src/coordination.ts` that both plugins import. The coordinator exposes:

```typescript
// src/coordination.ts
class PluginCoordinator {
  // Called by ThenChainingPlugin to register its ChainStateManager
  registerChainState(manager: ChainStateManager): void

  // Called by BeadsPlugin before injecting context.
  // Returns true if any registered ChainStateManager reports an active
  // chain for the given sessionID.
  isChainActive(sessionID: string): boolean

  // Called by BeadsPlugin to queue a callback for when a chain completes
  // on the given session. The callback fires once, then is removed.
  onChainComplete(sessionID: string, callback: () => void): void

  // Called by ThenChainingPlugin (from ChainExecutor.processNext)
  // when a chain fully completes. Fires and removes all queued callbacks
  // for that session.
  notifyChainComplete(sessionID: string): void
}

// Module-level singleton — both plugins import the same instance
export const coordinator: PluginCoordinator
```

**R2.6** If a then-chain is active when compaction occurs, the beads plugin
must call `coordinator.onChainComplete(sessionID, callback)` to queue the
re-injection. The callback fires when `notifyChainComplete` is called.

**R2.7** The ThenChainingPlugin must call `coordinator.notifyChainComplete()`
from the `ChainExecutor.processNext()` method when it returns `false`
(chain fully complete), and from `ChainStateManager.interrupt()` when a
chain is interrupted by the user. `notifyChainComplete()` must be a no-op
when no callbacks are queued (safe to call unconditionally).

**R2.8** If multiple compactions occur while a chain is active, only one
re-injection should fire when the chain completes (deduplicate queued
callbacks per session).

### R3: CLI setup command

Create a CLI entry point that copies commands, agents, skills, and prompts
into the user's `.opencode/` directory.

**R3.1** Invocation: `npx @toady00/open-mardi-gras setup`

**R3.2** The setup command copies the following files from the package into
the user's project `.opencode/` directory:

| Source (in package)                          | Destination (in project)                  |
|----------------------------------------------|-------------------------------------------|
| `opencode/commands/omg-work.md`              | `.opencode/commands/omg-work.md`          |
| `opencode/commands/omg-spec.md`              | `.opencode/commands/omg-spec.md`          |
| `opencode/commands/omg-spec-track.md`        | `.opencode/commands/omg-spec-track.md`    |
| `opencode/commands/omg-spec-refine.md`       | `.opencode/commands/omg-spec-refine.md`   |
| `opencode/commands/omg-decompose.md`         | `.opencode/commands/omg-decompose.md`     |
| `opencode/commands/omg-status.md`            | `.opencode/commands/omg-status.md`        |
| `opencode/commands/omg-cleanup.md`           | `.opencode/commands/omg-cleanup.md`       |
| `opencode/agents/omg-build.md`               | `.opencode/agents/omg-build.md`           |
| `opencode/agents/omg-spec-writer.md`         | `.opencode/agents/omg-spec-writer.md`     |
| `opencode/agents/omg-reviewer.md`            | `.opencode/agents/omg-reviewer.md`        |
| `opencode/agents/omg-decomposer.md`          | `.opencode/agents/omg-decomposer.md`      |
| `opencode/skills/omg-commands/SKILL.md`      | `.opencode/skills/omg-commands/SKILL.md`  |
| `opencode/skills/omg-epics/SKILL.md`         | `.opencode/skills/omg-epics/SKILL.md`     |
| `opencode/prompts/omg-workflow.md`           | `.opencode/prompts/omg-workflow.md`       |

**R3.3** The setup command creates any missing directories (`.opencode/commands/`,
`.opencode/agents/`, `.opencode/skills/omg-commands/`, etc.).

**R3.4** If a destination file already exists, overwrite it without prompting.
This supports upgrading to newer versions of the package.

**R3.5** The setup command writes `.workflow.yaml` with the following content:

```yaml
specs:
  directory: docs/specs
```

If `.workflow.yaml` already exists, overwrite it.

**R3.6** The setup command prints a summary of what was copied, the package
version, and next steps (e.g., "Add BeadsPlugin() to your opencode config").

**R3.7** Add a `bin` entry to `package.json` with the key
`@toady00/open-mardi-gras` pointing to the setup script (`dist/cli/setup.js`).
Users invoke the setup command as `npx @toady00/open-mardi-gras setup`.

**R3.8** The setup script is written in TypeScript in `src/cli/setup.ts` and
compiled to `dist/cli/setup.js` by the existing build process. The compiled
file must include a `#!/usr/bin/env node` shebang. Since `tsc` does not emit
shebangs, add a post-build step to the `build` script in `package.json` that
prepends the shebang to `dist/cli/setup.js` (e.g.,
`echo '#!/usr/bin/env node' | cat - dist/cli/setup.js > tmp && mv tmp dist/cli/setup.js && chmod +x dist/cli/setup.js`).

**R3.9** If the user runs the CLI with no arguments or an unrecognized
argument, print a brief usage message showing available commands (currently
only `setup`) and exit with code 1.

### R4: Shipped file content (rename and update references)

All shipped files must be renamed from the `bd-` prefix to `omg-` and all
internal cross-references updated.

**R4.1** File renames (command prefix `bd-` → `omg-`, skill prefix
`beads-`/`adr-` → `omg-`, prompt prefix `beads-` → `omg-`):

| Original                    | Shipped as                |
|-----------------------------|---------------------------|
| `bd-work.md`                | `omg-work.md`             |
| `bd-spec.md`                | `omg-spec.md`             |
| `bd-spec-track.md`          | `omg-spec-track.md`       |
| `bd-spec-refine.md`         | `omg-spec-refine.md`      |
| `bd-decompose.md`           | `omg-decompose.md`        |
| `bd-status.md`              | `omg-status.md`           |
| `bd-cleanup.md`             | `omg-cleanup.md`          |
| `bd-spec-writer.md`         | `omg-spec-writer.md`      |
| `bd-reviewer.md`            | `omg-reviewer.md`         |
| `bd-decomposer.md`          | `omg-decomposer.md`       |
| `beads-commands/SKILL.md`   | `omg-commands/SKILL.md`   |
| `beads-epics/SKILL.md`      | `omg-epics/SKILL.md`      |
| `beads-workflow.md`         | `omg-workflow.md`         |
| *(new)* `omg-build.md`      | `omg-build.md`            |

**R4.2** Internal reference updates (these are string replacements within
file contents — the `bd` CLI commands like `bd create`, `bd sync`, etc.
must NOT be renamed):

| Old reference              | New reference              | Where it appears                              |
|----------------------------|----------------------------|-----------------------------------------------|
| `agent: build`             | `agent: omg-build`         | `omg-work.md`                                 |
| `agent: bd-spec-writer`    | `agent: omg-spec-writer`   | `omg-spec.md`, `omg-spec-refine.md`           |
| `agent: bd-decomposer`    | `agent: omg-decomposer`   | `omg-decompose.md`                            |
| *(new)* `omg-spec-track.md`| `agent: omg-spec-writer`   | `omg-spec-track.md` (add agent field)         |
| `@bd-reviewer`             | `@omg-reviewer`            | `omg-work.md`, `omg-decompose.md`, `omg-epics/SKILL.md` |
| `/bd-spec-refine`          | `/omg-spec-refine`         | `omg-spec.md`, `omg-spec-track.md`            |
| `/bd-decompose`            | `/omg-decompose`           | `omg-spec.md`, `omg-spec-track.md`, `omg-spec-refine.md` |
| `beads-commands` (skill)   | `omg-commands`             | `omg-work.md`, `omg-workflow.md`, agents       |
| `beads-epics` (skill)      | `omg-epics`                | `omg-work.md`, `omg-workflow.md`, agents       |
| `{file:../prompts/beads-workflow.md}` | `{file:../prompts/omg-workflow.md}` | All shipped agents |

**R4.3** Remove all ADR-related references from shipped files:
- Remove the `adr-workflow` skill reference from `omg-workflow.md`
- Remove any ADR skill loading instructions from agents

**R4.4** The `omg-workflow.md` prompt must reference the renamed skills
(`omg-commands`, `omg-epics`) and omit the `adr-workflow` skill.

**R4.5** Add `agent: omg-spec-writer` to the frontmatter of `omg-spec-track.md`
(the original `bd-spec-track.md` had no agent field).

### R5: New `omg-build` agent

**R5.1** Create an `omg-build.md` agent definition that mirrors the behavior
of OpenCode's built-in `build` agent. This is a general-purpose coding agent
with full tool access. The agent definition must include:

- `description`: General-purpose coding agent for the OMG workflow
- `mode: primary`
- `tools`: full access (bash, read, write, edit, glob, grep, task, webfetch,
  skill, todowrite)
- `permission: bash:allow`
- Include `{file:../prompts/omg-workflow.md}` for beads context

**R5.2** The `omg-work.md` command must reference `agent: omg-build` instead
of `agent: build`.

### R6: Shipped file storage in the package

**R6.1** The shipped markdown files (commands, agents, skills, prompts) must
be stored in an `opencode/` directory at the package root, organized as:

```
opencode/
  commands/
    omg-work.md
    omg-spec.md
    omg-spec-track.md
    omg-spec-refine.md
    omg-decompose.md
    omg-status.md
    omg-cleanup.md
  agents/
    omg-build.md
    omg-spec-writer.md
    omg-reviewer.md
    omg-decomposer.md
  skills/
    omg-commands/
      SKILL.md
    omg-epics/
      SKILL.md
  prompts/
    omg-workflow.md
```

**R6.2** The `opencode/` directory must be included in the `files` array in
`package.json` so it ships with the npm package.

### R7: HelloWorldPlugin removal

**R7.1** Delete `src/plugins/hello-world.ts`.

**R7.2** Remove the `HelloWorldPlugin` and `HelloWorldPluginConfig` exports
from `src/index.ts`.

### R8: Local development wrapper update

**R8.1** Update `.opencode/plugins/beads.ts` to be a thin wrapper that imports
`BeadsPlugin` from `../../dist/index.js`, matching the pattern of
`.opencode/plugins/then-chaining.ts`.

**R8.2** The local `.opencode/` commands, agents, skills, and prompts used for
development of this repo should continue to use the `bd-` prefix (they are
the development originals, not the shipped copies). The shipped `omg-` prefixed
files live in the `opencode/` directory at the package root.

### R9: Package.json updates

**R9.1** Add `"bin"` entry with key `@toady00/open-mardi-gras` pointing
to `dist/cli/setup.js`.

**R9.2** Add `opencode/` to the `"files"` array.

**R9.3** Update the README to document:
- `BeadsPlugin` usage and configuration
- Prerequisites: `bd` and `yq` must be on `$PATH`
- The setup command invocation
- That `bd` and `yq` are only required if using `BeadsPlugin`
  (ThenChainingPlugin has no external dependencies)

---

## Acceptance Criteria

### Plugin Runtime

- [ ] `import { BeadsPlugin } from '@toady00/open-mardi-gras'` resolves without error
- [ ] `BeadsPlugin()` returns a valid Plugin that OpenCode can load
- [ ] First user message in a session triggers `bd prime` injection with
      `<beads-context>` tags
- [ ] Subsequent messages in the same session do not re-inject
- [ ] `session.compacted` event triggers re-injection
- [ ] `session.idle` event triggers `bd sync` quietly (no visible message)
- [ ] If `bd prime` returns empty output, no injection occurs

### Plugin Conflict Resolution

- [ ] Running a command with a `then` chain while BeadsPlugin is active
      completes the full chain without beads context being injected mid-chain
- [ ] The beads `bd sync` on `session.idle` still runs during then-chains
      (it's safe — no visible output)
- [ ] After a then-chain completes, beads context injection resumes normally
- [ ] If compaction occurs during a then-chain, beads re-injection is deferred
      until the chain completes, then fires
- [ ] A user-interrupted chain allows beads injection to resume immediately
- [ ] The test-then-command → test-then-prompt chain (the exact scenario from
      the conflict export) completes without beads context interleaving
- [ ] The `PluginCoordinator` works when only ThenChainingPlugin is loaded
- [ ] The `PluginCoordinator` works when only BeadsPlugin is loaded
- [ ] Multiple compactions during a single chain result in only one
      beads re-injection

### CLI Setup

- [ ] The setup command copies all 14 files to the correct `.opencode/`
      subdirectories
- [ ] Missing directories are created automatically
- [ ] Existing files are overwritten without prompting
- [ ] `.workflow.yaml` is written with `specs.directory: docs/specs`
- [ ] Summary of actions and package version is printed to stdout
- [ ] `npm pack` produces a tarball containing the `opencode/` directory
      with all 14 files
- [ ] Running the CLI with no arguments prints usage and exits with code 1

### File Content

- [ ] No shipped file contains the string `bd-` as a command/agent/skill
      prefix (only as CLI commands like `bd create`)
- [ ] No shipped file references `adr-workflow`, `bd-v2-`, or any V2 content
- [ ] All `agent:` frontmatter values reference `omg-` prefixed agents
- [ ] All `/` command references use `omg-` prefix
- [ ] All skill name references use `omg-` prefix
- [ ] All `{file:}` prompt includes reference `omg-workflow.md`
- [ ] Skill SKILL.md frontmatter `name:` fields match their directory names
- [ ] `omg-spec-track.md` has `agent: omg-spec-writer` in frontmatter
- [ ] `omg-work.md` references `agent: omg-build`

### New Agent

- [ ] `omg-build.md` exists in `opencode/agents/`
- [ ] `omg-build.md` includes `{file:../prompts/omg-workflow.md}`
- [ ] `omg-build.md` has full tool access and bash permissions

### Removals

- [ ] `HelloWorldPlugin` is no longer exported
- [ ] `src/plugins/hello-world.ts` does not exist

### Local Development

- [ ] `.opencode/plugins/beads.ts` imports from `../../dist/index.js`
- [ ] The local beads plugin still works after `bun run build`
- [ ] Local `.opencode/` files still use `bd-` prefix (unchanged)

### Build & Quality

- [ ] `bun run build` succeeds
- [ ] `bun run lint` passes
- [ ] `bun test` passes
- [ ] README documents BeadsPlugin prerequisites and setup command
- [ ] `dist/cli/setup.js` starts with `#!/usr/bin/env node`

---

## Edge Cases

### Plugin coordination

- **Chain starts, compaction happens, chain ends**: The queued beads
  re-injection must fire after the chain completes. If another compaction
  happens before the queued injection fires, only one injection should occur
  (not two).

- **Multiple concurrent sessions**: The coordination state must be per-session.
  A then-chain in session A must not block beads injection in session B.

- **Plugin load order**: The coordination mechanism must work regardless of
  which plugin initializes first. Both plugins import from a shared module,
  so load order is irrelevant.

- **Only one plugin active**: If a user only uses `ThenChainingPlugin` without
  `BeadsPlugin` (or vice versa), each plugin must work independently without
  errors. The shared coordination module must handle the case where only one
  side is present.

### Setup command

- **Existing `.opencode/` with other files**: The setup command only writes
  specific files. It must not delete or modify any files it doesn't own.

---

## Deferred to Follow-Up Spec

The following items are explicitly deferred to a separate "hardening" spec
to be created after this integration is working:

- **Dependency detection**: Lazy PATH checks for `bd` and `yq`, warning
  on missing dependencies, disabling plugin when dependencies are absent
- **Non-interactive setup**: `--yes`/`--no-workflow` flags, TTY detection,
  CI-friendly defaults
- **Version mismatch detection**: Checking that plugin runtime version
  matches the version of setup files installed in `.opencode/`
- **Graceful degradation**: `bd` disappearing mid-session, transient errors,
  retry logic
- **Per-session vs. global disabling**: Whether dependency failures disable
  the plugin globally or per-session

---

## Out of Scope

- V2 commands, agents, and skills (ADR-aware variants)
- ADR workflow (commands, agents, `adr-workflow` skill)
- Plugin configuration options (future: selective feature activation)
- Programmatic command/agent registration via the OpenCode `config` hook
  (may be explored in the future if OpenCode supports it)
- Conditional/parallel then-chaining
- Automatic `bd init` or beads project setup

---

## Open Questions

None — all questions resolved during spec refinement.
