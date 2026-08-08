import { createHash } from "node:crypto"
import {
  chmodSync,
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  rmdirSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from "node:fs"
import { dirname, join, relative, resolve, sep } from "node:path"
import { fileURLToPath } from "node:url"

import { RETIRED_FILES } from "./retired-files.js"

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const PLUGIN_PACKAGE = "@toady00/open-mardi-gras"
const WORKFLOW_DIRECTORIES = ["agents", "commands", "skills"] as const

export const MANIFEST_FILENAME = ".omg-manifest.json"
export const MANIFEST_SCHEMA_VERSION = 1

function collectRelativeFiles(root: string, currentDir = root): string[] {
  const entries = readdirSync(currentDir, { withFileTypes: true })
  const files: string[] = []

  for (const entry of entries) {
    const fullPath = join(currentDir, entry.name)

    if (entry.isDirectory()) {
      files.push(...collectRelativeFiles(root, fullPath))
      continue
    }

    if (entry.isFile()) {
      files.push(fullPath.slice(root.length + 1))
    }
  }

  return files.sort()
}

export function getWorkflowFiles(sourceRoot = resolve(__dirname, "../../opencode")): string[] {
  return WORKFLOW_DIRECTORIES.flatMap((directory) =>
    collectRelativeFiles(join(sourceRoot, directory)).map((file) => join(directory, file)),
  ).sort()
}

export function copyWorkflowFile(sourceRoot: string, destRoot: string, file: string): void {
  const src = join(sourceRoot, file)
  const dest = join(destRoot, file)

  mkdirSync(dirname(dest), { recursive: true })
  copyFileSync(src, dest)
  if (file.endsWith(".sh")) chmodSync(dest, statSync(dest).mode | 0o111)
}

export interface InstallManifest {
  schemaVersion: number
  package: string
  version: string
  files: Record<string, string>
}

export interface KeptFile {
  file: string
  /** True when we ship a different version than the one recorded as installed. */
  upstreamChanged: boolean
  reason: "modified" | "irregular"
}

export interface InstallPlan {
  copy: string[]
  keep: KeptFile[]
}

export interface PrunePlan {
  remove: string[]
  keep: string[]
}

/**
 * Setup only ever touches files inside the directories it installs, and never a
 * path that tries to climb out of them. Every removal is filtered through this.
 */
export function isManagedPath(file: string): boolean {
  if (file.length === 0) return false
  const segments = file.split(/[\\/]/)
  if (segments.includes("..") || segments.includes(".")) return false
  return WORKFLOW_DIRECTORIES.some((directory) => segments[0] === directory && segments.length > 1)
}

function safeLstat(path: string): ReturnType<typeof lstatSync> | undefined {
  try {
    return lstatSync(path)
  } catch {
    return undefined
  }
}

/** sha256 of a regular file, or undefined when it is missing or not a regular file. */
export function hashFile(path: string): string | undefined {
  const stats = safeLstat(path)
  if (stats === undefined || !stats.isFile()) return undefined
  try {
    return createHash("sha256").update(readFileSync(path)).digest("hex")
  } catch {
    return undefined
  }
}

/**
 * Reads the install manifest. Returns undefined when it is absent, unreadable,
 * malformed, or written by a newer schema — in every one of those cases we do
 * not know what we installed, so nothing may be removed on its authority.
 */
export function readManifest(destRoot: string): InstallManifest | undefined {
  let parsed: unknown
  try {
    parsed = JSON.parse(readFileSync(join(destRoot, MANIFEST_FILENAME), "utf-8")) as unknown
  } catch {
    return undefined
  }

  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return undefined
  const candidate = parsed as Record<string, unknown>
  const { schemaVersion, files } = candidate
  if (typeof schemaVersion !== "number" || schemaVersion > MANIFEST_SCHEMA_VERSION) return undefined
  if (files === null || typeof files !== "object" || Array.isArray(files)) return undefined

  const entries: Record<string, string> = {}
  for (const [file, hash] of Object.entries(files as Record<string, unknown>)) {
    if (typeof hash === "string") entries[file] = hash
  }

  return {
    schemaVersion,
    package: typeof candidate.package === "string" ? candidate.package : PLUGIN_PACKAGE,
    version: typeof candidate.version === "string" ? candidate.version : "unknown",
    files: entries,
  }
}

export function writeManifest(
  destRoot: string,
  version: string,
  files: Record<string, string>,
): void {
  const manifest: InstallManifest = {
    schemaVersion: MANIFEST_SCHEMA_VERSION,
    package: PLUGIN_PACKAGE,
    version,
    files: Object.fromEntries(Object.entries(files).sort(([a], [b]) => (a < b ? -1 : 1))),
  }
  mkdirSync(destRoot, { recursive: true })
  writeFileSync(join(destRoot, MANIFEST_FILENAME), `${JSON.stringify(manifest, null, 2)}\n`)
}

/**
 * Decides, per shipped file, whether to write it or leave what is there.
 * A local modification is measured against what we last installed, never against
 * what we are shipping — so an edit is preserved whether or not we changed the
 * file too, and only the case that withholds a real update is reported loudly.
 */
export function planInstall(options: {
  sourceRoot: string
  destRoot: string
  shipped: string[]
  previous: InstallManifest | undefined
  force: boolean
}): InstallPlan {
  const { sourceRoot, destRoot, shipped, previous, force } = options
  const copy: string[] = []
  const keep: KeptFile[] = []

  for (const file of shipped) {
    const destPath = join(destRoot, file)
    const stats = safeLstat(destPath)

    // Never write through a symlink or over a directory.
    if (stats !== undefined && !stats.isFile()) {
      keep.push({ file, upstreamChanged: false, reason: "irregular" })
      continue
    }
    // Missing means restore, not conflict. Force always writes.
    if (stats === undefined || force) {
      copy.push(file)
      continue
    }

    const installedHash = previous?.files[file]
    // No record of installing it: the pre-manifest run, which overwrites.
    if (installedHash === undefined) {
      copy.push(file)
      continue
    }

    const currentHash = hashFile(destPath)
    if (currentHash === installedHash) {
      copy.push(file)
      continue
    }

    keep.push({
      file,
      upstreamChanged: hashFile(join(sourceRoot, file)) !== installedHash,
      reason: "modified",
    })
  }

  return { copy, keep }
}

/**
 * Files we installed before and no longer ship. With a manifest that is exact;
 * without one it falls back to the paths retired across released versions.
 */
export function computeOrphans(
  previous: InstallManifest | undefined,
  shipped: string[],
  retired: Readonly<Record<string, readonly string[]>> = RETIRED_FILES,
): string[] {
  const shippedFiles = new Set(shipped)
  const candidates = previous === undefined ? Object.keys(retired) : Object.keys(previous.files)
  return candidates.filter((file) => !shippedFiles.has(file) && isManagedPath(file)).sort()
}

/**
 * Removal is allowed only when the bytes on disk are ones we published. Anything
 * else is someone's work and is kept until they ask for it to go with --force.
 */
export function planPrune(options: {
  destRoot: string
  orphans: string[]
  previous: InstallManifest | undefined
  force: boolean
  retired?: Readonly<Record<string, readonly string[]>>
}): PrunePlan {
  const { destRoot, orphans, previous, force, retired = RETIRED_FILES } = options
  const remove: string[] = []
  const keep: string[] = []

  for (const file of orphans) {
    if (!isManagedPath(file)) continue
    const destPath = join(destRoot, file)
    const stats = safeLstat(destPath)
    if (stats === undefined) continue
    if (!stats.isFile()) {
      keep.push(file)
      continue
    }
    if (force) {
      remove.push(file)
      continue
    }

    const installedHash = previous?.files[file]
    const known = installedHash === undefined ? (retired[file] ?? []) : [installedHash]
    const currentHash = hashFile(destPath)
    if (currentHash !== undefined && known.includes(currentHash)) remove.push(file)
    else keep.push(file)
  }

  return { remove, keep }
}

/** Deletes planned files. A failure is reported and never fails the run. */
export function removeFiles(destRoot: string, files: string[]): { removed: string[]; failed: string[] } {
  const removed: string[] = []
  const failed: string[] = []
  for (const file of files) {
    try {
      unlinkSync(join(destRoot, file))
      removed.push(file)
    } catch {
      failed.push(file)
    }
  }
  return { removed, failed }
}

/** Removes directories left empty by pruning, never the managed roots themselves. */
export function pruneEmptyDirectories(destRoot: string): string[] {
  const removed: string[] = []

  const walk = (current: string, isRoot: boolean): void => {
    let entries
    try {
      entries = readdirSync(current, { withFileTypes: true })
    } catch {
      return
    }
    for (const entry of entries) {
      if (entry.isDirectory()) walk(join(current, entry.name), false)
    }
    if (isRoot) return
    try {
      if (readdirSync(current).length === 0) {
        rmdirSync(current)
        removed.push(relative(destRoot, current).split(sep).join("/"))
      }
    } catch {
      // A directory we cannot remove is left alone.
    }
  }

  for (const directory of WORKFLOW_DIRECTORIES) {
    const root = join(destRoot, directory)
    if (existsSync(root)) walk(root, true)
  }

  return removed
}

function isConfiguredPlugin(entry: unknown): boolean {
  const packageName: unknown = Array.isArray(entry) ? (entry as unknown[])[0] : entry
  return (
    typeof packageName === "string" &&
    (packageName === PLUGIN_PACKAGE || packageName.startsWith(`${PLUGIN_PACKAGE}@`))
  )
}

function findStringEnd(source: string, start: number): number {
  let escaped = false
  for (let index = start + 1; index < source.length; index++) {
    if (!escaped && source[index] === '"') return index
    escaped = !escaped && source[index] === "\\"
    if (source[index] !== "\\") escaped = false
  }
  throw new Error("unterminated JSON string")
}

function findTopLevelProperty(source: string, name: string): { keyStart: number; valueStart: number } {
  let depth = 0
  for (let index = 0; index < source.length; index++) {
    const character = source[index]
    if (character === '"') {
      const end = findStringEnd(source, index)
      if (depth === 1 && JSON.parse(source.slice(index, end + 1)) === name) {
        let colon = end + 1
        while (/\s/.test(source[colon] ?? "")) colon++
        if (source[colon] === ":") {
          let valueStart = colon + 1
          while (/\s/.test(source[valueStart] ?? "")) valueStart++
          return { keyStart: index, valueStart }
        }
      }
      index = end
    } else if (character === "{" || character === "[") {
      depth++
    } else if (character === "}" || character === "]") {
      depth--
    }
  }
  throw new Error(`top-level "${name}" property was not found`)
}

function findArrayEnd(source: string, start: number): number {
  let depth = 0
  for (let index = start; index < source.length; index++) {
    const character = source[index]
    if (character === '"') {
      index = findStringEnd(source, index)
    } else if (character === "[") {
      depth++
    } else if (character === "]" && --depth === 0) {
      return index
    }
  }
  throw new Error("plugin array was not closed")
}

function addPluginToSource(source: string, config: Record<string, unknown>): string {
  const serializedPlugin = JSON.stringify(PLUGIN_PACKAGE)
  const plugins = config.plugin
  if (Array.isArray(plugins)) {
    const { valueStart } = findTopLevelProperty(source, "plugin")
    const arrayEnd = findArrayEnd(source, valueStart)
    const inside = source.slice(valueStart + 1, arrayEnd)
    if (inside.trim() === "") {
      return `${source.slice(0, valueStart + 1)}${serializedPlugin}${source.slice(valueStart + 1)}`
    }

    const trailingWhitespace = inside.match(/\s*$/)?.[0] ?? ""
    const insertionAt = arrayEnd - trailingWhitespace.length
    const newline = source.includes("\r\n") ? "\r\n" : "\n"
    let separator = ", "
    if (inside.includes("\n")) {
      const currentLine = source.slice(source.lastIndexOf("\n", insertionAt - 1) + 1, insertionAt)
      const indentation = currentLine.match(/^\s*/)?.[0] ?? ""
      separator = `,${newline}${indentation}`
    }
    return `${source.slice(0, insertionAt)}${separator}${serializedPlugin}${source.slice(insertionAt)}`
  }

  const objectEnd = source.lastIndexOf("}")
  const beforeEnd = source.slice(0, objectEnd)
  const trailingWhitespace = beforeEnd.match(/\s*$/)?.[0] ?? ""
  const insertionAt = objectEnd - trailingWhitespace.length
  const hasProperties = Object.keys(config).length > 0
  if (!source.includes("\n")) {
    const separator = hasProperties ? ", " : ""
    return `${source.slice(0, insertionAt)}${separator}"plugin": [${serializedPlugin}]${source.slice(insertionAt)}`
  }

  const newline = source.includes("\r\n") ? "\r\n" : "\n"
  let indentation = "  "
  if (hasProperties) {
    const firstKey = Object.keys(config)[0]
    const { keyStart } = findTopLevelProperty(source, firstKey)
    indentation = source.slice(source.lastIndexOf("\n", keyStart - 1) + 1, keyStart)
  }
  const separator = hasProperties ? "," : ""
  return `${source.slice(0, insertionAt)}${separator}${newline}${indentation}"plugin": [${serializedPlugin}]${source.slice(insertionAt)}`
}

export function configurePlugin(destRoot: string): "added" | "present" {
  const configPath = join(destRoot, "opencode.json")
  let config: Record<string, unknown> = {}
  let source: string | undefined

  try {
    source = readFileSync(configPath, "utf-8")
    const parsed = JSON.parse(source) as unknown
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("the top-level value must be a JSON object")
    }
    config = parsed as Record<string, unknown>
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
      const message = error instanceof Error ? error.message : String(error)
      throw new Error(`Cannot update ${configPath}: ${message}`)
    }
  }

  const plugins = config.plugin
  if (plugins !== undefined && !Array.isArray(plugins)) {
    throw new Error(`Cannot update ${configPath}: "plugin" must be an array`)
  }

  const pluginEntries: unknown[] = Array.isArray(plugins) ? (plugins as unknown[]) : []
  const pluginAlreadyConfigured = pluginEntries.some(isConfiguredPlugin)
  if (pluginAlreadyConfigured) return "present"

  mkdirSync(destRoot, { recursive: true })
  const updatedSource =
    source === undefined
      ? `${JSON.stringify(
          { $schema: "https://opencode.ai/config.json", plugin: [PLUGIN_PACKAGE] },
          null,
          2,
        )}\n`
      : addPluginToSource(source, config)
  writeFileSync(configPath, updatedSource)
  return "added"
}

