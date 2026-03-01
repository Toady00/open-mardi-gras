# Integration Testing

Agent-driven verification of plugin behavior against a live OpenCode server.

## Overview

The `then` chaining feature involves complex interactions between the plugin,
the OpenCode runtime, and the LLM. Unit tests verify parsing and state
management in isolation, but they can't prove the plugin actually works when
wired into a real OpenCode session. We need a way for an agent to stand up a
real OpenCode server with the plugin loaded, invoke commands that exercise
`then` chaining, inspect the resulting message history via the SDK, and report
whether the plugin behaved correctly.

This is not a traditional test suite. It is a set of verification scripts and
fixture files that an agent executes via bash and `bun run`. The agent manages
the server lifecycle, runs the scripts, interprets the output, and reports
pass/fail.

## Requirements

1. A temp directory is created that simulates an end-user project with the
   plugin installed as a local plugin and demo commands that use `then`.
2. An OpenCode server is started in that temp directory on a known port.
3. Verification scripts use `@opencode-ai/sdk` to create a session, invoke
   commands, wait for the session to go idle, fetch the message history, and
   check structural properties of that history.
4. Each verification script exits 0 on success, non-zero on failure, with
   human-readable output describing what was checked and whether it passed.
5. The server is shut down and the temp directory is cleaned up after
   verification completes (or on failure).

## Architecture

```
┌─────────────────────────┐
│  Agent (bash + bun run) │
│                         │
│  1. Create temp dir     │
│  2. Write fixtures      │
│  3. Start server        │
│  4. Run verify scripts ─┼──── HTTP / SSE ────┐
│  5. Kill server         │                    │
│  6. Report results      │                    ▼
└─────────────────────────┘       ┌─────────────────────┐
                                  │  opencode serve      │
                                  │  --port 4200         │
                                  │                      │
                                  │  .opencode/plugins/  │
                                  │    then-chaining.ts   │
                                  │                      │
                                  │  .opencode/commands/  │
                                  │    (test fixtures)    │
                                  └─────────────────────┘
```

The agent runs everything from bash. The verification scripts are standalone
TypeScript files executed via `bun run <script>`. They are not `bun test` files
— they are plain scripts that use the SDK, print results, and exit with an
appropriate code.

## Temp Directory Layout

The agent creates a temp directory that looks like a real end-user project
with the plugin installed locally.

```
/tmp/omg-verify-XXXXX/
├── opencode.json              # configures model + plugin
├── .opencode/
│   ├── plugins/
│   │   └── then-chaining.ts   # local plugin file importing from build
│   └── commands/
│       ├── echo-back.md       # simple command, no chaining
│       ├── then-prompt.md     # then: "some prompt"
│       ├── then-command.md    # then: "/echo-back farewell"
│       ├── then-sequence.md   # then: [array of entries]
│       └── then-nested.md     # chains to a command that itself has a then
└── package.json               # empty, just so opencode treats this as a project
```

### `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-haiku-4-5",
  "server": {
    "port": 4200
  }
}
```

Uses `claude-haiku-4-5` — cheap, fast, and capable enough to follow simple
instructions like "repeat this back" or "say hello." The `ANTHROPIC_API_KEY`
environment variable must be set.

### `.opencode/plugins/then-chaining.ts`

This is a local plugin file that imports the built plugin from the repo's
`dist/` directory using an absolute path:

```typescript
import { ThenChainingPlugin } from "/absolute/path/to/open-mardis-gras/dist/index.js"

export default ThenChainingPlugin({
  maxDepth: 3,
  syntheticMessageBehavior: "remove",
})
```

`maxDepth: 3` keeps the recursion test fast. `syntheticMessageBehavior: "remove"`
prevents OpenCode's synthetic follow-ups from interfering with chain assertions.

### Fixture Commands

#### `echo-back.md` — No chaining baseline

```markdown
---
description: Echoes the arguments back
---
Repeat the following text back exactly, with no additional commentary: $ARGUMENTS
```

#### `then-prompt.md` — Single prompt follow-up

```markdown
---
description: Says hello then follows up
then: "Now say goodbye"
---
Say hello to the user.
```

#### `then-command.md` — Single command follow-up

```markdown
---
description: Says hello then runs echo-back
then: "/echo-back farewell"
---
Say hello to the user.
```

#### `then-sequence.md` — Ordered array of follow-ups

```markdown
---
description: Multi-step sequence
then:
  - "Summarize what you just said in one sentence"
  - "/echo-back done"
