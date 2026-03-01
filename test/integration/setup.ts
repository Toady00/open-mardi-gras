import { mkdtemp, writeFile, mkdir, cp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, "..", "..");

const fixturesDir = join(repoRoot, "test", "integration", "fixtures", "commands");

const OPENCODE_CONFIG = {
  $schema: "https://opencode.ai/config.json",
  model: "anthropic/claude-haiku-4-5",
  server: { port: 4200 },
};

const PACKAGE_JSON = {
  name: "omg-verify",
  private: true,
};

function buildPluginSource(): string {
  const distPath = join(repoRoot, "dist", "index.js");
  return [
    `import { ThenChainingPlugin } from "${distPath}"`,
    `export default ThenChainingPlugin({ maxDepth: 3, syntheticMessageBehavior: "remove" })`,
    "",
  ].join("\n");
}

export async function setup(): Promise<{ tmpDir: string; cleanup: () => void }> {
  const tmpDir = await mkdtemp(join(tmpdir(), "omg-verify-"));

  // Write opencode.json
  await writeFile(
    join(tmpDir, "opencode.json"),
    JSON.stringify(OPENCODE_CONFIG, null, 2) + "\n",
  );

  // Write package.json
  await writeFile(
    join(tmpDir, "package.json"),
    JSON.stringify(PACKAGE_JSON, null, 2) + "\n",
  );

  // Create .opencode/plugins/ and write the plugin file
  const pluginsDir = join(tmpDir, ".opencode", "plugins");
  await mkdir(pluginsDir, { recursive: true });
  await writeFile(join(pluginsDir, "then-chaining.ts"), buildPluginSource());

  // Create .opencode/commands/ and copy fixture command files
  const commandsDir = join(tmpDir, ".opencode", "commands");
  await mkdir(commandsDir, { recursive: true });
  await cp(fixturesDir, commandsDir, { recursive: true });

  const cleanup = () => {
    rm(tmpDir, { recursive: true, force: true }).catch(() => {
      // Best-effort cleanup
    });
  };

  return { tmpDir, cleanup };
}

// When run standalone, create the temp dir and print its path
const isMainModule =
  process.argv[1] === __filename ||
  process.argv[1] === fileURLToPath(import.meta.url);

if (isMainModule) {
  const { tmpDir } = await setup();
  console.log(tmpDir);
}