function reportPreserved(kept: KeptFile[], keptOrphans: string[]): void {
  const withheld = kept.filter((entry) => entry.reason === "modified" && entry.upstreamChanged)
  const alreadyCurrent = kept.filter((entry) => entry.reason === "modified" && !entry.upstreamChanged)
  const irregular = kept.filter((entry) => entry.reason === "irregular")

  if (alreadyCurrent.length > 0) {
    console.log(
      `Preserved ${alreadyCurrent.length} locally modified file(s); no newer version was available.`,
    )
  }

  if (withheld.length > 0) {
    console.warn(`\nKept ${withheld.length} locally modified file(s) — a NEWER version was not installed:`)
    for (const entry of withheld) console.warn(`  .opencode/${entry.file}`)
  }

  if (keptOrphans.length > 0) {
    console.warn(`\nKept ${keptOrphans.length} retired file(s) that no longer ship but were modified locally:`)
    for (const file of keptOrphans) console.warn(`  .opencode/${file}`)
  }

  if (irregular.length > 0) {
    console.warn(`\nSkipped ${irregular.length} path(s) that are not regular files:`)
    for (const entry of irregular) console.warn(`  .opencode/${entry.file}`)
  }

  if (withheld.length > 0 || keptOrphans.length > 0) {
    console.warn("\nReview these, then re-run with --force to replace them with the shipped versions.")
  }
}

