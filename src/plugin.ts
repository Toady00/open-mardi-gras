/**
 * Default entry point for OpenCode npm plugin loading.
 *
 * OpenCode iterates all exports and calls each function as fn(pluginInput).
 * This module exports pre-instantiated Plugin values (factory functions
 * already called with default config) so they satisfy the Plugin type
 * signature directly.
 *
 * For the library API with configurable factory functions, import from
 * "@toady00/open-mardi-gras/api" instead.
 */

import type { Plugin } from "@opencode-ai/plugin"
import { BeadsPlugin } from "./plugins/beads.js"
import { ThenChainingPlugin } from "./plugins/then-chaining.js"

export const ThenChaining: Plugin = ThenChainingPlugin()
export const Beads: Plugin = BeadsPlugin()
