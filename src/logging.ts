import type { PluginInput } from "@opencode-ai/plugin"

export type PluginLogger = (
  level: "info" | "warn" | "error",
  message: string,
) => Promise<void>

/**
 * Create a logger function that logs to OpenCode's app log.
 * Errors from the log call are swallowed — logging must never
 * crash the plugin.
 */
export function createPluginLogger(
  client: PluginInput["client"],
): PluginLogger {
  return async (level, message) => {
    try {
      await client.app.log({
        body: { service: "open-mardi-gras", level, message },
      })
    } catch {
      // Log failure should not prevent plugin from functioning
    }
  }
}