export function setup(options: { force?: boolean } = {}): void {
  const force = options.force ?? false
  const sourceRoot = resolve(__dirname, "../../opencode")
  const destRoot = resolve(process.cwd(), ".opencode")
  const shipped = getWorkflowFiles(sourceRoot)
  const previous = readManifest(destRoot)

  // Read package version
  let version = "unknown"
  try {
    const pkgPath = resolve(__dirname, "../../package.json")
    const pkg = JSON.parse(readFileSync(pkgPath, "utf-8")) as { version?: string }
    version = pkg.version ?? "unknown"
  } catch {
    // If package.json can't be read, continue with "unknown"
  }

  console.log("Setting up Open Mardi Gras workflow files...\n")

  const preexisting = shipped.some((file) => existsSync(join(destRoot, file)))
  if (previous === undefined && preexisting && !force) {
    console.log("  No install manifest found — this is the first run that records one.")
    console.log("  Existing instrument files are replaced this once; later runs preserve")
    console.log("  local modifications and report them instead.\n")
  }

  const plan = planInstall({ sourceRoot, destRoot, shipped, previous, force })

  const installed: Record<string, string> = {}
  const errors: string[] = []
  for (const file of plan.copy) {
    try {
      copyWorkflowFile(sourceRoot, destRoot, file)
      const hash = hashFile(join(destRoot, file))
      if (hash !== undefined) installed[file] = hash
      console.log(`  copied: .opencode/${file}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`  FAILED: .opencode/${file} — ${msg}`)
      errors.push(file)
    }
  }

  // A kept file keeps the hash we last installed, not the one on disk — recording
  // the modified bytes would make the edit look resolved and overwrite it next run.
  for (const kept of plan.keep) {
    const carried = previous?.files[kept.file]
    if (carried !== undefined) installed[kept.file] = carried
  }

  console.log(`\n@toady00/open-mardi-gras v${version}`)
  console.log(`Copied ${plan.copy.length - errors.length} files to .opencode/`)

  if (errors.length > 0) {
    writeManifest(destRoot, version, installed)
    console.error(`\nFailed to copy ${errors.length} file(s). Re-run setup or copy them manually.`)
    console.error("Retired files were not removed because this install is incomplete.")
    process.exit(1)
  }

  const orphans = computeOrphans(previous, shipped)
  const prunePlan = planPrune({ destRoot, orphans, previous, force })
  const { removed, failed } = removeFiles(destRoot, prunePlan.remove)
  for (const file of removed) console.log(`  removed: .opencode/${file}`)
  pruneEmptyDirectories(destRoot)
  writeManifest(destRoot, version, installed)

  if (removed.length > 0) console.log(`Removed ${removed.length} retired file(s) no longer shipped.`)
  if (failed.length > 0) {
    console.warn(`\nCould not remove ${failed.length} retired file(s):`)
    for (const file of failed) console.warn(`  .opencode/${file}`)
  }

  reportPreserved(plan.keep, prunePlan.keep)

  try {
    const pluginStatus = configurePlugin(destRoot)
    console.log(
      pluginStatus === "added"
        ? `Added ${PLUGIN_PACKAGE} to .opencode/opencode.json`
        : `${PLUGIN_PACKAGE} is already configured in .opencode/opencode.json`,
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.error(`\nFailed to configure the plugin: ${message}`)
    process.exit(1)
  }

  console.log(`\nNext steps:`)
  console.log(`  1. Restart or open opencode in this project.`)
  console.log(`  2. Run /omg-onboard {solo|centralized|satellite}.`)
  console.log(`  3. Follow the onboarder's instructions to finish and verify the wiring.`)
}

function main(): void {
  const args = process.argv.slice(2)
  const command = args[0]

  if (command === "setup") {
    setup({ force: args.includes("--force") })
  } else {
    console.error("Usage: @toady00/open-mardi-gras setup [--force]")
    console.error("")
    console.error("Commands:")
    console.error("  setup  Install workflow instruments and configure the plugin")
    console.error("")
    console.error("Options:")
    console.error("  --force  Replace locally modified files and remove retired ones")
    console.error("           that were modified. Without it, both are kept and reported.")
    process.exit(1)
  }
}

if (process.argv[1] !== undefined && realpathSync(resolve(process.argv[1])) === __filename) {
  main()
}
