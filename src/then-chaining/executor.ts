import type { PluginInput } from "@opencode-ai/plugin"
import type { ChainStateManager } from "./state.js"

/** Agent/model context needed when dispatching prompts and commands */
export interface SessionContext {
  agent?: string
  model?: {
    providerID: string
    modelID: string
  }
}

export class ChainExecutor {
  /**
   * Set of session IDs where the executor is currently dispatching
   * a command. The command.execute.before hook checks this to
   * distinguish chain-invoked commands from user-invoked commands.
   *
   * - If sessionID is in this set when command.execute.before fires,
   *   the command was dispatched by the chain -> push nested frame.
   * - If sessionID is NOT in this set, the command was user-initiated
   *   -> interrupt the active chain first.
   *
   * The executor adds the sessionID before calling client.session.command()
   * and removes it in a finally block after the call completes.
   */
  readonly pendingDispatches: Set<string> = new Set()

  /** Stored session context (agent/model) per session for dispatching */
  private sessionContexts: Map<string, SessionContext> = new Map()

  /**
   * Pending prompt text per session. Set by processNext() for prompt
   * entries, consumed by the transform hook which replaces OpenCode's
   * generic synthetic message with this text. This two-phase approach
   * ensures the LLM actually sees and responds to the prompt.
   */
  readonly pendingPrompts: Map<string, string> = new Map()

  constructor(
    private client: PluginInput["client"],
    private stateManager: ChainStateManager,
    private logger: (
      level: "info" | "warn" | "error",
      message: string,
    ) => Promise<void>,
  ) {}

  /**
   * Store the agent/model context for a session so dispatches can
   * forward it to the OpenCode server.
   */
  setSessionContext(sessionID: string, context: SessionContext): void {
    this.sessionContexts.set(sessionID, context)
  }

  /**
   * Clear stored context for a session (called when chain completes).
   */
  clearSessionContext(sessionID: string): void {
    this.sessionContexts.delete(sessionID)
  }

  /**
   * Consume and return the pending prompt for a session (if any).
   * Called by the transform hook to get the text to inject.
   */
  consumePendingPrompt(sessionID: string): string | undefined {
    const prompt = this.pendingPrompts.get(sessionID)
    if (prompt !== undefined) {
      this.pendingPrompts.delete(sessionID)
    }
    return prompt
  }

  /**
   * Process the next entry in the active chain for a session.
   * Called from session.idle when the LLM finishes responding.
   *
   * For prompt entries: stores the prompt text as pending and calls
   * promptAsync to trigger a new LLM turn. The transform hook will
   * replace the synthetic message with the pending prompt text.
   *
   * For command entries: calls session.command directly.
   *
   * Returns true if an entry was dispatched, false if the chain is complete.
   */
  async processNext(sessionID: string): Promise<boolean> {
    const context = this.sessionContexts.get(sessionID)

    // Iterative loop handles both frame unwinding and error recovery
    // without recursive calls to processNext.
    while (true) {
      const entry = this.stateManager.advance(sessionID)

      if (entry === undefined) {
        // Current frame is exhausted -- pop it and try the parent
        this.stateManager.popChain(sessionID)

        if (this.stateManager.hasActiveChain(sessionID)) {
          continue // try the parent frame
        }

        // Chain is fully complete — clean up context
        this.clearSessionContext(sessionID)
        return false
      }

      if (entry.type === "prompt") {
        const preview =
          entry.value.length > 50
            ? entry.value.substring(0, 50) + "..."
            : entry.value
        try {
          await this.logger(
            "info",
            `Then chain: injecting prompt: "${preview}"`,
          )

          // Phase 1: Store the prompt so the transform hook can inject
          // it into the LLM's message array by replacing OpenCode's
          // generic synthetic message.
          this.pendingPrompts.set(sessionID, entry.value)

          // Phase 2: Fire promptAsync to trigger a new LLM turn.
          // The transform hook will replace the synthetic message with
          // our pending prompt text before the LLM sees it.
          await this.client.session.promptAsync({
            body: {
              agent: context?.agent,
              model: context?.model,
              parts: [
                {
                  type: "text",
                  text: entry.value,
                },
              ],
            },
            path: {
              id: sessionID,
            },
          })
          return true
        } catch (err) {
          this.pendingPrompts.delete(sessionID)
          await this.logger(
            "error",
            `Then chain: failed to inject prompt: ${err instanceof Error ? err.message : String(err)}`,
          )
          // Skip failed entry and try the next one
          continue
        }
      }

      // entry.type === "command"
      // Split into command name and arguments.
      // Strip the leading "/" — the frontmatter uses "/cmd" syntax to
      // distinguish commands from prompts, but the session.command API
      // and command.execute.before hook receive the name without it.
      const raw = entry.value.startsWith("/")
        ? entry.value.slice(1)
        : entry.value
      const spaceIndex = raw.indexOf(" ")
      let commandName: string
      let args: string
      if (spaceIndex === -1) {
        commandName = raw
        args = ""
      } else {
        commandName = raw.substring(0, spaceIndex)
        args = raw.substring(spaceIndex + 1)
      }

      this.pendingDispatches.add(sessionID)
      try {
        await this.logger(
          "info",
          `Then chain: executing command: ${commandName} (args: "${args}")`,
        )
        await this.client.session.command({
          body: {
            command: commandName,
            agent: context?.agent,
            arguments: args,
          },
          path: {
            id: sessionID,
          },
        })
        return true
      } catch (err) {
        await this.logger(
          "error",
          `Then chain: failed to execute command ${commandName}: ${err instanceof Error ? err.message : String(err)}`,
        )
        // Skip failed entry and try the next one
        continue
      } finally {
        this.pendingDispatches.delete(sessionID)
      }
    }
  }
}
