# Then Chaining

Deterministic follow-up execution after OpenCode commands complete.

## Problem

OpenCode commands are one-shot: you run `/do-something`, the model responds, and the conversation continues with whatever the user or model decides to do next. There's no way to declaratively say "after this command finishes, always do X." This makes it impossible to build reliable multi-step workflows from composable command files.

## Solution

Introduce a `then` key in command frontmatter. When a command with a `then` value completes, the plugin automatically submits the `then` value as the next message in the conversation — before the user or model can interject. This creates deterministic, declarative command chaining.

## Frontmatter Syntax

### Single prompt

```yaml
---
description: Review the current PR
then: "Summarize your findings in 3 bullet points"
---
Review the open PR for correctness, style, and test coverage.
```

After the model finishes the review, the plugin injects `"Summarize your findings in 3 bullet points"` as the next user message. The model then responds to that prompt in the same session.

### Single command

```yaml
---
description: Analyze the codebase
then: "/generate-report"
---
Analyze the project structure and identify areas for improvement.
```

After analysis completes, the plugin fires `/generate-report` as if the user had typed it.

### Ordered sequence

```yaml
---
description: Full release workflow
then:
  - "Check for any uncommitted changes and report them"
  - "/run-tests"
  - "/bump-version"
  - "Summarize everything that happened above"
---
Prepare the project for a new release.
```

Each entry executes in order. The next entry fires only after the previous one has fully completed (the model has finished responding or the chained command has finished its own execution, including any nested `then` chains).

## Behavior

### Prompt entries (plain text)

Any `then` entry that does **not** start with `/` is treated as a prompt. It is submitted to the conversation as a user message. The model sees it and responds to it normally.

### Command entries (slash-prefixed)

Any `then` entry that starts with `/` is treated as a command invocation. It is executed as if the user typed that command. The command may itself have a `then` chain, which will execute before the parent chain continues to its next entry.

### Execution model

1. User invokes a command (e.g., `/release-workflow`).
2. The model processes the command's prompt and produces a response.
3. When the response is complete, the plugin checks whether the originating command had a `then` value.
4. If yes, the plugin processes the first entry:
   - **Prompt**: inject as a user message; wait for model to finish responding.
   - **Command**: execute the command; wait for full completion (including any nested `then` chains).
5. Move to the next entry. Repeat until the chain is exhausted.
6. Control returns to the normal conversation flow.

### Nested chains

Commands invoked via `then` may themselves define `then` chains. These nested chains execute depth-first: the inner chain completes fully before the outer chain advances to its next entry. This is a stack-based execution model.

**Example:**

`/step-one` has `then: /step-two`.
`/step-two` has `then: "validate the output"`.

Execution order:
1. `/step-one` runs
2. `/step-two` runs (from step-one's `then`)
3. `"validate the output"` runs (from step-two's `then`)
4. step-one's chain is now exhausted; done.

### Recursion guard

To prevent infinite loops (e.g., `/a` chains to `/b` which chains back to `/a`), the plugin enforces a maximum chain depth. When the limit is reached, the chain halts and the plugin logs a warning. The default depth limit is **10**. This is configurable via plugin options.

## Implementation Strategy

### Reading frontmatter

The plugin needs to read command markdown files to extract `then` values from YAML frontmatter. Commands live in `.opencode/commands/` as markdown files. The plugin reads these files at initialization and whenever commands are invoked, parsing the YAML frontmatter to extract the `then` key.

### Detecting command completion

The plugin uses the `command.execute.before` hook to know when a command is being invoked and to associate the command's `then` chain with the current session/message context. It then uses `chat.message` or the experimental message transform hooks to detect when the model has finished responding to that command, which is the signal to inject the next `then` entry.

### Injecting follow-up messages

When a `then` entry needs to fire, the plugin uses the client SDK to submit a new message to the active session. For prompts, this is a user message. For commands, the plugin triggers the command through the appropriate client API method.

### State tracking

The plugin maintains an in-memory map of active chains keyed by session ID. Each entry tracks:

- The full `then` sequence for the originating command
- The current index into that sequence
- The current chain depth (for recursion guarding)

When a chain completes or is interrupted, the entry is cleaned up.

### Synthetic message handling

When OpenCode completes a subtask-style command, it may inject its own synthetic follow-up messages (e.g., asking the model to summarize). The plugin should intercept and remove these synthetic messages when a `then` chain is active, so that the `then` entry takes precedence rather than competing with OpenCode's default behavior. The `experimental.chat.messages.transform` hook is the mechanism for this.

## Configuration

The plugin accepts the following options relevant to `then` chaining:

```typescript
interface ThenChainingConfig {
  /** Maximum depth for nested then chains. Default: 10 */
  maxDepth?: number

  /**
   * What to do when a command has no `then` key and OpenCode
   * injects a synthetic follow-up message.
   *
   * - "keep": leave OpenCode's default behavior alone
   * - "remove": strip the synthetic message silently
   * - "replace": replace with a custom prompt (see `defaultFollowUp`)
   *
   * Default: "keep"
   */
  syntheticMessageBehavior?: "keep" | "remove" | "replace"

  /**
   * Custom prompt to use when syntheticMessageBehavior is "replace".
   * Only meaningful when syntheticMessageBehavior is "replace".
   */
  defaultFollowUp?: string
}
```

## Edge Cases

### Empty `then` value

A `then` key with an empty string or empty array is treated as no-op. No chaining occurs.

### Invalid command references

If a `then` entry references a command that doesn't exist (e.g., `/nonexistent`), the plugin logs a warning and skips that entry, advancing to the next one in the sequence. The chain does not abort entirely.

### Session ends mid-chain

If the session is terminated while a chain is in progress, the chain is abandoned. No cleanup is required beyond dropping the in-memory state.

### Concurrent commands in the same session

If a user manually invokes a new command while a `then` chain is still executing, the chain is interrupted. The user's explicit action takes priority. The interrupted chain is discarded.

### Argument forwarding

`then` command entries can include arguments, e.g., `then: "/deploy staging"`. The arguments are passed through as if the user had typed them. The `$ARGUMENTS` placeholder in the target command's template will receive `"staging"`.

## Non-Goals (for now)

- **Conditional chaining**: branching based on command output (e.g., "if tests pass, deploy; otherwise, fix"). This is a future consideration.
- **Parallel execution**: running multiple `then` entries concurrently. All entries execute sequentially.
- **Result capture / interpolation**: referencing the output of a previous chain step in a later step (e.g., `$RESULT[step-one]`). This is a future consideration.
- **Dynamic `then` values**: computing the `then` value at runtime based on command output. The `then` value is always read statically from frontmatter.
