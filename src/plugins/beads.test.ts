import { describe, expect, it, mock } from "bun:test"
import type { PluginInput } from "@opencode-ai/plugin"
import { BeadsPlugin } from "./beads.js"

// Mock the coordinator module — we need to control isChainActive/onChainComplete
// We can't easily mock the module-level singleton, so we test through the
// plugin's behavior with a fresh coordinator for integration-style tests.

function createMockShell(primeOutput = "mock beads context") {
  const syncCalls: number[] = []
  const primeCalls: number[] = []
  let callCount = 0

  // The $ template tag returns an object with .quiet() and .text() methods
  const $ = (strings: TemplateStringsArray) => {
    const cmd = strings[0]
    callCount++
    if (cmd.includes("bd sync")) {
      syncCalls.push(callCount)
      return { quiet: mock(() => Promise.resolve()) }
    }
    if (cmd.includes("bd prime")) {
      primeCalls.push(callCount)
      return { text: mock(() => Promise.resolve(primeOutput)) }
    }
    return { quiet: mock(() => Promise.resolve()), text: mock(() => Promise.resolve("")) }
  }

  return { $: $ as unknown as PluginInput["$"], syncCalls, primeCalls }
}

function createMockClient(existingMessages: unknown[] = []) {
  const promptCalls: Array<{ sessionID: string; text: string }> = []
  const logCalls: Array<{ level: string; message: string }> = []

  const client = {
    session: {
      prompt: mock(async (opts: { path: { id: string }; body: { parts: Array<{ text: string }> } }) => {
        promptCalls.push({
          sessionID: opts.path.id,
          text: opts.body.parts[0].text,
        })
        return { data: {} }
      }),
      messages: mock(async () => ({
        data: existingMessages,
      })),
    },
    app: {
      log: mock(async (opts: { body: { level: string; message: string } }) => {
        logCalls.push({ level: opts.body.level, message: opts.body.message })
        return {}
      }),
    },
  } as unknown as PluginInput["client"]

  return { client, promptCalls, logCalls }
}

describe("BeadsPlugin", () => {
  it("returns a valid Plugin factory function", () => {
    const plugin = BeadsPlugin()
    expect(typeof plugin).toBe("function")
  })

  it("initializes and returns hooks", async () => {
    const { client } = createMockClient()
    const { $ } = createMockShell()
    const plugin = BeadsPlugin()
    const hooks = await plugin({ client, $, directory: "/tmp" } as unknown as PluginInput)
    expect(hooks).toBeDefined()
    expect(hooks["chat.message"]).toBeDefined()
    expect(hooks.event).toBeDefined()
  })

  describe("chat.message", () => {
    it("triggers injection on first user message", async () => {
      const { client, promptCalls } = createMockClient()
      const { $ } = createMockShell("beads prime output")
      const plugin = BeadsPlugin()
      const hooks = await plugin({ client, $, directory: "/tmp" } as unknown as PluginInput)

      await hooks["chat.message"]!(
        { sessionID: "s1" } as any,
        { message: { sessionID: "s1", model: undefined, agent: undefined } } as any,
      )

      expect(promptCalls.length).toBe(1)
      expect(promptCalls[0].sessionID).toBe("s1")
      expect(promptCalls[0].text).toContain("<beads-context>")
      expect(promptCalls[0].text).toContain("beads prime output")
    })

    it("skips injection on second message in same session", async () => {
      const { client, promptCalls } = createMockClient()
      const { $ } = createMockShell("output")
      const plugin = BeadsPlugin()
      const hooks = await plugin({ client, $, directory: "/tmp" } as unknown as PluginInput)

      const input = { sessionID: "s1" } as any
      const output = { message: { sessionID: "s1" } } as any

      await hooks["chat.message"]!(input, output)
      await hooks["chat.message"]!(input, output)

      // Only one injection
      expect(promptCalls.length).toBe(1)
    })

    it("skips injection when beads context already exists in messages", async () => {
      const existingMessages = [
        {
          info: { role: "user" },
          parts: [{ type: "text", text: "some <beads-context> stuff" }],
        },
      ]
      const { client, promptCalls } = createMockClient(existingMessages)
      const { $ } = createMockShell("output")
      const plugin = BeadsPlugin()
      const hooks = await plugin({ client, $, directory: "/tmp" } as unknown as PluginInput)

      await hooks["chat.message"]!(
        { sessionID: "s1" } as any,
        { message: { sessionID: "s1" } } as any,
      )

      expect(promptCalls.length).toBe(0)
    })

    it("skips injection when bd prime returns empty output", async () => {
      const { client, promptCalls } = createMockClient()
      const { $ } = createMockShell("")
      const plugin = BeadsPlugin()
      const hooks = await plugin({ client, $, directory: "/tmp" } as unknown as PluginInput)

      await hooks["chat.message"]!(
        { sessionID: "s1" } as any,
        { message: { sessionID: "s1" } } as any,
      )

      expect(promptCalls.length).toBe(0)
    })
  })

  describe("event: session.idle", () => {
    it("runs bd sync on session idle", async () => {
      const { client } = createMockClient()
      const { $, syncCalls } = createMockShell()
      const plugin = BeadsPlugin()
      const hooks = await plugin({ client, $, directory: "/tmp" } as unknown as PluginInput)

      await hooks.event!(
        { event: { type: "session.idle", properties: { sessionID: "s1" } } } as any,
      )

      // sync is called: once during init log + once for idle
      expect(syncCalls.length).toBeGreaterThan(0)
    })
  })

  describe("event: session.compacted", () => {
    it("triggers re-injection on session compacted", async () => {
      const { client, promptCalls } = createMockClient()
      const { $ } = createMockShell("prime output")
      const plugin = BeadsPlugin()
      const hooks = await plugin({ client, $, directory: "/tmp" } as unknown as PluginInput)

      await hooks.event!(
        { event: { type: "session.compacted", properties: { sessionID: "s1" } } } as any,
      )

      expect(promptCalls.length).toBe(1)
      expect(promptCalls[0].text).toContain("<beads-context>")
    })
  })

  describe("error handling", () => {
    it("does not throw when bd commands fail", async () => {
      const { client } = createMockClient()
      const failingShell = ((_strings: TemplateStringsArray) => {
        return {
          quiet: () => Promise.reject(new Error("bd not found")),
          text: () => Promise.reject(new Error("bd not found")),
        }
      }) as unknown as PluginInput["$"]

      const plugin = BeadsPlugin()
      const hooks = await plugin({ client, $: failingShell, directory: "/tmp" } as unknown as PluginInput)

      // Should not throw
      await hooks["chat.message"]!(
        { sessionID: "s1" } as any,
        { message: { sessionID: "s1" } } as any,
      )

      // Should not throw
      await hooks.event!(
        { event: { type: "session.idle", properties: { sessionID: "s1" } } } as any,
      )
    })
  })
})
