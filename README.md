# Open Mardi Gras

An [opencode](https://opencode.ai) plugin bringing together powerful workflow features for personal productivity.

## Philosophy

This plugin combines ideas from multiple sources to create a cohesive set of tools for managing AI-assisted workflows. It's built for personal use, with an eye toward broader utility.

## Features

### Then Chaining

Deterministic follow-up execution after OpenCode commands complete. Commands are normally one-shot: you run a slash command, the model responds, and the conversation continues freely. Then chaining lets you declaratively specify what happens next, enabling reliable multi-step workflows from composable command files.

#### Quick Start

Add a `then` key to any command's YAML frontmatter:

```yaml
---
description: Review the current PR
then: "Summarize your findings in 3 bullet points"
---
Review the open PR for correctness, style, and test coverage.
```

After the model finishes the review, the plugin automatically injects the summary prompt as the next message. The model then responds to it in the same session.

#### Frontmatter Syntax

**Single prompt** -- a plain text follow-up message:

```yaml
then: "Summarize your findings in 3 bullet points"
```

**Single command** -- invoke another slash command:

```yaml
then: "/generate-report"
```

**Ordered sequence** -- execute multiple steps in order:

```yaml
then:
  - "Check for any uncommitted changes and report them"
  - "/run-tests"
  - "/bump-version"
  - "Summarize everything that happened above"
```

Each entry fires only after the previous one has fully completed.

#### Behavior

- **Prompts** (entries without a leading `/`) are injected as user messages. The model sees and responds to them normally.
- **Commands** (entries starting with `/`) are executed as if the user had typed them. Arguments are supported: `then: "/deploy staging"` passes `"staging"` to the `/deploy` command.
- **Nested chains**: commands invoked via `then` can themselves have `then` chains. These execute depth-first -- the inner chain completes fully before the outer chain advances.
- **User interruption**: if you manually invoke a command while a chain is running, the chain is interrupted. Your explicit action always takes priority.

#### Configuration

ThenChainingPlugin accepts optional configuration when used as a local plugin file:

```typescript
// .opencode/plugins/then-chaining.ts
import type { Plugin } from "@opencode-ai/plugin"
import { ThenChainingPlugin } from "@toady00/open-mardi-gras/api"

export const ThenChaining: Plugin = ThenChainingPlugin({
  // Maximum depth for nested then chains (default: 10)
  maxDepth: 10,

  // How to handle OpenCode's synthetic follow-up messages
  // when no then chain is active.
  // "keep" (default) - leave them alone
  // "remove" - strip them silently
  // "replace" - substitute with a custom prompt
  syntheticMessageBehavior: "keep",

  // Custom prompt used when syntheticMessageBehavior is "replace"
  defaultFollowUp: "What should we do next?",
})
```

When installed via npm in `opencode.json`, the plugin uses default settings.

#### Edge Cases

- **Empty `then` values**: an empty string or empty array is treated as a no-op. No chaining occurs.
- **Invalid command references**: if a `then` entry references a command that doesn't exist, it is skipped with a warning. The chain continues with the next entry.
- **Session termination**: if the session ends mid-chain, the chain is abandoned.
- **Recursion guard**: nested chains enforce a maximum depth (default 10). When the limit is reached, the chain halts with a warning.

#### Non-Goals

Conditional chaining, parallel execution, result interpolation between steps, and dynamic `then` values are not currently supported.

## Installation

No manual `npm install` is required. Run the setup command in the repository you want to onboard:

```bash
npx @toady00/open-mardi-gras setup
```

Setup adds the package to the `plugin` array in your OpenCode configuration. OpenCode then installs the plugin automatically at startup.

## Plugins

This package ships two plugins that can be used independently or together.

### ThenChainingPlugin

Deterministic follow-up execution after OpenCode commands complete. See the [Then Chaining](#then-chaining) section above for full documentation.

### BeadsPlugin

Integrates [beads](https://github.com/toady00/beads) workflow state with OpenCode without injecting blanket instructions into agent prompts. The plugin forwards `BEADS_*` environment variables to every OpenCode shell, flushes pending Beads state when sessions become idle, and keeps an `/omg-build <epic>` foreman running while `bd ready --parent <epic> --json` reports ready work.

Foreman ownership is persisted under `${XDG_STATE_HOME:-~/.local/state}/open-mardi-gras/beads/`, so the plugin remembers the epic after OpenCode restarts without automatically running the session in the background. When the user returns to that session and manually resumes it, subsequent idle events can continue nudging it until the ready queue drains. Each epic has one current owner: invoking `/omg-build` for that epic in a fresh session transfers ownership and attempts to abort the previous owner. Empty ready queues do not create another turn. If a legacy or custom `then` chain is attached to the command, it remains gated until the plugin observes a valid empty ready array; command failures and malformed output keep the chain gated.

#### Prerequisites

BeadsPlugin requires two external tools on your `$PATH`:

- **`bd`** — the [beads](https://github.com/toady00/beads) CLI for issue tracking
- **`yq`** — YAML processor used by the workflow commands

These are only required if you use BeadsPlugin. ThenChainingPlugin has no external dependencies.

#### Setup

Run the setup command to install the workflow agents, commands, and skills into your project:

```bash
npx @toady00/open-mardi-gras setup
```

This copies the packaged `opencode/agents`, `opencode/commands`, and `opencode/skills` directories into your `.opencode/` directory. It also creates or updates `.opencode/opencode.json` and adds `@toady00/open-mardi-gras` to the `plugin` array without duplicating an existing version-pinned entry. Run setup again after upgrading to pick up new versions of the workflow files.

After running setup, open opencode in your project and:

1. Restart opencode so it loads the installed plugin and instruments.
2. Run `/omg-onboard {solo|centralized|satellite}` and follow its instructions to wire and verify the workflow. It will direct you to `/omg-hindsight-setup` if the project's Hindsight memory or guidance still needs setup.

### Manual Plugin Configuration

The setup command configures the npm plugin automatically. To configure it manually instead, add the package name to the `plugin` array in your `opencode.json` config file. This can be either project-level or global:

- **Project**: `opencode.json` in your project root
- **Global**: `~/.config/opencode/opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@toady00/open-mardi-gras"]
}
```

OpenCode automatically installs npm plugins at startup.

You can also pin a specific version directly in the plugin entry:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@toady00/open-mardi-gras@1.2.0"]
}
```

- `@toady00/open-mardi-gras@1.2.0` - exact pin, best cache behavior
- `@toady00/open-mardi-gras` - always track latest
- Semver ranges like `@toady00/open-mardi-gras@^1.2.0` work, but may reinstall on every startup due to OpenCode's current cache behavior

#### Upgrading

- If you use `@toady00/open-mardi-gras` (no pin), OpenCode checks npm for updates at startup
- If you pin an exact version, update the version string in `opencode.json`
- If OpenCode appears stuck on an old version, remove `~/.cache/opencode/node_modules/@toady00/open-mardi-gras`
- After upgrading, rerun `npx @toady00/open-mardi-gras setup` to refresh workflow files in `.opencode/`
- Setup records what it installed in `.opencode/.omg-manifest.json` and removes instruments a later release retires. Commit that file — it is what lets setup tell its own files from yours
- A file you edited is never replaced or deleted; setup keeps it and reports it, loudly when a newer version was withheld. Rerun with `--force` to take the shipped versions and discard local changes
- The first run after upgrading to a release that records a manifest has nothing to compare against, so it replaces existing instrument files once. Reconcile anything you customized before that run

#### From local files

Alternatively, create wrapper files in your plugin directory:

- **Project**: `.opencode/plugins/`
- **Global**: `~/.config/opencode/plugins/`

```typescript
// .opencode/plugins/open-mardi-gras.ts
import type { Plugin } from "@opencode-ai/plugin"
import { ThenChainingPlugin, BeadsPlugin } from "@toady00/open-mardi-gras/api"

export const ThenChaining: Plugin = ThenChainingPlugin()
export const Beads: Plugin = BeadsPlugin()
```

The `/api` sub-path exports configurable factory functions. Use this approach when you need to pass configuration (e.g., `ThenChainingPlugin({ maxDepth: 5 })`).

Local plugins require the package to be listed as a dependency in `.opencode/package.json`:

```json
{
  "dependencies": {
    "@toady00/open-mardi-gras": "latest"
  }
}
```

#### Notes

Both plugins can be used together safely. BeadsPlugin gates a foreman's then-chain while the epic has ready work and releases it only after observing a valid empty ready queue.

## Development Setup

```bash
# Install dependencies
bun install

# Build the project
bun run build

# Run tests
bun test

# Run linter
bun run lint

# Watch mode (rebuild on changes)
bun run dev
```

## Contributing

Contributions are welcome. Please open an issue first to discuss what you'd like to change. Make sure to run `bun run lint` and `bun run build` before submitting a pull request.

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for release history.

## License

MIT
