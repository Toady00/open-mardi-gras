#!/usr/bin/env node
/**
 * Regenerates src/cli/retired-files.ts.
 *
 * A retired file is one that some released version of this package installed
 * under .opencode/ and the current tree no longer ships. Setup removes them, but
 * only when the copy on disk still matches one of the exact contents we
 * published — so we need every historical hash for each path.
 *
 * Run from the repo root: node tools/generate-retired-files.mjs
 */
import { execFileSync } from "node:child_process"
import { createHash } from "node:crypto"
import { writeFileSync } from "node:fs"

const MANAGED = ["agents/", "commands/", "skills/"]
const OUTPUT = "src/cli/retired-files.ts"

const git = (args, encoding = "utf-8") =>
  execFileSync("git", args, { encoding, maxBuffer: 64 * 1024 * 1024 })

const listTree = (ref) =>
  git(["ls-tree", "-r", "--name-only", ref, "--", "opencode/"])
    .split("\n")
    .filter(Boolean)

const tags = git(["tag"]).split("\n").filter(Boolean)
if (tags.length === 0) throw new Error("no git tags found — cannot derive released file sets")

const shipped = new Set(listTree("HEAD"))
const everShipped = new Set(tags.flatMap((tag) => listTree(tag)))

const retired = [...everShipped]
  .filter((path) => !shipped.has(path))
  .map((path) => path.replace(/^opencode\//, ""))
  .filter((path) => MANAGED.some((dir) => path.startsWith(dir)))
  .sort()

const entries = retired.map((path) => {
  const hashes = new Set()
  for (const tag of tags) {
    const spec = `${tag}:opencode/${path}`
    try {
      execFileSync("git", ["cat-file", "-e", spec], { stdio: "ignore" })
    } catch {
      continue // the file did not exist at this tag
    }
    const content = git(["cat-file", "-p", spec], "buffer")
    hashes.add(createHash("sha256").update(content).digest("hex"))
  }
  if (hashes.size === 0) throw new Error(`no historical content found for ${path}`)
  return [path, [...hashes].sort()]
})

const body = entries
  .map(([path, hashes]) => {
    const lines = hashes.map((hash) => `    "${hash}",`).join("\n")
    return `  ${JSON.stringify(path)}: [\n${lines}\n  ],`
  })
  .join("\n")

writeFileSync(
  OUTPUT,
  `/**
 * Instrument files that setup installed under a previous release and no longer
 * ships. Setup removes them, but only when the file on disk still matches one of
 * the exact contents we published — a locally modified copy is kept and reported
 * instead, so no customization is destroyed silently.
 *
 * This list only matters for installs made before the install manifest existed.
 * Once \`.opencode/.omg-manifest.json\` is present the manifest is authoritative
 * and this list is not consulted.
 *
 * Paths are limited to the directories setup manages (agents, commands, skills).
 * \`opencode/prompts/\` was never installed by setup, so removing it is not ours.
 *
 * Generated — do not edit by hand.
 * Regenerate with: node tools/generate-retired-files.mjs
 */
export const RETIRED_FILES: Readonly<Record<string, readonly string[]>> = {
${body}
}
`,
)

console.log(`wrote ${OUTPUT}: ${entries.length} paths, ${entries.reduce((n, [, h]) => n + h.length, 0)} hashes`)
