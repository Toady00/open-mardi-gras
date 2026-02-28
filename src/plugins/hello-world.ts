import type { Plugin } from "@opencode-ai/plugin"

export interface HelloWorldPluginConfig {
  // Reserved for future configuration options
}

export const HelloWorldPlugin = (config?: HelloWorldPluginConfig): Plugin => {
  return async ({ client }) => {
    await client.app.log({
      body: {
        service: "open-mardi-gras",
        level: "info",
        message: "HelloWorldPlugin initialized",
      },
    })

    return {
      // Empty hooks object - this plugin just validates wiring
    }
  }
}
