import type { PluginInput } from "@opencode-ai/plugin"
import type { ChainStateManager } from "./state.js"

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

  constructor(
    private client: PluginInput["client"],
    private stateManager: ChainStateManager,
    private logger: (
      level: "info" | "warn" | "error",
      message: string,
    ) => Promise<void>,
  ) {}

  /**
   * Process the next entry in the active chain for a session.
   * Called when a command or prompt response completes.
   *
   * Returns true if an entry was dispatched, false if the chain is complete.
   */
  async processNext(sessionID: string): Promise<boolean> {
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

        // Chain is fully complete
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
          await this.client.session.prompt({
            body: {
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
          await this.logger(
            "error",
            `Then chain: failed to inject prompt: ${err instanceof Error ? err.message : String(err)}`,
          )
          // Skip failed entry and try the next one
          continue
        }
      }

      // entry.type === "command"
      // Split into command name and arguments
      const spaceIndex = entry.value.indexOf(" ")
      let commandName: string
      let args: string
      if (spaceIndex === -1) {
        commandName = entry.value
        args = ""
      } else {
        commandName = entry.value.substring(0, spaceIndex)
        args = entry.value.substring(spaceIndex + 1)
      }

      this.pendingDispatches.add(sessionID)
      try {
        await this.logger(
          "info",
          `Then chain: executing command: ${entry.value}`,
        )
        await this.client.session.command({
          body: {
            command: commandName,
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
