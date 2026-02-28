import { readFile } from "node:fs/promises"
import { join } from "node:path"
import type { Plugin } from "@opencode-ai/plugin"
import { ChainExecutor } from "../then-chaining/executor.js"
import { parseThenChain } from "../then-chaining/frontmatter.js"
import { ChainStateManager } from "../then-chaining/state.js"
import {
  createSyntheticFilter,
  type SyntheticMessageBehavior,
} from "../then-chaining/synthetic-filter.js"

export interface ThenChainingConfig {
  /** Maximum depth for nested then chains. Default: 10 */
  maxDepth?: number

  /**
   * What to do when a command has no `then` key and OpenCode
   * injects a synthetic follow-up message.
   * - "keep": leave OpenCode's default behavior alone (default)
   * - "remove": strip the synthetic message silently
   * - "replace": replace with a custom prompt (see defaultFollowUp)
   */
  syntheticMessageBehavior?: SyntheticMessageBehavior

  /**
   * Custom prompt to use when syntheticMessageBehavior is "replace".
   */
  defaultFollowUp?: string
}

export const ThenChainingPlugin = (config?: ThenChainingConfig): Plugin => {
  return async ({ client, directory }) => {
    const maxDepth = config?.maxDepth ?? 10
    const syntheticBehavior = config?.syntheticMessageBehavior ?? "keep"

    // Create shared instances
    const stateManager = new ChainStateManager(maxDepth)
    const logger = async (
      level: "info" | "warn" | "error",
      message: string,
    ) => {
      try {
        await client.app.log({
          body: { service: "open-mardi-gras", level, message },
        })
      } catch {
        // Log failure should not prevent plugin from functioning
      }
    }
    const executor = new ChainExecutor(client, stateManager, logger)

    await logger("info", "ThenChainingPlugin initialized")

    // Commands live in `.opencode/commands/` as markdown files
    const commandsDir = join(directory, ".opencode", "commands")

    /**
     * Read a command's markdown file and parse its then-chain entries.
     * Returns an empty array if the file doesn't exist or has no then key.
     */
    async function readCommandThenChain(commandName: string) {
      // Strip leading `/` from command name to get filename
      const filename = commandName.startsWith("/")
        ? commandName.slice(1)
        : commandName
      const filePath = join(commandsDir, `${filename}.md`)

      try {
        const content = await readFile(filePath, "utf-8")
        return parseThenChain(content)
      } catch (err) {
        // ENOENT is expected for built-in commands with no markdown file
        const isNotFound =
          err instanceof Error &&
          "code" in err &&
          (err as NodeJS.ErrnoException).code === "ENOENT"
        if (!isNotFound) {
          await logger(
            "warn",
            `Then chain: error reading command file ${filePath}: ${err instanceof Error ? err.message : String(err)}`,
          )
        }
        return []
      }
    }

    return {
      "command.execute.before": async (input, _output) => {
        const { command, sessionID } = input

        // Read the command's markdown file and parse its then-chain
        const entries = await readCommandThenChain(command)

        if (entries.length === 0) {
          // No then-chain for this command.
          // If a chain is already active and this command was user-initiated
          // (not dispatched by the executor), interrupt the chain.
          if (
            stateManager.hasActiveChain(sessionID) &&
            !executor.pendingDispatches.has(sessionID)
          ) {
            await logger(
              "info",
              `Then chain: interrupted by user command: ${command}`,
            )
            stateManager.interrupt(sessionID)
          }
          return
        }

        // This command has a then-chain.
        // Determine if it was user-initiated or chain-initiated.
        if (stateManager.hasActiveChain(sessionID)) {
          if (executor.pendingDispatches.has(sessionID)) {
            // Chain-invoked command -- push nested frame
            const pushed = stateManager.pushChain(
              sessionID,
              entries,
              command,
            )
            if (pushed) {
              await logger(
                "info",
                `Then chain: pushed nested chain for ${command} (depth: ${stateManager.currentDepth(sessionID)}, entries: ${entries.length})`,
              )
            } else {
              await logger(
                "warn",
                `Then chain: max depth (${maxDepth}) exceeded for command: ${command}. Chain halted.`,
              )
            }
          } else {
            // User-invoked command while a chain is active -- interrupt
            await logger(
              "info",
              `Then chain: interrupted by user command: ${command}`,
            )
            stateManager.interrupt(sessionID)
            // Start a fresh chain for this user command
            stateManager.pushChain(sessionID, entries, command)
            await logger(
              "info",
              `Then chain: started for ${command} (${entries.length} entries)`,
            )
          }
        } else {
          // No active chain -- start a new one
          stateManager.pushChain(sessionID, entries, command)
          await logger(
            "info",
            `Then chain: started for ${command} (${entries.length} entries)`,
          )
        }
      },

      "chat.message": async (input, _output) => {
        const { sessionID } = input

        if (!stateManager.hasActiveChain(sessionID)) {
          return
        }

        const dispatched = await executor.processNext(sessionID)
        if (!dispatched) {
          await logger("info", "Then chain: completed")
        }
      },

      "experimental.chat.messages.transform": createSyntheticFilter(
        stateManager,
        {
          behavior: syntheticBehavior,
          defaultFollowUp: config?.defaultFollowUp,
        },
        logger,
      ),
    }
  }
}
