import { createHash } from "node:crypto"
import { existsSync } from "node:fs"
import { mkdtemp, mkdir, readFile, rm, stat, symlink, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import { dirname, join } from "node:path"
import { afterEach, describe, expect, it } from "bun:test"

import { RETIRED_FILES } from "../src/cli/retired-files"
import {
  MANIFEST_FILENAME,
  MANIFEST_SCHEMA_VERSION,
  computeOrphans,
  configurePlugin,
  copyWorkflowFile,
  getWorkflowFiles,
  isManagedPath,
  planInstall,
  planPrune,
  pruneEmptyDirectories,
  readManifest,
  writeManifest,
} from "../src/cli/setup"
import type { InstallManifest } from "../src/cli/setup"

const tempDirs: string[] = []

afterEach(async () => {
  await Promise.all(
    tempDirs.splice(0).map((dir) => rm(dir, { recursive: true, force: true })),
  )
})

describe("getWorkflowFiles", () => {
  it("returns every file under opencode recursively in stable order", async () => {
    const root = await mkdtemp(join(tmpdir(), "omg-setup-"))
    tempDirs.push(root)

    await mkdir(join(root, "commands"), { recursive: true })
    await mkdir(join(root, "agents"), { recursive: true })
    await mkdir(join(root, "skills", "omg-commands"), { recursive: true })
    await mkdir(join(root, "unrelated"), { recursive: true })

    await writeFile(join(root, "commands", "omg-zeta.md"), "zeta\n")
    await writeFile(join(root, "commands", "omg-alpha.md"), "alpha\n")
    await writeFile(join(root, "agents", "omg-build.md"), "build\n")
    await writeFile(join(root, "skills", "omg-commands", "SKILL.md"), "skill\n")
    await writeFile(join(root, "unrelated", "not-an-instrument.md"), "ignore\n")

    expect(getWorkflowFiles(root)).toEqual([
      "agents/omg-build.md",
      "commands/omg-alpha.md",
      "commands/omg-zeta.md",
      "skills/omg-commands/SKILL.md",
    ])
  })
})

describe("copyWorkflowFile", () => {
  it("makes copied shell scripts executable", async () => {
    const root = await mkdtemp(join(tmpdir(), "omg-setup-"))
    tempDirs.push(root)
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "destination")
    const file = join("skills", "example", "script.sh")
    await mkdir(join(sourceRoot, "skills", "example"), { recursive: true })
    await writeFile(join(sourceRoot, file), "#!/bin/sh\n", { mode: 0o600 })

    copyWorkflowFile(sourceRoot, destRoot, file)

    expect((await stat(join(destRoot, file))).mode & 0o111).toBe(0o111)
  })

  it("does not make copied non-shell files executable", async () => {
    const root = await mkdtemp(join(tmpdir(), "omg-setup-"))
    tempDirs.push(root)
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "destination")
    const file = join("skills", "example", "SKILL.md")
    await mkdir(join(sourceRoot, "skills", "example"), { recursive: true })
    await writeFile(join(sourceRoot, file), "# Example\n", { mode: 0o600 })

    copyWorkflowFile(sourceRoot, destRoot, file)

    expect((await stat(join(destRoot, file))).mode & 0o111).toBe(0)
  })
})