---
Tell me three fun facts about octopuses.
```

#### `then-nested.md` — Nested chain (command whose target also has a `then`)

```markdown
---
description: Outer command that chains to then-prompt
then: "/then-prompt"
---
Say "starting outer command" to the user.
```

This triggers: outer command responds → `/then-prompt` fires → `then-prompt`
responds with hello → "Now say goodbye" is injected → model responds to
goodbye. The inner chain (`then-prompt`'s `then`) completes before the outer
chain considers its next entry (there isn't one here, so it just finishes).

## Verification Scripts

Each script is a standalone TypeScript file in `test/integration/`. The agent
runs them via `bun run test/integration/<script>.ts`. Each script:

1. Connects to the OpenCode server at `http://localhost:4200` using the SDK.
2. Creates a fresh session.
3. Sends a command via `client.session.chat()`.
4. Subscribes to the event stream via `client.event.list()` and waits for a
   `session.idle` event matching the session ID (with a timeout).
5. Fetches the full message history via `client.session.messages()`.
6. Checks structural properties of the message list (message count, role
   sequence, presence of expected content).
7. Prints pass/fail for each check and exits 0 if all pass, 1 if any fail.

### Idle Detection

The SDK's SSE event stream emits `session.idle` events when the model finishes
responding and no further work is pending. The verification scripts subscribe
to the event stream and wait for a `session.idle` event whose `sessionID`
matches the test session. Timeout after 60 seconds.

```typescript
import Opencode from "@opencode-ai/sdk"

const client = new Opencode({ baseURL: "http://localhost:4200" })

// Wait for session to go idle
async function waitForIdle(sessionId: string, timeoutMs = 60000): Promise<void> {
  const stream = await client.event.list()
  const deadline = Date.now() + timeoutMs

  for await (const event of stream) {
    if (Date.now() > deadline) {
      stream.controller.abort()
      throw new Error(`Timed out waiting for session ${sessionId} to go idle`)
    }
    if (event.type === "session.idle" && event.properties.sessionID === sessionId) {
      stream.controller.abort()
      return
    }
  }
}
```

### What to Assert

Assertions are structural, not textual. LLM output varies, so we don't assert
on exact wording. Instead we check:

- **Message count**: The session has the expected number of messages (within a
  tolerance — the model might produce slightly different turn counts).
- **Role sequence**: Messages alternate correctly between user and assistant
  roles, with injected `then` prompts appearing as user messages.
- **Content presence**: Key strings appear somewhere in the message history
  (e.g., "farewell" appears after `/echo-back farewell` fires, "goodbye"
  appears after "Now say goodbye" is injected).
- **Ordering**: When checking a sequence, content A appears before content B
  in the message list.
- **Absence**: No synthetic follow-up messages remain (since we configure
  `syntheticMessageBehavior: "remove"`).

### Script List

| Script | What it verifies |
|--------|-----------------|
| `verify-no-then.ts` | `/echo-back hello` produces a response with no follow-up. Message count is exactly 2 (user command + assistant response). |
| `verify-then-prompt.ts` | `/then-prompt` produces: assistant hello → user "Now say goodbye" → assistant goodbye response. At least 4 messages. The string "goodbye" appears in a message after "hello". |
| `verify-then-command.ts` | `/then-command` produces: assistant hello → `/echo-back farewell` fires → assistant echoes "farewell". The string "farewell" appears in the message history. |
| `verify-then-sequence.ts` | `/then-sequence` produces: fun facts → "Summarize..." injected → summary → `/echo-back done` fires → "done" echoed. Messages appear in this order. |
| `verify-then-nested.ts` | `/then-nested` produces: outer response → `/then-prompt` fires → hello → "Now say goodbye" injected → goodbye response. The inner chain completes fully. |

## Server Lifecycle

The agent manages the server from bash:

### Starting

```bash
# Build the plugin first
bun run build

# Create temp directory and write fixtures (agent does this)
TMPDIR=$(mktemp -d /tmp/omg-verify-XXXXX)
# ... write opencode.json, plugin file, command fixtures ...

# Start server in background
opencode serve --port 4200 &
SERVER_PID=$!

# Wait for server to be ready (poll until responding)
for i in $(seq 1 30); do
  curl -s http://localhost:4200/ > /dev/null 2>&1 && break
  sleep 1
done
```

