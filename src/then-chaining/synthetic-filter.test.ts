import { describe, expect, it } from "bun:test"
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
      tokens: { input: 0, output: 0, reasoning: 0, cache: { read: 0, write: 0 } },
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
  describe("with active chain", () => {
    it("removes synthetic messages when chain is active", async () => {
      const state = new ChainStateManager()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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

      expect(output.messages).toHaveLength(1)
      expect(output.messages[0].info.role).toBe("assistant")
    })

    it("does not remove non-synthetic messages when chain is active", async () => {
      const state = new ChainStateManager()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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

  describe("without active chain - keep behavior", () => {
    it("leaves synthetic messages untouched", async () => {
      const state = new ChainStateManager()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
        { behavior: "remove" },
        logger,
      )

      const output = { messages: [] as ReturnType<typeof makeUserMessage>[] }
      await filter({}, output)

      expect(output.messages).toHaveLength(0)
    })

    it("only checks the last message", async () => {
      const state = new ChainStateManager()
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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
      const { logger } = createMockLogger()
      const filter = createSyntheticFilter(
        state,
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
