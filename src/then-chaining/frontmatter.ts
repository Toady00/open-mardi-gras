import yaml from "js-yaml"

export interface ThenEntry {
  /** The raw string value from frontmatter */
  value: string
  /** Whether this entry is a command (starts with /) or a prompt */
  type: "command" | "prompt"
}

/**
 * Extract YAML frontmatter from markdown content.
 * Frontmatter is delimited by `---` on its own line at the start of the file.
 * Returns the raw YAML string, or null if no frontmatter is found.
 */
function extractFrontmatter(markdownContent: string): string | null {
  const match = markdownContent.match(/^---\r?\n([\s\S]*?)\r?\n---/)
  if (!match?.[1]) {
    return null
  }
  return match[1]
}

/**
 * Classify a then entry string as either a command or a prompt.
 */
function classifyEntry(value: string): ThenEntry {
  return {
    value,
    type: value.startsWith("/") ? "command" : "prompt",
  }
}

/**
 * Parse the `then` key from a command markdown file's YAML frontmatter.
 * Returns an empty array if no `then` key is present or the value is empty.
 *
 * Handles all three syntactic forms:
 * 1. Single string: `then: "some prompt"` -> [{ value: "some prompt", type: "prompt" }]
 * 2. Single command: `then: "/some-command"` -> [{ value: "/some-command", type: "command" }]
 * 3. Ordered array: `then: ["a", "/b", "c"]` -> [{ value: "a", type: "prompt" }, ...]
 */
export function parseThenChain(markdownContent: string): ThenEntry[] {
  const rawYaml = extractFrontmatter(markdownContent)
  if (rawYaml === null) {
    return []
  }

  let parsed: unknown
  try {
    parsed = yaml.load(rawYaml)
  } catch {
    return []
  }

  if (parsed === null || parsed === undefined || typeof parsed !== "object") {
    return []
  }

  const frontmatter = parsed as Record<string, unknown>
  const thenValue = frontmatter["then"]

  if (thenValue === null || thenValue === undefined) {
    return []
  }

  // Single string value
  if (typeof thenValue === "string") {
    if (thenValue === "") {
      return []
    }
    return [classifyEntry(thenValue)]
  }

  // Array of strings
  if (Array.isArray(thenValue)) {
    if (thenValue.length === 0) {
      return []
    }
    return thenValue
      .filter((entry): entry is string => typeof entry === "string" && entry !== "")
      .map(classifyEntry)
  }

  return []
}
