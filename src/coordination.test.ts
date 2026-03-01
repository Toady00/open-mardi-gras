import { describe, expect, it, mock } from "bun:test"
import { PluginCoordinator } from "./coordination.js"
import type { ChainStateProvider } from "./coordination.js"

describe("PluginCoordinator", () => {
  describe("isChainActive", () => {
    it("returns false when no providers are registered", () => {
      const coord = new PluginCoordinator()
      expect(coord.isChainActive("session-1")).toBe(false)
    })

    it("returns true when a provider reports an active chain", () => {
      const coord = new PluginCoordinator()
      const provider: ChainStateProvider = {
        hasActiveChain: (id) => id === "session-1",
      }
      coord.registerChainState(provider)
      expect(coord.isChainActive("session-1")).toBe(true)
      expect(coord.isChainActive("session-2")).toBe(false)
    })

    it("queries all registered providers", () => {
      const coord = new PluginCoordinator()
      const providerA: ChainStateProvider = {
        hasActiveChain: (id) => id === "a",
      }
      const providerB: ChainStateProvider = {
        hasActiveChain: (id) => id === "b",
      }
      coord.registerChainState(providerA)
      coord.registerChainState(providerB)
      expect(coord.isChainActive("a")).toBe(true)
      expect(coord.isChainActive("b")).toBe(true)
      expect(coord.isChainActive("c")).toBe(false)
    })
  })

  describe("onChainComplete / notifyChainComplete", () => {
    it("fires the callback when notifyChainComplete is called", () => {
      const coord = new PluginCoordinator()
      const cb = mock(() => {})
      coord.onChainComplete("session-1", cb)
      coord.notifyChainComplete("session-1")
      expect(cb).toHaveBeenCalledTimes(1)
    })

    it("removes the callback after firing", () => {
      const coord = new PluginCoordinator()
      const cb = mock(() => {})
      coord.onChainComplete("session-1", cb)
      coord.notifyChainComplete("session-1")
      coord.notifyChainComplete("session-1")
      expect(cb).toHaveBeenCalledTimes(1)
    })

    it("is a no-op when no callback is queued", () => {
      const coord = new PluginCoordinator()
      // Should not throw
      coord.notifyChainComplete("nonexistent")
    })

    it("swallows synchronous errors from callbacks", () => {
      const coord = new PluginCoordinator()
      coord.onChainComplete("session-1", () => {
        throw new Error("callback error")
      })
      // Must not throw
      coord.notifyChainComplete("session-1")
    })

    it("deduplicates callbacks per session (replaces, does not stack)", () => {
      const coord = new PluginCoordinator()
      const cb1 = mock(() => {})
      const cb2 = mock(() => {})
      coord.onChainComplete("session-1", cb1)
      coord.onChainComplete("session-1", cb2)
      coord.notifyChainComplete("session-1")
      expect(cb1).toHaveBeenCalledTimes(0)
      expect(cb2).toHaveBeenCalledTimes(1)
    })
  })

  describe("per-session isolation", () => {
    it("chains in different sessions do not interfere", () => {
      const coord = new PluginCoordinator()
      const cbA = mock(() => {})
      const cbB = mock(() => {})
      coord.onChainComplete("session-a", cbA)
      coord.onChainComplete("session-b", cbB)

      coord.notifyChainComplete("session-a")
      expect(cbA).toHaveBeenCalledTimes(1)
      expect(cbB).toHaveBeenCalledTimes(0)

      coord.notifyChainComplete("session-b")
      expect(cbB).toHaveBeenCalledTimes(1)
    })

    it("isChainActive is per-session", () => {
      const coord = new PluginCoordinator()
      const provider: ChainStateProvider = {
        hasActiveChain: (id) => id === "active-session",
      }
      coord.registerChainState(provider)
      expect(coord.isChainActive("active-session")).toBe(true)
      expect(coord.isChainActive("other-session")).toBe(false)
    })
  })

  describe("registerChainState", () => {
    it("accepts multiple providers", () => {
      const coord = new PluginCoordinator()
      const p1: ChainStateProvider = { hasActiveChain: () => false }
      const p2: ChainStateProvider = { hasActiveChain: () => false }
      coord.registerChainState(p1)
      coord.registerChainState(p2)
      // No error — both registered
      expect(coord.isChainActive("any")).toBe(false)
    })
  })
})
