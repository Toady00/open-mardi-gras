# Beads Workflow Validation (Smoke Test)

## Overview

The beads CLI and its integration with this project have undergone significant
changes. Before cutting a new release, we need to verify that the core beads
lifecycle — creating issues, claiming them, performing trivial work, and
closing them — works without errors or warnings.

This spec defines a set of no-op tasks whose only purpose is to exercise the
`bd` command lifecycle. Each task touches a file in `tmp/` (which is not
committed to git) and then closes its bead. The real deliverable is not the
files — it's confidence that `bd` commands execute cleanly and that issue
state is accurate after each transition.

**If any `bd` command produces warnings or errors during execution, the agent
must file a bug bead immediately documenting the exact command, output, and
context.**

---

## Requirements

### R1: Setup

**R1.1**: Create the `tmp/` directory if it does not already exist.

### R2: No-op tasks

Each task follows the same pattern:

1. Claim the bead (`bd update <id> --claim`).
2. Verify the bead status is `in_progress` (`bd show <id> --json`, check
   that the `status` field equals `"in_progress"`).
3. Create a file in `tmp/` with the specified name and content.
4. Verify the file exists.
5. Close the bead (`bd close <id> --reason "File created successfully"`).
6. Verify the bead status is `closed` (`bd show <id> --json`, check that
   the `status` field equals `"closed"`).

**Error detection**: A `bd` command is considered failed if it exits non-zero.
Do NOT match on the words "warning" or "error" in stdout — the JSON output
includes the bead's description text which may contain those words innocuously.
Only non-zero exit codes indicate a problem.

**If any `bd` command in steps 1, 5, or their verification steps (2, 6)
exits non-zero, file a bug bead immediately:**
```
bd create "bd command failure: <summary>" -d "<full command and output>" --type bug --priority 0 --parent <epic-id> --json
```

If the bug-filing `bd create` itself fails, log the full error to agent
output and continue with the remaining tasks. Do not attempt to file a bug
about the bug-filing failure.

The five tasks are:

**R2.1 — Knock knock**: Create `tmp/knock-knock.txt` containing:
```
Knock knock.
Who's there?
Bead.
Bead who?
Bead you to it — this workflow works!
```

**R2.2 — Why did the function break?**: Create `tmp/function-broke.txt` containing:
```
Why did the function break?
Because it had too many arguments.
```

**R2.3 — A SQL walks into a bar**: Create `tmp/sql-bar.txt` containing:
```
A SQL query walks into a bar, sees two tables, and asks...
"Can I JOIN you?"
```

**R2.4 — Git blame**: Create `tmp/git-blame.txt` containing:
```
Why do programmers prefer dark mode?
Because light attracts bugs.
```

**R2.5 — The final bead**: Create `tmp/final-bead.txt` containing:
```
What's a bead's favorite type of music?
Heavy meta.
```

### R3: Verification and cleanup

**R3.1**: After all five tasks are closed, verify all child beads are in
`closed` status by running `bd list --parent <epic-id> --json` and checking
that every entry has `"status": "closed"`.

**R3.2**: Close the epic bead itself
(`bd close <epic-id> --reason "All smoke tests passed"`).

**R3.3**: Verify the epic status is `closed`
(`bd show <epic-id> --json`, check that the `status` field equals `"closed"`).

**R3.4**: Do NOT delete the `tmp/` files or directory. The user will clean
those up manually.

**R3.5**: Do NOT add, commit, or push any files in `tmp/` to git. Do NOT
modify `.gitignore`.

---

## Acceptance Criteria

- [ ] `tmp/` directory exists
- [ ] All five task beads transition from `open` → `in_progress` → `closed`
      with zero non-zero exit codes from `bd` commands
- [ ] Each `bd show <id> --json` verification confirms the expected `status`
      value after each transition
- [ ] All five `tmp/` files exist with the specified content
- [ ] `bd list --parent <epic-id> --json` shows all children as `closed`
- [ ] The epic bead is closed after all child beads are closed
- [ ] No files in `tmp/` are staged or committed to git
- [ ] `.gitignore` is unmodified
- [ ] If any `bd` command exited non-zero, a bug bead was filed as a child
      of the epic with priority 0

---

## Edge Cases

- **`tmp/` already exists**: R1.1 handles this — create only if missing.
- **`bd` command fails**: The agent files a bug bead per R2 and continues
  with the remaining tasks. A single failure should not halt the entire
  smoke test.
- **Bug-filing itself fails**: Log the error to agent output and continue.
  Do not recurse into further bug-filing attempts.
- **`bd show` returns unexpected status**: This itself is a bug — the
  non-zero exit code rule won't catch it, so the agent should file a bug
  bead describing the expected vs actual status value.

---

## Open Questions

None.
