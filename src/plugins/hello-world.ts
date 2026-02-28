import type { Plugin } from "@opencode-ai/plugin"

export interface HelloWorldPluginConfig {
  // Reserved for future configuration options
}

export const HelloWorldPlugin = (_config?: HelloWorldPluginConfig): Plugin => {
  return async ({ client }) => {
    try {
      await client.app.log({
        body: {
          service: "open-mardi-gras",
          level: "info",
          message: "HelloWorldPlugin initialized",
        },
      })
    } catch {
      // Log failure should not prevent plugin from loading
    }

    return {
      // Empty hooks object - this plugin just validates wiring
    }
  }
}
