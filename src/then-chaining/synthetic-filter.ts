import type { Hooks } from "@opencode-ai/plugin"
import type { Message, Part } from "@opencode-ai/sdk"
import type { ChainStateManager } from "./state.js"

export type SyntheticMessageBehavior = "keep" | "remove" | "replace"

export interface SyntheticFilterConfig {
  behavior: SyntheticMessageBehavior
  defaultFollowUp?: string
}

/** A message entry as seen in the transform hook output. */
type MessageEntry = { info: Message; parts: Part[] }

/**
 * Check if a message entry appears to be a synthetic follow-up injected
 * by OpenCode after a subtask-style command completes.
 *
 * Synthetic messages are user messages where at least one text part
 * has the `synthetic` flag set to true.
 */
function isSyntheticMessage(entry: MessageEntry): boolean {
  if (entry.info.role !== "user") {
    return false
  }

  return entry.parts.some(
    (part) => part.type === "text" && "synthetic" in part && part.synthetic === true,
  )
}

/**
 * Create the experimental.chat.messages.transform hook handler.
 *
 * When a then-chain is active: always remove synthetic messages
 * (the then-chain entry takes precedence).
 *
 * When no then-chain is active: apply the configured behavior
 * ("keep", "remove", or "replace").
 */
export function createSyntheticFilter(
  stateManager: ChainStateManager,
  config: SyntheticFilterConfig,
  logger: (
    level: "info" | "warn" | "error",
    message: string,
  ) => Promise<void>,
): NonNullable<Hooks["experimental.chat.messages.transform"]> {
  return async (_input, output) => {
    if (output.messages.length === 0) {
      return
    }

    const lastMessage = output.messages[output.messages.length - 1]
    if (!lastMessage || !isSyntheticMessage(lastMessage)) {
      return
    }

    // Extract session ID from the message itself since the hook
    // input is empty ({}) and does not provide a session ID.
    const sessionID = lastMessage.info.sessionID

    // When a then-chain is active for this session, always remove
    // synthetic messages so the chain executor's injected message
    // takes precedence.
    if (sessionID && stateManager.hasActiveChain(sessionID)) {
      output.messages.pop()
      await logger("info", "Then chain: removed synthetic follow-up message")
      return
    }

    // No active chain -- apply configured behavior
    switch (config.behavior) {
      case "keep":
        // Leave the synthetic message as-is
        break
      case "remove":
        output.messages.pop()
        await logger(
          "info",
          "Synthetic filter: removed synthetic follow-up message",
        )
        break
      case "replace":
        if (config.defaultFollowUp) {
          // Replace the synthetic text parts with the configured follow-up
          // and clear the synthetic flag so the replaced message is treated
          // as a normal user message.
          for (const part of lastMessage.parts) {
            if (part.type === "text" && "synthetic" in part && part.synthetic) {
              part.text = config.defaultFollowUp
              part.synthetic = false
            }
          }
          await logger(
            "info",
            "Synthetic filter: replaced synthetic follow-up message",
          )
        }
        break
    }
  }
}
