/**
 * Beads OpenCode Plugin
 *
 * Integrates the beads issue tracker with OpenCode for the bd- workflow system.
 *
 * Features:
 * - Context injection via `bd prime` on first user message per session
 * - Context re-injection after compaction via `session.compacted` event
 * - Automatic `bd sync` on session idle (idempotent, no context pollution)
 * - Recovery sync before prime on every injection (catches hard exits)
 *
 * Reference: joshuadavidthomas/opencode-beads (v0.5.2) for lifecycle patterns.
 * This plugin adopts its proven hook patterns but adds idle sync and
 * sync-before-prime for reliability.
 */

import type { Plugin, PluginInput } from "@opencode-ai/plugin"

type OpencodeClient = PluginInput["client"]

/**
 * Get the current model/agent context for a session by querying messages.
 *
 * Mirrors OpenCode's internal lastModel() logic to find the most recent
 * user message. Used during event handling when we don't have direct access
 * to the current user message's context.
 */
async function getSessionContext(
  client: OpencodeClient,
  sessionID: string,
): Promise<
  | { model?: { providerID: string; modelID: string }; agent?: string }
  | undefined
> {
  try {
    const response = await client.session.messages({
      path: { id: sessionID },
      query: { limit: 50 },
    })
    if (response.data) {
      for (const msg of response.data) {
        if (
          msg.info.role === "user" &&
          "model" in msg.info &&
          msg.info.model
        ) {
          return { model: msg.info.model, agent: msg.info.agent }
        }
      }
    }
  } catch {
    // On error, return undefined (let opencode use its default)
  }
  return undefined
}

/**
 * Inject beads context into a session.
 *
 * Runs `bd sync` (recovery from hard exits) then `bd prime` and injects
 * the output wrapped in <beads-context> tags. Silently skips if bd is not
 * installed or beads is not initialized in the current project.
 */
async function injectBeadsContext(
  client: OpencodeClient,
  $: PluginInput["$"],
  sessionID: string,
  context?: {
    model?: { providerID: string; modelID: string }
    agent?: string
  },
): Promise<void> {
  try {
    // Flush any unsaved state before reading — recovers from hard exits
    await $`bd sync`.quiet()

    const primeOutput = await $`bd prime`.text()
    if (!primeOutput?.trim()) return

    const beadsContext = `<beads-context>
${primeOutput.trim()}
</beads-context>

<beads-guidance>
There is no native bd tool. Use the bash tool to run bd commands.
Always use --json flag for structured output when parsing results.
</beads-guidance>`

    await client.session.prompt({
      path: { id: sessionID },
      body: {
        noReply: true,
        model: context?.model,
        agent: context?.agent,
        parts: [{ type: "text", text: beadsContext, synthetic: true }],
      },
    })
  } catch {
    // Silent skip if bd is not installed or not initialized
  }
}

export const BeadsPlugin: Plugin = async ({ client, $ }) => {
  const injectedSessions = new Set<string>()

  return {
    // Inject bd prime context on first user message per session
    "chat.message": async (_input, output) => {
      const sessionID = output.message.sessionID
      if (injectedSessions.has(sessionID)) return

      // Check for existing injection (handles plugin reload/reconnection)
      try {
        const existing = await client.session.messages({
          path: { id: sessionID },
        })
        if (existing.data) {
          const hasBeadsContext = existing.data.some((msg) => {
            const parts = (msg as any).parts || (msg.info as any).parts
            if (!parts) return false
            return parts.some(
              (part: any) =>
                part.type === "text" &&
                part.text?.includes("<beads-context>"),
            )
          })
          if (hasBeadsContext) {
            injectedSessions.add(sessionID)
            return
          }
        }
      } catch {
        // On error, proceed with injection
      }

      injectedSessions.add(sessionID)
      await injectBeadsContext(client, $, sessionID, {
        model: output.message.model,
        agent: output.message.agent,
      })
    },

    // Re-inject beads context after compaction; auto-sync on idle
    event: async ({ event }) => {
      if (event.type === "session.compacted") {
        const sessionID = event.properties.sessionID
        const context = await getSessionContext(client, sessionID)
        await injectBeadsContext(client, $, sessionID, context)
      }

      // Flush beads state after every agent turn.
      // bd sync is idempotent, cheap (ms), and a no-op when beads isn't
      // initialized. No context pollution — output goes to stderr only.
      if (event.type === "session.idle") {
        try {
          await $`bd sync`.quiet()
        } catch {
          // Silent skip — bd not installed or not initialized
        }
      }
    },
  }
}
