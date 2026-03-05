# Replace `bd sync` With Dolt-Native Commands

## Overview

The beads CLI removed the `bd sync` command entirely as part of the migration
from JSONL-based sync to Dolt-native storage. Running `bd sync` now returns
`Error: unknown command "sync"`. This project references `bd sync` in plugin
source code, shipped workflow files, documentation, and agent instructions.
All references must be updated to use the Dolt-native equivalents.

### Background

`bd sync` used to serialize the SQLite database to `issues.jsonl`, commit
it to git, and optionally push to a git remote. With Dolt as the sole
backend, this pipeline is gone. Dolt provides its own version control:

- **`bd dolt commit`** -- commits pending changes in the Dolt working set.
  With `auto-commit: on` (the default), every `bd` write auto-commits, so
  an explicit `bd dolt commit` is a cheap no-op. With `auto-commit: batch`
  or `off`, it flushes accumulated changes. Exits 0 even when there is
  nothing to commit. Works regardless of whether a Dolt remote is configured.

- **`bd dolt push`** -- pushes Dolt commits to a configured Dolt remote.
  Exits 1 if no remote is configured. This is the user's responsibility
  (or handled by auto-push if the user configures a remote).

### Replacement Principle

| Old intent                  | Old command  | New command       |
|-----------------------------|--------------|-------------------|
| Flush local state           | `bd sync`    | `bd dolt commit`  |
| Push to remote              | `bd sync`    | `bd dolt push`    |

The plugin must only flush local state. It must never push on behalf of the
user. Workflow commands and agent instructions should use the appropriate
replacement depending on the intent of the original `bd sync` call.

---

## Scope

Changes are limited to files tracked in this repository, excluding:

- **`.opencode/` development directory** — contains `bd-` prefixed local
  workflow files that also reference `bd sync`. These are maintained by
  hand and are out of scope for this spec.
- **`.beads/issues.jsonl` and `.beads/backup/`** — auto-generated JSONL
  files containing historical issue descriptions that reference `bd sync`.
  These are not modified.

### Files in scope

| File | Nature of change |
|------|-----------------|
| `src/plugins/beads.ts` | Runtime code: replace `bd sync` calls |
| `src/plugins/beads.test.ts` | Test mocks: update command strings |
| `AGENTS.md` | Agent instructions: update quick ref and landing workflow |
| `README.md` | Documentation: update BeadsPlugin description |
| `.beads/README.md` | Auto-generated: replace with fresh `bd init` output |
| `opencode/commands/omg-work.md` | Workflow: replace sync steps |
| `opencode/commands/omg-decompose.md` | Workflow: replace sync step |
| `opencode/commands/omg-cleanup.md` | Workflow: replace sync step and description |
| `opencode/skills/omg-commands/SKILL.md` | CLI reference: replace sync section |

---

## Requirements

### R1: Plugin runtime (`src/plugins/beads.ts`)

**R1.1**: In `fetchBeadsContext()`, replace `await $`bd sync`.quiet()` with
`await $`bd dolt commit`.quiet()`. The purpose is to flush any uncommitted
Dolt working set changes before running `bd prime`, ensuring the prime
output reflects the latest state.

**R1.2**: In the `session.idle` event handler, replace
`await $`bd sync`.quiet()` with `await $`bd dolt commit`.quiet()`.

**R1.3**: Update the idle handler's error handling. The current code uses a
bare `catch {}` that silently swallows all errors. Replace it with a
try/catch that always logs a warning via the plugin logger, matching the
pattern already used in `fetchBeadsContext`. Do not attempt to classify
errors — log all of them as warnings.

**R1.4**: Update the JSDoc comment at the top of `fetchBeadsContext` --
currently says "Run `bd sync` then `bd prime`", should say "Run
`bd dolt commit` then `bd prime`".

**R1.5**: Update the module-level doc comment (lines 8-9) -- currently says
"Automatic `bd sync` on session idle", should describe the behavior
abstractly: "Automatic flush of pending beads state on session idle".

**R1.6**: Update the inline comments at lines 124-125 -- currently says
"bd sync is idempotent, cheap (ms), and a no-op when beads isn't
initialized", should say "bd dolt commit is idempotent, cheap, and a no-op
when auto-commit is on or beads isn't initialized".

### R2: Plugin tests (`src/plugins/beads.test.ts`)

**R2.1**: Update mock command matching from `bd sync` to `bd dolt commit`.

**R2.2**: Update the test name "runs bd sync on session idle" to reflect the
new command.

**R2.3**: Rename the `syncCalls` variable in `createMockShell` (and its
return type) to `commitCalls`. This variable tracks calls to the dolt commit
mock, so the name should match. Update all references in the test file
(declaration on line 6, push on line 15, return on line 28, and usage on
line 209).

**R2.4**: Add a test assertion to the "does not throw when bd commands fail"
test (or add a new test) verifying that the idle handler logs a warning when
`bd dolt commit` fails. The existing test only asserts no-throw; after R1.3
the idle handler calls `logger("warn", ...)`, and the test should verify
that a warning was logged via `logCalls`.

