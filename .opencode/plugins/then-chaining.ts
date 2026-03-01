/**
 * Local development wrapper for the ThenChainingPlugin.
 *
 * Imports from the compiled dist/ output.
 * Run `bun run build` before restarting OpenCode to pick up changes.
 */

import type { Plugin } from "@opencode-ai/plugin"
import { ThenChainingPlugin } from "../../dist/index.js"

export const ThenChainingPluginLocal: Plugin = ThenChainingPlugin()