describe("configurePlugin", () => {
  it("creates .opencode/opencode.json with the plugin", async () => {
    const root = await mkdtemp(join(tmpdir(), "omg-setup-"))
    tempDirs.push(root)
    const destRoot = join(root, ".opencode")

    expect(configurePlugin(destRoot)).toBe("added")

    expect(JSON.parse(await readFile(join(destRoot, "opencode.json"), "utf-8"))).toEqual({
      $schema: "https://opencode.ai/config.json",
      plugin: ["@toady00/open-mardi-gras"],
    })
  })

  it("preserves existing config while adding the plugin", async () => {
    const root = await mkdtemp(join(tmpdir(), "omg-setup-"))
    tempDirs.push(root)
    const destRoot = join(root, ".opencode")
    await mkdir(destRoot)
    const original = `{
  "$schema": "https://opencode.ai/config.json",
  "disabled_providers": ["amazon-bedrock", "synthetic"],
  "agent": {
    "build":       {"model": "openai/gpt-5.6-terra-fast"},
    "omg-builder": {"model": "openai/gpt-5.6-terra-fast"}
  }
}
`
    await writeFile(join(destRoot, "opencode.json"), original)

    expect(configurePlugin(destRoot)).toBe("added")

    expect(await readFile(join(destRoot, "opencode.json"), "utf-8")).toBe(`{
  "$schema": "https://opencode.ai/config.json",
  "disabled_providers": ["amazon-bedrock", "synthetic"],
  "agent": {
    "build":       {"model": "openai/gpt-5.6-terra-fast"},
    "omg-builder": {"model": "openai/gpt-5.6-terra-fast"}
  },
  "plugin": ["@toady00/open-mardi-gras"]
}
`)
  })

  it("preserves formatting while appending to an existing plugin array", async () => {
    const root = await mkdtemp(join(tmpdir(), "omg-setup-"))
    tempDirs.push(root)
    const destRoot = join(root, ".opencode")
    const original = `{
  "plugin": [
    "another-plugin"
  ],
  "agent": {"build": {"model": "provider/model"}}
}
`
    await mkdir(destRoot)
    await writeFile(join(destRoot, "opencode.json"), original)

    expect(configurePlugin(destRoot)).toBe("added")
    expect(await readFile(join(destRoot, "opencode.json"), "utf-8")).toBe(`{
  "plugin": [
    "another-plugin",
    "@toady00/open-mardi-gras"
  ],
  "agent": {"build": {"model": "provider/model"}}
}
`)
  })

  it("does not duplicate an existing pinned plugin entry", async () => {
    const root = await mkdtemp(join(tmpdir(), "omg-setup-"))
    tempDirs.push(root)
    const destRoot = join(root, ".opencode")
    const config = {
      $schema: "https://opencode.ai/config.json",
      plugin: ["@toady00/open-mardi-gras@0.4.2"],
    }
    await mkdir(destRoot)
    await writeFile(join(destRoot, "opencode.json"), JSON.stringify(config))

    expect(configurePlugin(destRoot)).toBe("present")
    expect(JSON.parse(await readFile(join(destRoot, "opencode.json"), "utf-8"))).toEqual(config)
  })
})

const sha256 = (content: string): string => createHash("sha256").update(content).digest("hex")

async function scratch(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "omg-setup-"))
  tempDirs.push(root)
  return root
}

/** Writes a file under a root, creating parents. Returns its sha256. */
async function put(root: string, file: string, content: string): Promise<string> {
  await mkdir(join(root, dirname(file)), { recursive: true })
  await writeFile(join(root, file), content)
  return sha256(content)
}

const manifestOf = (files: Record<string, string>): InstallManifest => ({
  schemaVersion: 1,
  package: "@toady00/open-mardi-gras",
  version: "1.0.0",
  files,
})

describe("isManagedPath", () => {
  it("accepts files inside the directories setup installs", () => {
    expect(isManagedPath("agents/omg-builder.md")).toBe(true)
    expect(isManagedPath("skills/omg-misc/scripts/x.sh")).toBe(true)
  })

  it("rejects anything outside them, and any attempt to climb out", () => {
    expect(isManagedPath("opencode.json")).toBe(false)
    expect(isManagedPath("plugins/evil.ts")).toBe(false)
    expect(isManagedPath("agents")).toBe(false)
    expect(isManagedPath("agents/../../etc/passwd")).toBe(false)
    expect(isManagedPath("skills/./x.md")).toBe(false)
    expect(isManagedPath("")).toBe(false)
  })
})

describe("readManifest", () => {
  it("returns undefined when absent, so nothing may be removed on its authority", async () => {
    expect(readManifest(await scratch())).toBeUndefined()
  })

  it("returns undefined for unparseable content rather than guessing", async () => {
    const root = await scratch()
    await writeFile(join(root, MANIFEST_FILENAME), "{ not json")
    expect(readManifest(root)).toBeUndefined()
  })

  it("returns undefined for a newer schema version", async () => {
    const root = await scratch()
    await writeFile(
      join(root, MANIFEST_FILENAME),
      JSON.stringify({ schemaVersion: MANIFEST_SCHEMA_VERSION + 1, files: { "agents/a.md": "x" } }),
    )
    expect(readManifest(root)).toBeUndefined()
  })

  it("round-trips what writeManifest produced, sorted and without a timestamp", async () => {
    const root = await scratch()
    writeManifest(root, "9.9.9", { "commands/z.md": "hz", "agents/a.md": "ha" })

    const raw = JSON.parse(await readFile(join(root, MANIFEST_FILENAME), "utf-8")) as Record<
      string,
      unknown
    >
    expect(Object.keys(raw)).toEqual(["schemaVersion", "package", "version", "files"])
    expect(Object.keys(raw.files as Record<string, string>)).toEqual([
      "agents/a.md",
      "commands/z.md",
    ])
    expect(readManifest(root)?.files).toEqual({ "commands/z.md": "hz", "agents/a.md": "ha" })
  })
})

