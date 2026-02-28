import { describe, expect, it } from "bun:test"
import { parseThenChain } from "./frontmatter.js"

describe("parseThenChain", () => {
  describe("single string value", () => {
    it("parses a single prompt string", () => {
      const md = `---
description: test
then: "Summarize your findings"
---
Do the thing.`
      const result = parseThenChain(md)
      expect(result).toEqual([
        { value: "Summarize your findings", type: "prompt" },
      ])
    })

    it("parses a single command string", () => {
      const md = `---
description: test
then: "/generate-report"
---
Do the thing.`
      const result = parseThenChain(md)
      expect(result).toEqual([
        { value: "/generate-report", type: "command" },
      ])
    })

    it("preserves arguments in command entries", () => {
      const md = `---
then: "/deploy staging"
---
Deploy.`
      const result = parseThenChain(md)
      expect(result).toEqual([
        { value: "/deploy staging", type: "command" },
      ])
    })
  })

  describe("array value", () => {
    it("parses an ordered array of mixed entries", () => {
      const md = `---
then:
  - "Check for changes"
  - "/run-tests"
  - "/bump-version"
  - "Summarize everything"
---
Prepare release.`
      const result = parseThenChain(md)
      expect(result).toEqual([
        { value: "Check for changes", type: "prompt" },
        { value: "/run-tests", type: "command" },
        { value: "/bump-version", type: "command" },
        { value: "Summarize everything", type: "prompt" },
      ])
    })

    it("filters out empty strings in arrays", () => {
      const md = `---
then:
  - "step one"
  - ""
  - "step two"
---
Content.`
      const result = parseThenChain(md)
      expect(result).toEqual([
        { value: "step one", type: "prompt" },
        { value: "step two", type: "prompt" },
      ])
    })

    it("filters out non-string entries in arrays", () => {
      const md = `---
then:
  - "step one"
  - 42
  - true
  - "step two"
---
Content.`
      const result = parseThenChain(md)
      expect(result).toEqual([
        { value: "step one", type: "prompt" },
        { value: "step two", type: "prompt" },
      ])
    })
  })

  describe("empty/missing then values", () => {
    it("returns [] when no frontmatter exists", () => {
      const md = "Just some markdown content."
      expect(parseThenChain(md)).toEqual([])
    })

    it("returns [] when frontmatter has no then key", () => {
      const md = `---
description: test command
---
Content.`
      expect(parseThenChain(md)).toEqual([])
    })

    it("returns [] when then is an empty string", () => {
      const md = `---
then: ""
---
Content.`
      expect(parseThenChain(md)).toEqual([])
    })

    it("returns [] when then is null", () => {
      const md = `---
then: null
---
Content.`
      expect(parseThenChain(md)).toEqual([])
    })

    it("returns [] when then is an empty array", () => {
      const md = `---
then: []
---
Content.`
      expect(parseThenChain(md)).toEqual([])
    })
  })

  describe("edge cases", () => {
    it("handles frontmatter with other keys alongside then", () => {
      const md = `---
description: My command
author: someone
then: "/next-step"
priority: high
---
Content.`
      const result = parseThenChain(md)
      expect(result).toEqual([
        { value: "/next-step", type: "command" },
      ])
    })

    it("handles malformed YAML gracefully", () => {
      const md = `---
then: [unclosed bracket
---
Content.`
      expect(parseThenChain(md)).toEqual([])
    })

    it("handles CRLF line endings", () => {
      const md = "---\r\nthen: \"do something\"\r\n---\r\nContent."
      const result = parseThenChain(md)
      expect(result).toEqual([
        { value: "do something", type: "prompt" },
      ])
    })

    it("handles then value that is a number", () => {
      const md = `---
then: 42
---
Content.`
      expect(parseThenChain(md)).toEqual([])
    })

    it("handles then value that is a boolean", () => {
      const md = `---
then: true
---
Content.`
      expect(parseThenChain(md)).toEqual([])
    })

    it("handles then value that is an object", () => {
      const md = `---
then:
  key: value
---
Content.`
      expect(parseThenChain(md)).toEqual([])
    })
  })
})
