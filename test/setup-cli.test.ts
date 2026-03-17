import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { afterEach, describe, expect, it } from "bun:test"

import { getWorkflowFiles } from "../src/cli/setup"

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
    await mkdir(join(root, "prompts"), { recursive: true })

    await writeFile(join(root, "commands", "omg-zeta.md"), "zeta\n")
    await writeFile(join(root, "commands", "omg-alpha.md"), "alpha\n")
    await writeFile(join(root, "agents", "omg-build.md"), "build\n")
    await writeFile(join(root, "skills", "omg-commands", "SKILL.md"), "skill\n")
    await writeFile(join(root, "prompts", "omg-workflow.md"), "prompt\n")

    expect(getWorkflowFiles(root)).toEqual([
      "agents/omg-build.md",
      "commands/omg-alpha.md",
      "commands/omg-zeta.md",
      "prompts/omg-workflow.md",
      "skills/omg-commands/SKILL.md",
    ])
  })
})
