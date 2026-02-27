---
description: Work through an epic's ready queue
agent: build
---

Work through the ready queue for epic `$1`.

Before starting, load the `beads-commands` skill. If you need to manage
epic-level operations or dependencies, also load the `beads-epics` skill.

Your workflow:
1. Run: `bd ready --parent $1 --unassigned --json --limit 1`
2. If no results, the epic is complete. Run: `bd epic close-eligible && bd sync`
3. Claim the issue: `bd update <id> --claim`
4. Read the full description: `bd show <id>`
5. Implement what the description says.
6. If you discover new work while implementing:
   `bd create "Title" -d "Details" --deps discovered-from:<id> --json`
7. When done: `bd close <id> --reason "what you did" --json`
8. Run: `bd sync`
9. Go back to step 1.

IMPORTANT: If the bead you reach is a code review bead, invoke the reviewer:
`@bd-reviewer`
Pass it the epic ID and the review bead ID so it knows what to review and what
to close.

All work creates beads. Everything you do must be tracked in beads.
Do NOT use TodoWrite or markdown TODO lists.
