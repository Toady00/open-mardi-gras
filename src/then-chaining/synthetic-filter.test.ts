import { describe, expect, it } from "bun:test"
import type { ChainExecutor } from "./executor.js"
import type { ThenEntry } from "./frontmatter.js"
import { ChainStateManager } from "./state.js"
import { createSyntheticFilter } from "./synthetic-filter.js"

function prompt(value: string): ThenEntry {
  return { value, type: "prompt" }
}

function createMockLogger() {
  const logs: Array<{ level: string; message: string }> = []
  const logger = async (level: "info" | "warn" | "error", message: string) => {
    logs.push({ level, message })
  }
  return { logger, logs }
}

function createMockExecutor(): ChainExecutor {
  const pendingPrompts = new Map<string, string>()
  return {
    pendingDispatches: new Set(),
    pendingPrompts,
    consumePendingPrompt(sessionID: string) {
      const p = pendingPrompts.get(sessionID)
      if (p !== undefined) {
        pendingPrompts.delete(sessionID)
      }
      return p
    },
  } as unknown as ChainExecutor
}

function makeUserMessage(
  sessionID: string,
  text: string,
  synthetic: boolean = false,
) {
  return {
    info: {
      id: "msg-1",
      sessionID,
      role: "user" as const,
      time: { created: Date.now() },
      agent: "default",
      model: { providerID: "test", modelID: "test" },
    },
    parts: [
      {
        id: "part-1",
        sessionID,
        messageID: "msg-1",
        type: "text" as const,
        text,
        synthetic,
      },
    ],
  }
}

function makeAssistantMessage(sessionID: string) {
  return {
    info: {
      id: "msg-2",
      sessionID,
      role: "assistant" as const,
      time: { created: Date.now() },
      parentID: "msg-1",
      modelID: "test",
      providerID: "test",
      mode: "default",
      path: { cwd: "/", root: "/" },
      cost: 0,
      tokens: {
        input: 0,
        output: 0,
        reasoning: 0,
        cache: { read: 0, write: 0 },
      },
    },
    parts: [
      {
        id: "part-2",
        sessionID,
        messageID: "msg-2",
        type: "text" as const,
        text: "Response",
      },
    ],
  }
}

describe("createSyntheticFilter", () => {
  describe("with active chain but no pending prompt", () => {
    it("leaves synthetic messages alone when chain is active but no pending prompt", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "keep" },
        logger,
      )

      state.pushChain("s1", [prompt("next step")], "/cmd")

      const messages = [
        makeAssistantMessage("s1"),
        makeUserMessage("s1", "synthetic follow-up", true),
      ]
      const output = { messages }

      await filter({}, output)

      // Should NOT remove — the chain hasn't dispatched yet,
      // so the current command's LLM turn needs this message.
      expect(output.messages).toHaveLength(2)
    })

    it("does not remove non-synthetic messages when chain is active", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "keep" },
        logger,
      )

      state.pushChain("s1", [prompt("next")], "/cmd")

      const messages = [makeUserMessage("s1", "real user message", false)]
      const output = { messages }

      await filter({}, output)

      expect(output.messages).toHaveLength(1)
    })
  })

  describe("pending prompt replacement", () => {
    it("replaces last message text with pending prompt", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "keep" },
        logger,
      )

      // Simulate the executor setting a pending prompt
      executor.pendingPrompts.set("s1", "Summarize your findings")

      const messages = [makeUserMessage("s1", "original text", false)]
      const output = { messages }

      await filter({}, output)

      expect(output.messages).toHaveLength(1)
      expect(output.messages[0].parts[0].text).toBe("Summarize your findings")
    })

    it("consumes the pending prompt after replacement", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "keep" },
        logger,
      )

      executor.pendingPrompts.set("s1", "Do the thing")

      const messages = [makeUserMessage("s1", "original", false)]
      const output = { messages }

      await filter({}, output)

      // Pending prompt should be consumed
      expect(executor.pendingPrompts.has("s1")).toBe(false)
    })

    it("clears synthetic flag when replacing with pending prompt", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "keep" },
        logger,
      )

      executor.pendingPrompts.set("s1", "Next step")

      const messages = [makeUserMessage("s1", "synthetic msg", true)]
      const output = { messages }

      await filter({}, output)

      const part = output.messages[0].parts[0] as { synthetic?: boolean }
      expect(part.synthetic).toBe(false)
      expect(output.messages[0].parts[0].text).toBe("Next step")
    })
  })

  describe("without active chain - keep behavior", () => {
    it("leaves synthetic messages untouched", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "keep" },
        logger,
      )

      const messages = [makeUserMessage("s1", "synthetic", true)]
      const output = { messages }

      await filter({}, output)

      expect(output.messages).toHaveLength(1)
      expect(output.messages[0].parts[0].text).toBe("synthetic")
    })
  })

  describe("without active chain - remove behavior", () => {
    it("removes synthetic messages", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "remove" },
        logger,
      )

      const messages = [
        makeAssistantMessage("s1"),
        makeUserMessage("s1", "synthetic", true),
      ]
      const output = { messages }

      await filter({}, output)

      expect(output.messages).toHaveLength(1)
      expect(output.messages[0].info.role).toBe("assistant")
    })
  })

  describe("without active chain - replace behavior", () => {
    it("replaces synthetic message text with defaultFollowUp", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "replace", defaultFollowUp: "What next?" },
        logger,
      )

      const messages = [makeUserMessage("s1", "original synthetic", true)]
      const output = { messages }

      await filter({}, output)

      expect(output.messages).toHaveLength(1)
      expect(output.messages[0].parts[0].text).toBe("What next?")
    })

    it("clears the synthetic flag after replacement", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "replace", defaultFollowUp: "What next?" },
        logger,
      )

      const messages = [makeUserMessage("s1", "original", true)]
      const output = { messages }

      await filter({}, output)

      const part = output.messages[0].parts[0] as { synthetic?: boolean }
      expect(part.synthetic).toBe(false)
    })

    it("does nothing if defaultFollowUp is not set", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "replace" },
        logger,
      )

      const messages = [makeUserMessage("s1", "original", true)]
      const output = { messages }

      await filter({}, output)

      expect(output.messages).toHaveLength(1)
      expect(output.messages[0].parts[0].text).toBe("original")
    })
  })

  describe("edge cases", () => {
    it("does nothing when messages array is empty", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "remove" },
        logger,
      )

      const output = { messages: [] as ReturnType<typeof makeUserMessage>[] }
      await filter({}, output)

      expect(output.messages).toHaveLength(0)
    })

    it("only checks the last message", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "remove" },
        logger,
      )

      const messages = [
        makeUserMessage("s1", "first synthetic", true),
        makeUserMessage("s1", "non-synthetic last", false),
      ]
      const output = { messages }

      await filter({}, output)

      // Should not remove anything since last message is not synthetic
      expect(output.messages).toHaveLength(2)
    })

    it("does not touch assistant messages", async () => {
      const state = new ChainStateManager()
      const executor = createMockExecutor()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        executor,
        { behavior: "remove" },
        logger,
      )

      const messages = [makeAssistantMessage("s1")]
      const output = { messages }

      await filter({}, output)

      expect(output.messages).toHaveLength(1)
    })
  })
})
