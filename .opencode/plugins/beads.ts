/**
 * Local development wrapper for the BeadsPlugin.
 *
 * Imports from the compiled dist/ output.
 * Run `bun run build` before restarting OpenCode to pick up changes.
 */

import type { Plugin } from "@opencode-ai/plugin"
import { BeadsPlugin } from "../../dist/index.js"

export const BeadsPluginLocal: Plugin = BeadsPlugin()
