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

```bash
npm install @toady00/open-mardi-gras
```

## Plugins

This package ships two plugins that can be used independently or together.

### ThenChainingPlugin

Deterministic follow-up execution after OpenCode commands complete. See the [Then Chaining](#then-chaining) section above for full documentation.

### BeadsPlugin

Integrates [beads](https://github.com/toady00/beads) issue tracking into your OpenCode sessions. The plugin appends `bd prime` output to the system prompt so beads context is available on every LLM call. Context is refreshed automatically after session compaction. The plugin also flushes pending beads state on session idle.

#### Prerequisites

BeadsPlugin requires two external tools on your `$PATH`:

- **`bd`** — the [beads](https://github.com/toady00/beads) CLI for issue tracking
- **`yq`** — YAML processor used by the workflow commands

These are only required if you use BeadsPlugin. ThenChainingPlugin has no external dependencies.

#### Setup

Run the setup command to install workflow files (commands, agents, skills, prompts) into your project:

```bash
npx @toady00/open-mardi-gras setup
```

This copies files into your `.opencode/` directory and writes a `.workflow.yaml` config file. Run it again after upgrading to pick up new versions of the workflow files.

### Plugin Installation

#### From npm (recommended)

Add the package name to the `plugin` array in your `opencode.json` config file. This can be either project-level or global:

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
  "plugin": ["@toady00/open-mardi-gras@0.3.0"]
}
```

- `@toady00/open-mardi-gras@0.3.0` - exact pin, best cache behavior
- `@toady00/open-mardi-gras` - always track latest
- Semver ranges like `@toady00/open-mardi-gras@^0.3.0` work, but may reinstall on every startup due to OpenCode's current cache behavior

#### Upgrading

- If you use `@toady00/open-mardi-gras` (no pin), OpenCode checks npm for updates at startup
- If you pin an exact version, update the version string in `opencode.json`
- If OpenCode appears stuck on an old version, remove `~/.cache/opencode/node_modules/@toady00/open-mardi-gras`
- After upgrading, rerun `npx @toady00/open-mardi-gras setup` to refresh workflow files in `.opencode/`

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

Both plugins can be used together safely. Beads context is injected via the system prompt, so it never interferes with then-chain execution.

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
