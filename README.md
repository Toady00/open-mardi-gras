# Open Mardi Gras

An [opencode](https://opencode.ai) plugin bringing together powerful workflow features for personal productivity.

## Philosophy

This plugin combines ideas from multiple sources to create a cohesive set of tools for managing AI-assisted workflows. It's built for personal use, with an eye toward broader utility.

## Features

### 🔄 Return (Command Chaining)

Execute follow-up actions automatically when a command completes. Inspired by similar functionality in other tools, but built with flexibility in mind.

**How it works:**
Add a `return` key to your command's frontmatter:

```yaml
---
return: "Summarize the output in 3 bullet points"
---
```

Or chain to another command:

```yaml
---
return: "/my-next-command"
---
```

After your command executes, the plugin automatically submits the return value as the next message — whether that's a text prompt to send to the AI or another command to run.

**Use cases:**
- Automatically summarize long outputs
- Chain multiple commands into a single workflow
- Ensure consistent follow-up prompts after specific tasks
- Create "macros" that combine multiple operations

### 📿 Beads Integration

[Beads](https://github.com/steveyegge/beads) is a powerful notation for thought sequences. This plugin integrates beads workflows into opencode for structured thinking and problem-solving.

*(Coming soon)*

## Installation

```bash
npm install open-mardi-gras
```

## Plugin Usage

Add to your `opencode.config.ts`:

```typescript
// Option 1: String reference (simplest)
export default defineConfig({
  plugins: [
    'open-mardi-gras'
  ]
})

// Option 2: Import with configuration
import { HelloWorldPlugin } from 'open-mardi-gras'

export default defineConfig({
  plugins: [
    HelloWorldPlugin({ /* options */ })
  ]
})
```

## Development Setup

```bash
# Install dependencies
bun install

# Build the project
bun run build

# Run linter
bun run lint

# Watch mode (rebuild on changes)
bun run dev
```

## Contributing

Contributions are welcome. Please open an issue first to discuss what you'd like to change. Make sure to run `bun run lint` and `bun run build` before submitting a pull request.

## License

MIT