describe("planInstall", () => {
  it("copies everything when there is no manifest, even over existing files", async () => {
    const root = await scratch()
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "dest")
    await put(sourceRoot, "agents/a.md", "new")
    await put(destRoot, "agents/a.md", "someone's edit")

    const plan = planInstall({
      sourceRoot,
      destRoot,
      shipped: ["agents/a.md"],
      previous: undefined,
      force: false,
    })

    expect(plan.copy).toEqual(["agents/a.md"])
    expect(plan.keep).toEqual([])
  })

  it("copies an unmodified file — the normal upgrade", async () => {
    const root = await scratch()
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "dest")
    await put(sourceRoot, "agents/a.md", "v2")
    const installed = await put(destRoot, "agents/a.md", "v1")

    const plan = planInstall({
      sourceRoot,
      destRoot,
      shipped: ["agents/a.md"],
      previous: manifestOf({ "agents/a.md": installed }),
      force: false,
    })

    expect(plan.copy).toEqual(["agents/a.md"])
  })

  it("restores a tracked file the user deleted, treating absence as no conflict", async () => {
    const root = await scratch()
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "dest")
    await put(sourceRoot, "agents/a.md", "v2")

    const plan = planInstall({
      sourceRoot,
      destRoot,
      shipped: ["agents/a.md"],
      previous: manifestOf({ "agents/a.md": sha256("v1") }),
      force: false,
    })

    expect(plan.copy).toEqual(["agents/a.md"])
  })

  it("keeps a modified file quietly when we ship no newer version", async () => {
    const root = await scratch()
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "dest")
    const shippedHash = await put(sourceRoot, "agents/a.md", "v1")
    await put(destRoot, "agents/a.md", "their customization")

    const plan = planInstall({
      sourceRoot,
      destRoot,
      shipped: ["agents/a.md"],
      previous: manifestOf({ "agents/a.md": shippedHash }),
      force: false,
    })

    expect(plan.copy).toEqual([])
    expect(plan.keep).toEqual([{ file: "agents/a.md", upstreamChanged: false, reason: "modified" }])
  })

  it("keeps a modified file loudly when a newer version is being withheld", async () => {
    const root = await scratch()
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "dest")
    await put(sourceRoot, "agents/a.md", "v2")
    await put(destRoot, "agents/a.md", "their customization")

    const plan = planInstall({
      sourceRoot,
      destRoot,
      shipped: ["agents/a.md"],
      previous: manifestOf({ "agents/a.md": sha256("v1") }),
      force: false,
    })

    expect(plan.keep).toEqual([{ file: "agents/a.md", upstreamChanged: true, reason: "modified" }])
  })

  it("overwrites a modified file only when forced", async () => {
    const root = await scratch()
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "dest")
    await put(sourceRoot, "agents/a.md", "v2")
    await put(destRoot, "agents/a.md", "their customization")

    const plan = planInstall({
      sourceRoot,
      destRoot,
      shipped: ["agents/a.md"],
      previous: manifestOf({ "agents/a.md": sha256("v1") }),
      force: true,
    })

    expect(plan.copy).toEqual(["agents/a.md"])
    expect(plan.keep).toEqual([])
  })

  it("never writes through a symlink standing where a shipped file belongs", async () => {
    const root = await scratch()
    const sourceRoot = join(root, "source")
    const destRoot = join(root, "dest")
    await put(sourceRoot, "agents/a.md", "v2")
    const outside = join(root, "outside.md")
    await writeFile(outside, "must not be touched")
    await mkdir(join(destRoot, "agents"), { recursive: true })
    await symlink(outside, join(destRoot, "agents", "a.md"))

    const plan = planInstall({
      sourceRoot,
      destRoot,
      shipped: ["agents/a.md"],
      previous: undefined,
      force: true,
    })

    expect(plan.copy).toEqual([])
    expect(plan.keep).toEqual([{ file: "agents/a.md", upstreamChanged: false, reason: "irregular" }])
    expect(await readFile(outside, "utf-8")).toBe("must not be touched")
  })
})

describe("computeOrphans", () => {
  it("is what the manifest recorded minus what we now ship", () => {
    const previous = manifestOf({
      "agents/kept.md": "h1",
      "agents/retired.md": "h2",
      "skills/s/gone.md": "h3",
    })
    expect(computeOrphans(previous, ["agents/kept.md"])).toEqual([
      "agents/retired.md",
      "skills/s/gone.md",
    ])
  })

  it("falls back to the retired list when there is no manifest", () => {
    const retired = { "commands/old.md": ["h"], "agents/older.md": ["h"] }
    expect(computeOrphans(undefined, [], retired)).toEqual(["agents/older.md", "commands/old.md"])
  })

  it("never proposes a path outside the directories setup manages", () => {
    const previous = manifestOf({ "opencode.json": "h", "agents/../escape.md": "h" })
    expect(computeOrphans(previous, [])).toEqual([])
  })

  it("leaves a user-authored file alone because setup never installed it", async () => {
    const root = await scratch()
    await put(root, "skills/mine/SKILL.md", "my own skill")
    const previous = manifestOf({ "agents/a.md": "h" })

    const orphans = computeOrphans(previous, [])
    expect(orphans).toEqual(["agents/a.md"])
    expect(orphans).not.toContain("skills/mine/SKILL.md")
  })
})

