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
opencode plugin install toady00/open-mardi-gras
```

## Configuration

Add to your `opencode.config.ts`:

```typescript
export default defineConfig({
  plugins: [
    'open-mardi-gras'
  ]
})
```

## Development

This plugin is in active development. Features are being added incrementally based on real-world use.

## License

MIT
