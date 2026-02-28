import { describe, expect, it, mock } from "bun:test"
import type { PluginInput } from "@opencode-ai/plugin"
import { ChainExecutor } from "./executor.js"
import type { ThenEntry } from "./frontmatter.js"
import { ChainStateManager } from "./state.js"

function prompt(value: string): ThenEntry {
  return { value, type: "prompt" }
}

function command(value: string): ThenEntry {
  return { value, type: "command" }
}

function createMockClient() {
  const promptCalls: Array<{ sessionID: string; text: string }> = []
  const commandCalls: Array<{
    sessionID: string
    command: string
    arguments: string
  }> = []

  const client = {
    session: {
      prompt: mock(async (opts: { body: { parts: Array<{ text: string }> }; path: { id: string } }) => {
        promptCalls.push({
          sessionID: opts.path.id,
          text: opts.body.parts[0].text,
        })
        return { data: { info: {}, parts: [] } }
      }),
      command: mock(async (opts: { body: { command: string; arguments: string }; path: { id: string } }) => {
        commandCalls.push({
          sessionID: opts.path.id,
          command: opts.body.command,
          arguments: opts.body.arguments,
        })
        return { data: { info: {}, parts: [] } }
      }),
    },
  } as unknown as PluginInput["client"]

  return { client, promptCalls, commandCalls }
}

function createMockLogger() {
  const logs: Array<{ level: string; message: string }> = []
  const logger = async (level: "info" | "warn" | "error", message: string) => {
    logs.push({ level, message })
  }
  return { logger, logs }
}