describe("planPrune", () => {
  it("removes a retired file whose bytes are the ones we installed", async () => {
    const destRoot = await scratch()
    const hash = await put(destRoot, "agents/old.md", "shipped content")

    const plan = planPrune({
      destRoot,
      orphans: ["agents/old.md"],
      previous: manifestOf({ "agents/old.md": hash }),
      force: false,
    })

    expect(plan).toEqual({ remove: ["agents/old.md"], keep: [] })
  })

  it("keeps a retired file the user changed", async () => {
    const destRoot = await scratch()
    await put(destRoot, "agents/old.md", "their edit")

    const plan = planPrune({
      destRoot,
      orphans: ["agents/old.md"],
      previous: manifestOf({ "agents/old.md": sha256("shipped content") }),
      force: false,
    })

    expect(plan).toEqual({ remove: [], keep: ["agents/old.md"] })
  })

  it("removes a modified retired file when forced", async () => {
    const destRoot = await scratch()
    await put(destRoot, "agents/old.md", "their edit")

    const plan = planPrune({
      destRoot,
      orphans: ["agents/old.md"],
      previous: manifestOf({ "agents/old.md": sha256("shipped content") }),
      force: true,
    })

    expect(plan.remove).toEqual(["agents/old.md"])
  })

  it("without a manifest, removes only content matching a published version", async () => {
    const destRoot = await scratch()
    const pristine = await put(destRoot, "agents/pristine.md", "v1 content")
    await put(destRoot, "agents/edited.md", "v1 content, plus mine")
    const retired = {
      "agents/pristine.md": [pristine, sha256("v2 content")],
      "agents/edited.md": [sha256("v1 content")],
    }

    const plan = planPrune({
      destRoot,
      orphans: ["agents/edited.md", "agents/pristine.md"],
      previous: undefined,
      force: false,
      retired,
    })

    expect(plan).toEqual({ remove: ["agents/pristine.md"], keep: ["agents/edited.md"] })
  })

  it("ignores a file that is already gone and refuses to unlink a symlink", async () => {
    const destRoot = await scratch()
    const outside = join(destRoot, "outside.md")
    await writeFile(outside, "keep me")
    await mkdir(join(destRoot, "agents"), { recursive: true })
    await symlink(outside, join(destRoot, "agents", "link.md"))

    const plan = planPrune({
      destRoot,
      orphans: ["agents/missing.md", "agents/link.md"],
      previous: manifestOf({ "agents/missing.md": "h", "agents/link.md": "h" }),
      force: true,
    })

    expect(plan).toEqual({ remove: [], keep: ["agents/link.md"] })
  })
})

describe("pruneEmptyDirectories", () => {
  it("removes directories emptied by pruning but never the managed roots", async () => {
    const destRoot = await scratch()
    await mkdir(join(destRoot, "skills", "retired", "references"), { recursive: true })
    await mkdir(join(destRoot, "agents"), { recursive: true })
    await mkdir(join(destRoot, "commands"), { recursive: true })
    await put(destRoot, "skills/live/SKILL.md", "still here")

    const removed = pruneEmptyDirectories(destRoot)

    expect(removed.sort()).toEqual(["skills/retired", "skills/retired/references"])
    expect(existsSync(join(destRoot, "skills", "live"))).toBe(true)
    expect(existsSync(join(destRoot, "agents"))).toBe(true)
    expect(existsSync(join(destRoot, "commands"))).toBe(true)
  })
})

describe("RETIRED_FILES", () => {
  it("lists only managed paths, each with at least one well-formed hash", () => {
    const entries = Object.entries(RETIRED_FILES)
    expect(entries.length).toBeGreaterThan(0)
    for (const [file, hashes] of entries) {
      expect(isManagedPath(file)).toBe(true)
      expect(hashes.length).toBeGreaterThan(0)
      for (const hash of hashes) expect(hash).toMatch(/^[0-9a-f]{64}$/)
    }
  })

  it("carries no hash of empty content, which would whitelist deleting any empty file", () => {
    const emptyHash = sha256("")
    for (const hashes of Object.values(RETIRED_FILES)) expect(hashes).not.toContain(emptyHash)
  })
})
