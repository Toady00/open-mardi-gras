import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

/** All files to copy from the package's opencode/ tree, relative to that root. */
const FILES_TO_COPY = [
  "commands/omg-work.md",
  "commands/omg-spec.md",
  "commands/omg-spec-track.md",
  "commands/omg-spec-refine.md",
  "commands/omg-decompose.md",
  "commands/omg-status.md",
  "commands/omg-cleanup.md",
  "agents/omg-build.md",
  "agents/omg-spec-writer.md",
  "agents/omg-reviewer.md",
  "agents/omg-decomposer.md",
  "skills/omg-commands/SKILL.md",
  "skills/omg-epics/SKILL.md",
  "prompts/omg-workflow.md",
]

function setup(): void {
  const sourceRoot = resolve(__dirname, "../../opencode")
  const destRoot = resolve(process.cwd(), ".opencode")

  console.log("Setting up Open Mardi Gras workflow files...\n")

  let copied = 0
  const errors: string[] = []
  for (const file of FILES_TO_COPY) {
    const src = join(sourceRoot, file)
    const dest = join(destRoot, file)

    try {
      mkdirSync(dirname(dest), { recursive: true })
      copyFileSync(src, dest)
      console.log(`  copied: .opencode/${file}`)
      copied++
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`  FAILED: .opencode/${file} — ${msg}`)
      errors.push(file)
    }
  }

  // Write .workflow.yaml
  const workflowPath = resolve(process.cwd(), ".workflow.yaml")
  writeFileSync(workflowPath, "specs:\n  directory: docs/specs\n", "utf-8")
  console.log(`  wrote:  .workflow.yaml`)

  // Read package version
  let version = "unknown"
  try {
    const pkgPath = resolve(__dirname, "../../package.json")
    const pkg = JSON.parse(readFileSync(pkgPath, "utf-8")) as { version?: string }
    version = pkg.version ?? "unknown"
  } catch {
    // If package.json can't be read, continue with "unknown"
  }

  console.log(`\n@toady00/open-mardi-gras v${version}`)
  console.log(`Copied ${copied} files to .opencode/`)

  if (errors.length > 0) {
    console.error(`\nFailed to copy ${errors.length} file(s). Re-run setup or copy them manually.`)
    process.exit(1)
  }

  console.log(`\nNext steps:`)
  console.log(`  Add BeadsPlugin() to your opencode config:`)
  console.log(``)
  console.log(`    import { BeadsPlugin } from '@toady00/open-mardi-gras'`)
  console.log(`    export default { plugins: [BeadsPlugin()] }`)
}

function main(): void {
  const command = process.argv[2]

  if (command === "setup") {
    setup()
  } else {
    console.error("Usage: @toady00/open-mardi-gras setup")
    console.error("")
    console.error("Commands:")
    console.error("  setup  Copy workflow files to .opencode/ and create .workflow.yaml")
    process.exit(1)
  }
}

main()