describe("ChainExecutor", () => {
  describe("processNext with prompts", () => {
    it("dispatches a prompt entry via client.session.prompt", async () => {
      const state = new ChainStateManager()
      const { client, promptCalls } = createMockClient()
      const { logger } = createMockLogger()
      const executor = new ChainExecutor(client, state, logger)

      state.pushChain("s1", [prompt("Hello world")], "/test")
      const result = await executor.processNext("s1")

      expect(result).toBe(true)
      expect(promptCalls).toHaveLength(1)
      expect(promptCalls[0].sessionID).toBe("s1")
      expect(promptCalls[0].text).toBe("Hello world")
    })

    it("truncates long prompt in log preview", async () => {
      const state = new ChainStateManager()
      const { client } = createMockClient()
      const { logger, logs } = createMockLogger()
      const executor = new ChainExecutor(client, state, logger)

      const longPrompt = "A".repeat(100)
      state.pushChain("s1", [prompt(longPrompt)], "/test")
      await executor.processNext("s1")

      const infoLog = logs.find(
        (l) => l.level === "info" && l.message.includes("injecting prompt"),
      )
      expect(infoLog).toBeDefined()
      expect(infoLog!.message).toContain("...")
      expect(infoLog!.message.length).toBeLessThan(longPrompt.length + 50)
    })
  })

  describe("processNext with commands", () => {
    it("dispatches a command entry via client.session.command", async () => {
      const state = new ChainStateManager()
      const { client, commandCalls } = createMockClient()
      const { logger } = createMockLogger()
      const executor = new ChainExecutor(client, state, logger)

      state.pushChain("s1", [command("/deploy")], "/test")
      const result = await executor.processNext("s1")

      expect(result).toBe(true)
      expect(commandCalls).toHaveLength(1)
      expect(commandCalls[0].command).toBe("/deploy")
      expect(commandCalls[0].arguments).toBe("")
    })

    it("splits command name and arguments", async () => {
      const state = new ChainStateManager()
      const { client, commandCalls } = createMockClient()
      const { logger } = createMockLogger()
      const executor = new ChainExecutor(client, state, logger)

      state.pushChain("s1", [command("/deploy staging --force")], "/test")
      await executor.processNext("s1")

      expect(commandCalls[0].command).toBe("/deploy")
      expect(commandCalls[0].arguments).toBe("staging --force")
    })

    it("tracks pendingDispatches during command execution", async () => {
      const state = new ChainStateManager()
      const { logger } = createMockLogger()

      let capturedPending = false
      const client = {
        session: {
          prompt: mock(async () => ({ data: { info: {}, parts: [] } })),
          command: mock(async () => {
            // Check state during execution
            capturedPending = executor.pendingDispatches.has("s1")
            return { data: { info: {}, parts: [] } }
          }),
        },
      } as unknown as PluginInput["client"]

      const executor = new ChainExecutor(client, state, logger)
      state.pushChain("s1", [command("/test")], "/test")
      await executor.processNext("s1")

      expect(capturedPending).toBe(true)
      // After completion, should be cleared
      expect(executor.pendingDispatches.has("s1")).toBe(false)
    })
  })

  describe("error handling", () => {
    it("skips to next entry when prompt dispatch fails", async () => {
      const state = new ChainStateManager()
      const { logger, logs } = createMockLogger()

      let callCount = 0
      const client = {
        session: {
          prompt: mock(async () => {
            callCount++
            if (callCount === 1) {
              throw new Error("Network error")
            }
            return { data: { info: {}, parts: [] } }
          }),
          command: mock(async () => ({ data: { info: {}, parts: [] } })),
        },
      } as unknown as PluginInput["client"]

      const executor = new ChainExecutor(client, state, logger)
      state.pushChain("s1", [prompt("fail"), prompt("succeed")], "/test")
      const result = await executor.processNext("s1")

      expect(result).toBe(true)
      expect(callCount).toBe(2) // first failed, second succeeded
      expect(logs.some((l) => l.level === "error")).toBe(true)
    })

    it("skips to next entry when command dispatch fails", async () => {
      const state = new ChainStateManager()
      const { logger } = createMockLogger()

      const promptCalls: string[] = []
      const client = {
        session: {
          prompt: mock(async (opts: { body: { parts: Array<{ text: string }> } }) => {
            promptCalls.push(opts.body.parts[0].text)
            return { data: { info: {}, parts: [] } }
          }),
          command: mock(async () => {
            throw new Error("Command not found")
          }),
        },
      } as unknown as PluginInput["client"]

      const executor = new ChainExecutor(client, state, logger)
      state.pushChain(
        "s1",
        [command("/bad-cmd"), prompt("fallback")],
        "/test",
      )
      const result = await executor.processNext("s1")

      expect(result).toBe(true)
      expect(promptCalls).toEqual(["fallback"])
    })

    it("clears pendingDispatches even on command failure", async () => {
      const state = new ChainStateManager()
      const { logger } = createMockLogger()

      const client = {
        session: {
          prompt: mock(async () => ({ data: { info: {}, parts: [] } })),
          command: mock(async () => {
            throw new Error("fail")
          }),
        },
      } as unknown as PluginInput["client"]

      const executor = new ChainExecutor(client, state, logger)
      state.pushChain("s1", [command("/fail")], "/test")
      await executor.processNext("s1")

      expect(executor.pendingDispatches.has("s1")).toBe(false)
    })
  })

  describe("frame unwinding", () => {
    it("returns false when chain is complete", async () => {
      const state = new ChainStateManager()
      const { client } = createMockClient()
      const { logger } = createMockLogger()
      const executor = new ChainExecutor(client, state, logger)

      state.pushChain("s1", [prompt("only")], "/test")
      await executor.processNext("s1") // dispatches "only"
      const result = await executor.processNext("s1")

      expect(result).toBe(false)
    })

    it("returns false when no active chain exists", async () => {
      const state = new ChainStateManager()
      const { client } = createMockClient()
      const { logger } = createMockLogger()
      const executor = new ChainExecutor(client, state, logger)

      const result = await executor.processNext("nonexistent")
      expect(result).toBe(false)
    })

    it("pops exhausted frame and advances parent", async () => {
      const state = new ChainStateManager()
      const { client, promptCalls } = createMockClient()
      const { logger } = createMockLogger()
      const executor = new ChainExecutor(client, state, logger)

      state.pushChain("s1", [prompt("outer-1"), prompt("outer-2")], "/outer")
      state.advance("s1") // consume outer-1 (as if dispatched)
      state.pushChain("s1", [prompt("inner-1")], "/inner")

      // processNext should dispatch inner-1
      await executor.processNext("s1")
      expect(promptCalls[0].text).toBe("inner-1")

      // Next processNext: inner is exhausted, should pop and dispatch outer-2
      const result = await executor.processNext("s1")
      expect(result).toBe(true)
      expect(promptCalls[1].text).toBe("outer-2")
    })
  })
})
