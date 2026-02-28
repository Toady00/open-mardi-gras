import { describe, expect, it } from "bun:test"
import type { ThenEntry } from "./frontmatter.js"
import { ChainStateManager } from "./state.js"

function prompt(value: string): ThenEntry {
  return { value, type: "prompt" }
}

function command(value: string): ThenEntry {
  return { value, type: "command" }
}

describe("ChainStateManager", () => {
  describe("pushChain", () => {
    it("pushes a chain frame for a new session", () => {
      const mgr = new ChainStateManager()
      const entries = [prompt("step 1"), command("/step-2")]
      const result = mgr.pushChain("session-1", entries, "/my-cmd")
      expect(result).toBe(true)
      expect(mgr.hasActiveChain("session-1")).toBe(true)
      expect(mgr.currentDepth("session-1")).toBe(1)
    })

    it("pushes nested frames onto the stack", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("a")], "/cmd-1")
      mgr.pushChain("s1", [prompt("b")], "/cmd-2")
      expect(mgr.currentDepth("s1")).toBe(2)
    })

    it("enforces max depth", () => {
      const mgr = new ChainStateManager(2)
      mgr.pushChain("s1", [prompt("a")], "/cmd-1")
      mgr.pushChain("s1", [prompt("b")], "/cmd-2")
      const result = mgr.pushChain("s1", [prompt("c")], "/cmd-3")
      expect(result).toBe(false)
      expect(mgr.currentDepth("s1")).toBe(2) // not 3
    })

    it("uses default max depth of 10", () => {
      const mgr = new ChainStateManager()
      for (let i = 0; i < 10; i++) {
        expect(mgr.pushChain("s1", [prompt(`step-${i}`)], `/cmd-${i}`)).toBe(
          true,
        )
      }
      expect(mgr.pushChain("s1", [prompt("too deep")], "/cmd-11")).toBe(false)
    })
  })

  describe("advance", () => {
    it("returns entries in order", () => {
      const mgr = new ChainStateManager()
      const entries = [prompt("a"), command("/b"), prompt("c")]
      mgr.pushChain("s1", entries, "/cmd")

      expect(mgr.advance("s1")).toEqual(prompt("a"))
      expect(mgr.advance("s1")).toEqual(command("/b"))
      expect(mgr.advance("s1")).toEqual(prompt("c"))
    })

    it("returns undefined when frame is exhausted", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("only one")], "/cmd")
      mgr.advance("s1") // consume it
      expect(mgr.advance("s1")).toBeUndefined()
    })

    it("returns undefined when no active chain", () => {
      const mgr = new ChainStateManager()
      expect(mgr.advance("nonexistent")).toBeUndefined()
    })

    it("advances the innermost frame only", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("outer-1"), prompt("outer-2")], "/outer")
      mgr.advance("s1") // consume outer-1
      mgr.pushChain("s1", [prompt("inner-1")], "/inner")

      // Should advance inner frame, not outer
      expect(mgr.advance("s1")).toEqual(prompt("inner-1"))
      expect(mgr.advance("s1")).toBeUndefined() // inner exhausted
    })
  })

  describe("popChain", () => {
    it("removes the innermost frame", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("outer")], "/outer")
      mgr.pushChain("s1", [prompt("inner")], "/inner")
      expect(mgr.currentDepth("s1")).toBe(2)

      mgr.popChain("s1")
      expect(mgr.currentDepth("s1")).toBe(1)
    })

    it("cleans up session when stack becomes empty", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("only")], "/cmd")
      mgr.popChain("s1")
      expect(mgr.hasActiveChain("s1")).toBe(false)
      expect(mgr.currentDepth("s1")).toBe(0)
    })

    it("is a no-op for nonexistent sessions", () => {
      const mgr = new ChainStateManager()
      // Should not throw
      mgr.popChain("nonexistent")
    })

    it("resumes outer frame after popping inner", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("outer-1"), prompt("outer-2")], "/outer")
      mgr.advance("s1") // consume outer-1
      mgr.pushChain("s1", [prompt("inner-1")], "/inner")
      mgr.advance("s1") // consume inner-1
      mgr.popChain("s1") // pop inner frame

      // Should now see outer-2
      expect(mgr.advance("s1")).toEqual(prompt("outer-2"))
    })
  })

  describe("hasActiveChain", () => {
    it("returns false for nonexistent sessions", () => {
      const mgr = new ChainStateManager()
      expect(mgr.hasActiveChain("nope")).toBe(false)
    })

    it("returns true when entries remain", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("a")], "/cmd")
      expect(mgr.hasActiveChain("s1")).toBe(true)
    })

    it("returns false when all entries are exhausted", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("a")], "/cmd")
      mgr.advance("s1") // exhaust the only entry
      expect(mgr.hasActiveChain("s1")).toBe(false)
    })

    it("returns true when outer frame has entries after inner is exhausted", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("outer-1"), prompt("outer-2")], "/outer")
      mgr.advance("s1") // consume outer-1
      mgr.pushChain("s1", [prompt("inner-1")], "/inner")
      mgr.advance("s1") // exhaust inner
      // Inner is exhausted but outer still has outer-2
      expect(mgr.hasActiveChain("s1")).toBe(true)
    })
  })

  describe("currentDepth", () => {
    it("returns 0 for nonexistent sessions", () => {
      const mgr = new ChainStateManager()
      expect(mgr.currentDepth("nope")).toBe(0)
    })

    it("tracks depth correctly through push/pop", () => {
      const mgr = new ChainStateManager()
      expect(mgr.currentDepth("s1")).toBe(0)
      mgr.pushChain("s1", [prompt("a")], "/a")
      expect(mgr.currentDepth("s1")).toBe(1)
      mgr.pushChain("s1", [prompt("b")], "/b")
      expect(mgr.currentDepth("s1")).toBe(2)
      mgr.popChain("s1")
      expect(mgr.currentDepth("s1")).toBe(1)
      mgr.popChain("s1")
      expect(mgr.currentDepth("s1")).toBe(0)
    })
  })

  describe("interrupt", () => {
    it("clears all state for a session", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("a"), prompt("b")], "/cmd-1")
      mgr.pushChain("s1", [prompt("c")], "/cmd-2")
      mgr.interrupt("s1")
      expect(mgr.hasActiveChain("s1")).toBe(false)
      expect(mgr.currentDepth("s1")).toBe(0)
    })

    it("does not affect other sessions", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("a")], "/cmd-1")
      mgr.pushChain("s2", [prompt("b")], "/cmd-2")
      mgr.interrupt("s1")
      expect(mgr.hasActiveChain("s1")).toBe(false)
      expect(mgr.hasActiveChain("s2")).toBe(true)
    })

    it("is a no-op for nonexistent sessions", () => {
      const mgr = new ChainStateManager()
      // Should not throw
      mgr.interrupt("nonexistent")
    })
  })

  describe("multi-session isolation", () => {
    it("tracks chains independently per session", () => {
      const mgr = new ChainStateManager()
      mgr.pushChain("s1", [prompt("s1-a"), prompt("s1-b")], "/cmd-1")
      mgr.pushChain("s2", [prompt("s2-a")], "/cmd-2")

      expect(mgr.advance("s1")).toEqual(prompt("s1-a"))
      expect(mgr.advance("s2")).toEqual(prompt("s2-a"))
      expect(mgr.advance("s1")).toEqual(prompt("s1-b"))
      expect(mgr.advance("s2")).toBeUndefined()
    })
  })
})
