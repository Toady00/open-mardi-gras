import type { Hooks } from "@opencode-ai/plugin"
import type { Message, Part } from "@opencode-ai/sdk"
import type { ChainExecutor } from "./executor.js"
import type { ChainStateManager } from "./state.js"

export type SyntheticMessageBehavior = "keep" | "remove" | "replace"

export interface SyntheticFilterConfig {
  behavior: SyntheticMessageBehavior
  defaultFollowUp?: string
}

/** A message entry as seen in the transform hook output. */
type MessageEntry = { info: Message; parts: Part[] }

/**
 * Check if a message entry is a user message (potential candidate for
 * prompt injection). We look for user-role messages whose text parts
 * may be synthetic or match OpenCode's generic follow-up.
 */
function isUserMessage(entry: MessageEntry): boolean {
  return entry.info.role === "user"
}

/**
 * Check if a message entry appears to be a synthetic follow-up injected
 * by OpenCode after a subtask-style command completes.
 */
function isSyntheticMessage(entry: MessageEntry): boolean {
  if (entry.info.role !== "user") {
    return false
  }

  return entry.parts.some(
    (part) =>
      part.type === "text" && "synthetic" in part && part.synthetic === true,
  )
}

/**
 * Create the experimental.chat.messages.transform hook handler.
 *
 * When a then-chain has a pending prompt: replace the last user message's
 * text with the pending prompt. This is the mechanism that makes the LLM
 * actually see and respond to the chained prompt.
 *
 * When no pending prompt but a chain is active: remove synthetic messages
 * to prevent interference.
 *
 * When no active chain: apply the configured behavior
 * ("keep", "remove", or "replace").
 */
export function createSyntheticFilter(
  stateManager: ChainStateManager,
  executor: ChainExecutor,
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
    if (!lastMessage || !isUserMessage(lastMessage)) {
      return
    }

    // Extract session ID from the message itself since the hook
    // input is empty ({}) and does not provide a session ID.
    const sessionID = lastMessage.info.sessionID
    if (!sessionID) {
      return
    }

    // Check if the executor has a pending prompt to inject.
    // This is phase 2 of the two-phase dispatch: promptAsync triggered
    // a new LLM turn, now we replace the message text so the LLM
    // sees our prompt instead of whatever OpenCode injected.
    const pendingPrompt = executor.consumePendingPrompt(sessionID)
    if (pendingPrompt) {
      // Replace all text parts with our prompt
      for (const part of lastMessage.parts) {
        if (part.type === "text") {
          part.text = pendingPrompt
          if ("synthetic" in part) {
            part.synthetic = false
          }
        }
      }
      await logger(
        "info",
        `Then chain: replaced message with pending prompt`,
      )
      return
    }

    // No pending prompt -- apply configured behavior for synthetic
    // messages only. When a chain is active but hasn't dispatched yet,
    // we leave messages untouched so the current command's LLM turn
    // completes normally.
    if (!isSyntheticMessage(lastMessage)) {
      return
    }

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
          for (const part of lastMessage.parts) {
            if (
              part.type === "text" &&
              "synthetic" in part &&
              part.synthetic
            ) {
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