The agent runs this from the temp directory as the working directory so
OpenCode picks up the `opencode.json` and `.opencode/` fixtures there.

### Stopping

```bash
kill $SERVER_PID 2>/dev/null
rm -rf "$TMPDIR"
```

The agent must kill the server even if verification fails. Use a trap or
ensure cleanup happens in a finally-style block.

### Port Selection

Use port `4200`. If the port is occupied, the agent should detect the failure
when `opencode serve` exits early and report it clearly rather than hanging.

## Acceptance Criteria

1. **Fixture creation**: Running the setup produces a temp directory with a
   valid `opencode.json`, a local plugin file that imports from the repo's
   built `dist/`, and all five command fixtures.

2. **Server starts**: `opencode serve --port 4200` starts successfully in the
   temp directory and loads the `then-chaining` plugin (confirmed by the plugin's
   "ThenChainingPlugin initialized" log message).

3. **verify-no-then.ts passes**: The echo-back command produces exactly 2
   messages with no follow-up injection.

4. **verify-then-prompt.ts passes**: The session history contains a user
   message with "Now say goodbye" that was not typed by the test — it was
   injected by the `then` chain.

5. **verify-then-command.ts passes**: The session history shows that
   `/echo-back farewell` was invoked and the word "farewell" appears in an
   assistant response.

6. **verify-then-sequence.ts passes**: Messages appear in the declared order:
   fun facts first, summary second, "done" echo last.

7. **verify-then-nested.ts passes**: The inner chain (`then-prompt`'s "Now say
   goodbye") completes before the outer chain finishes.

8. **Cleanup**: The server process is killed and the temp directory is removed
   after verification, regardless of pass/fail.

## Edge Cases

| Scenario | Expected behavior |
|----------|------------------|
| Empty `then: ""` | No follow-up; behaves like no `then` key. Covered by frontmatter parser (returns empty array for empty string). |
| Empty array `then: []` | No follow-up; behaves like no `then` key. |
| Whitespace-only `then: "   "` | Treated as a prompt (the frontmatter parser does not trim). Not tested in v1 — defer to unit tests which already cover this. |
| Invalid command ref `then: "/nonexistent"` | Error logged, entry skipped, chain continues to next entry. Not tested in v1 — the error path is covered by unit tests. |
| Recursion limit exceeded | Nested push refused (`pushChain` returns false), parent chain continues. Not tested in v1 — covered by unit tests. `maxDepth: 3` in the fixture config keeps this safe. |
| `replace` without `defaultFollowUp` | No-op; synthetic message stays. Not tested in v1 — the fixture uses `"remove"` mode. |
| Server fails to start | Agent detects that `opencode serve` exited or the health poll times out, reports the error, and cleans up. |
| LLM returns an error mid-chain | The executor catches the error, logs it, skips the failed entry, and continues the chain. This is inherently hard to trigger in integration — rely on unit tests. |

## Environment Requirements

- **OpenCode CLI** installed and on `$PATH` (`opencode serve` must work).
- **Bun** installed (for `bun run build` and `bun run <script>`).
- **`ANTHROPIC_API_KEY`** set in the environment (the server talks to a real
  Anthropic model).
- **`@opencode-ai/sdk`** added as a `devDependency` in this project's
  `package.json` so the verification scripts can import it.
- **Port 4200** available on localhost.

## Cost and Speed

Integration verification hits a real LLM. To manage cost:

- Commands use short, simple prompts ("say hello", "repeat this back").
- `claude-haiku-4-5` is the cheapest Anthropic model that can follow these
  instructions reliably.
- A full verification run (5 scripts) should complete in under 2 minutes and
  cost less than $0.05.
- Verification is run on-demand by an agent, not on every commit or in CI.

## Non-Goals (for now)

- **CI integration**: This runs when an agent decides to verify, not
  automatically. CI support is a future enhancement.
- **Synthetic message behavior testing**: The v1 fixtures use `"remove"` mode.
  Testing `"keep"` and `"replace"` modes requires separate fixture configs and
  is deferred.
- **Snapshot testing**: Comparing full message transcripts is too brittle with
  LLM output variance. Stick to structural assertions.
- **Performance benchmarks**: Measuring latency or token usage is out of scope.
- **Multi-session tests**: Start with single-session-per-script verification.
- **Mock mode**: Replacing the LLM with deterministic stubs for speed. Start
  with real LLM calls; add mock mode later if verification becomes too slow
  or expensive.

## Open Questions

None. All questions have been resolved.