### R3: Agent instructions (`AGENTS.md`)

**R3.1**: In the Quick Reference block, replace `bd sync` and also fix the
stale `--status in_progress` flag. The updated block should read:
```
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
bd dolt commit        # Commit pending beads changes
bd dolt push          # Push beads to remote (if configured)
```

**R3.2**: In the Landing the Plane workflow (step 4), replace:
```bash
git pull --rebase
bd sync
git push
git status  # MUST show "up to date with origin"
```
with:
```bash
git pull --rebase
bd dolt push || true  # push beads to Dolt remote if configured
git push
git status  # MUST show "up to date with origin"
```
The `|| true` prevents agents from getting stuck when no Dolt remote is
configured. `bd dolt commit` is not needed here because auto-commit handles
it, and the prior steps (closing issues, etc.) already triggered commits.
The `git status` verification line is preserved — it validates the git push,
not the beads sync.

### R4: README (`README.md`)

**R4.1**: Update the BeadsPlugin description (line 116). Replace:
> The plugin also runs `bd sync` on session idle to keep beads state in sync.

with an abstract description:
> The plugin also flushes pending beads state on session idle.

### R5: `.beads/README.md`

**R5.1**: Replace the contents of `.beads/README.md` with the output from a
fresh `bd init`. Procedure:

1. Create a temp directory, run `git init` in it, then run `bd init`.
2. Copy the generated `.beads/README.md` from the temp directory over the
   existing `.beads/README.md` in the repo.
3. Clean up the temp directory.

The current file references `bd sync`, JSONL storage, and "Intelligent JSONL
merge resolution". The fresh version should reference `bd dolt push`, Dolt
storage, and "Dolt-native three-way merge resolution". Verify the generated
file contains `bd dolt push` and does not contain `bd sync` before copying.

### R6: Shipped workflow commands (`opencode/commands/`)

**R6.1**: `omg-work.md` line 14 -- replace `bd sync` with `bd dolt commit`
in the "epic complete" step: `bd epic close-eligible && bd dolt commit`.

**R6.2**: `omg-work.md` line 23 -- remove the `bd sync` step (step 8)
entirely. After closing a bead, auto-commit handles persistence. The next
iteration of the loop starts with `bd ready` which reads from the committed
state. Removing this step tightens the loop. Renumber the remaining step:
"Go back to step 1" becomes step 8 (was step 9).

**R6.3**: `omg-decompose.md` lines 29-33 -- replace the `bd sync` + git add
block. The intent is to ensure spec file and beads state are committed before
decomposition. Replace `bd sync` with `bd dolt commit`:
```
bd dolt commit
git add $1 .beads/
git status
```

**R6.4**: `omg-cleanup.md` line 9 -- replace `bd sync` with `bd dolt commit`.
Also update the frontmatter description from "cleanup, doctor, sync" to
"cleanup, doctor, commit".

### R7: Shipped skills reference (`opencode/skills/omg-commands/SKILL.md`)

**R7.1**: Replace the "Sync" section (lines 94-99) with an updated
reference:
```
## Sync

```
bd dolt commit                         # Commit pending beads changes
bd dolt push                           # Push to Dolt remote (if configured)
```
```

Remove the `bd sync --flush-only` line entirely -- there is no equivalent
and the concept no longer applies.

---

## Acceptance Criteria

- [ ] `bd sync` does not appear in any in-scope file
- [ ] Plugin calls `bd dolt commit` (not `bd sync`) in both locations
- [ ] Plugin idle handler logs warnings on all `bd dolt commit` failures
- [ ] Idle handler error test verifies a warning was logged (not just no-throw)
- [ ] All tests pass (`bun test`)
- [ ] Build succeeds (`bun run build`)
- [ ] Lint passes (`bun run lint`)
- [ ] `grep -r "bd sync" src/ opencode/ AGENTS.md README.md .beads/README.md` returns zero matches
- [ ] `.beads/README.md` contains `bd dolt push` (positive check for fresh content)
- [ ] AGENTS.md Quick Reference uses `--claim` (not `--status in_progress`)
- [ ] `omg-work.md` has exactly 8 numbered steps (step 8 = "Go back to step 1")

## Edge Cases

- **No Dolt remote configured**: `bd dolt commit` works fine (local-only).
  `bd dolt push` in AGENTS.md uses `|| true` to avoid blocking agents.
- **Auto-commit on (default)**: `bd dolt commit` is a no-op. No harm, no
  performance concern.
- **Auto-commit batch/off**: `bd dolt commit` flushes accumulated changes.
  This is the case where the explicit commit call matters most.
- **bd not installed**: Plugin logs a warning (R1.3). The `fetchBeadsContext`
  caller returns null, so the plugin degrades gracefully. The idle handler
  logs and continues.
- **Dolt server not running**: `bd dolt commit` will fail. Plugin logs a
  warning (R1.3) and continues.
- **`bd init` output changes**: R5.1 generates the file dynamically rather
  than hardcoding content. If `bd init` changes its README template in the
  future, the generated file will reflect those changes automatically.

## Open Questions

None.
