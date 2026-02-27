---
name: beads-commands
description: Detailed beads CLI command reference for creating, updating, and managing issues. Load this skill before creating issues, filing discovered work, or updating issue fields.
---

# Beads Command Reference

## Creating Issues

```
bd create "Title" -d "description" --type task --priority 2 --json
```

- Use `--body-file=<path>` for long descriptions (up to 64 KB)
- Use `-d "markdown content"` for inline descriptions
- Use `--spec-id "<spec-path>"` to link an epic to its spec file
- Use `--parent <epic-id>` to create a child under an epic
- 4 rich-text fields: description (`-d`), design (`--design`),
  acceptance criteria (`--acceptance`), notes (`--notes`)
- Priority: 0-4 or P0-P4 (0=critical, 2=medium, 4=backlog).
  NOT "high"/"medium"/"low"
- Types: `task`, `bug`, `feature`, `epic`, `chore`

## Updating Issues

```
bd update <id> --title "..." --description "..." --notes "..."
bd update <id> --status in_progress
bd update <id> --assignee username
bd update <id> --body-file=<path>            # Sync body from file content
```

**WARNING**: Do NOT use `bd edit` — it opens $EDITOR which blocks agents.
Always use `bd update` with inline flags instead.

## Claiming and Closing

```
bd update <id> --claim                 # Atomic: sets assignee + in_progress
bd close <id> --reason "what you did"  # Complete work
bd close <id1> <id2> ...               # Close multiple at once (more efficient)
```

## Finding Work

```
bd ready --json                        # Unblocked work
bd ready --parent <epic> --json        # Scoped to an epic
bd show <id> --json                    # Full issue details
bd list --status open --json           # All open issues
bd list --spec "<spec-path>" --json    # Find epic by spec file path
bd blocked --json                      # Blocked issues
```

## Filing Discovered Work

When you find something that needs attention while working on another task:

```
bd create "Found issue" -d "Details" --deps discovered-from:<current-bead-id> --json
```

This creates the new issue and links it back to the bead where you discovered it.

## Sync

```
bd sync                                # Sync state with git
bd sync --flush-only                   # Export to JSONL only
```
