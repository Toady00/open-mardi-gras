/**
 * BeadsPlugin — integrates the beads issue tracker with OpenCode.
 *
 * Features:
 * - Context injection via `bd prime` appended to the system prompt
 * - Uses experimental.chat.system.transform to inject on every LLM call
 * - Automatic refresh after compaction via `session.compacted` event
 * - Automatic `bd sync` on session idle (idempotent, no context pollution)
 * - Recovery sync before prime on every refresh (catches hard exits)
 *
 * The system.transform approach eliminates race conditions with
 * ThenChainingPlugin because system prompt injection never creates
 * extra user messages or LLM turns.
 */

import type { Plugin, PluginInput } from "@opencode-ai/plugin"
import { createPluginLogger } from "../logging.js"

type Shell = PluginInput["$"]

/**
 * Run `bd sync` then `bd prime` and return the formatted beads context.
 * Returns null if bd is not installed, not initialized, or prime is empty.
 */
async function fetchBeadsContext(
  $: Shell,
  logger: (level: "info" | "warn" | "error", message: string) => Promise<void>,
): Promise<string | null> {
  try {
    // Flush any unsaved state before reading — recovers from hard exits
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    await $`bd sync`.quiet()

    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-assignment
    const primeOutput: string = await $`bd prime`.text()
    if (!primeOutput?.trim()) return null

    return `<beads-context>
${primeOutput.trim()}
</beads-context>

<beads-guidance>
There is no native bd tool. Use the bash tool to run bd commands.
Always use --json flag for structured output when parsing results.
</beads-guidance>`
  } catch (err) {
    await logger(
      "warn",
      `BeadsPlugin: failed to fetch context: ${err instanceof Error ? err.message : String(err)}`,
    )
    return null
  }
}

export function BeadsPlugin(): Plugin {
  return async ({ client, $ }) => {
    /**
     * Cached beads context per session. Populated on first LLM call
     * (via system.transform) and refreshed after compaction.
     *
     * Key: sessionID, Value: formatted beads context string
     */
    const sessionContextCache = new Map<string, string>()

    /**
     * Sessions that need a context refresh on the next system.transform
     * call. Set by the compaction handler and consumed by the transform.
     */
    const pendingRefresh = new Set<string>()

    const logger = createPluginLogger(client)

    await logger("info", "BeadsPlugin initialized")

    return {
      // Append beads context to the system prompt on every LLM call.
      // This is purely additive — existing system prompt strings are
      // untouched. The beads context appears as system instructions,
      // not as a user message, so it cannot race with then-chains or
      // trigger extra LLM turns.
      "experimental.chat.system.transform": async (input, output) => {
        const sessionID = input.sessionID
        if (!sessionID) return

        // Check if a refresh is pending (post-compaction)
        if (pendingRefresh.has(sessionID)) {
          pendingRefresh.delete(sessionID)
          sessionContextCache.delete(sessionID)
        }

        // Fetch and cache beads context on first call per session
        if (!sessionContextCache.has(sessionID)) {
          const context = await fetchBeadsContext($, logger)
          if (context) {
            sessionContextCache.set(sessionID, context)
            await logger("info", "BeadsPlugin: cached beads context for session")
          } else {
            // Mark as empty so we don't retry every call
            sessionContextCache.set(sessionID, "")
          }
        }

        const cached = sessionContextCache.get(sessionID)
        if (cached) {
          output.system.push(cached)
        }
      },

      // Refresh beads context after compaction; auto-sync on idle
      event: async ({ event }) => {
        if (event.type === "session.compacted") {
          const sessionID = event.properties.sessionID
          // Flag this session for refresh on the next system.transform call.
          // The actual bd prime fetch happens lazily in the transform hook
          // so there's no race with other hooks or chain state.
          pendingRefresh.add(sessionID)
          await logger(
            "info",
            "BeadsPlugin: flagged session for context refresh after compaction",
          )
        }

        // Flush beads state after every agent turn.
        // bd sync is idempotent, cheap (ms), and a no-op when beads isn't
        // initialized. No context pollution — output goes to stderr only.
        if (event.type === "session.idle") {
          try {
            // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
            await $`bd sync`.quiet()
          } catch {
            // Silent skip — bd not installed or not initialized
          }
        }
      },
    }
  }
}
