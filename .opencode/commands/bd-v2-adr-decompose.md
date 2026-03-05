---
description: Decompose an ADR into child constraint beads
agent: bd-v2-adr-decomposer
---

Decompose the ADR at `$1` into child constraint beads.

Steps:

1. Read the ADR file at `$1` thoroughly. Parse the YAML frontmatter for
   `title`, `description`, and `tags`.

2. Find the existing decision bead for this ADR:
   ```
   bd list --spec "$1" --json
   ```
   If no decision bead exists, create the parent first:
   ```
   bd create "ADR: <title>" -t decision --spec-id "$1" --body-file=$1 -l <tags> --json
   ```

3. Sync the decision bead body to match the current ADR file content:
   ```
   bd update <parent-id> --body-file=$1
   ```

4. Ensure the ADR file and beads state are committed before proceeding.
   The ADR file will be deleted at the end, so uncommitted changes would
   be lost:
   ```
    bd dolt commit
    git add $1 .beads/
    git status
   ```
   If there are uncommitted changes, commit them now:
   ```
   git commit -S -m "Sync ADR and beads state before decomposition"
   ```

5. Extract actionable constraints from the ADR. For each constraint, create
   a child decision bead and close it immediately:
   ```
   bd create "<Constraint statement>" -t decision --parent <parent-id> \
     -d "<detailed constraint with implementation context>" \
     -l <relevant-labels> --json
   bd close <child-id> --reason "Constraint extracted from ADR" --json
   ```

   Guidelines for constraint extraction:
   - Each constraint should be a specific, actionable statement
   - Focus on what agents need to know for implementation, not why
   - Split compound constraints into separate beads
   - One ADR may produce 1 to many constraints
   - Assign labels per-child based on what that constraint relates to
     (subset of parent tags, chosen by you based on relevance)

6. Run 2 refinement passes:
   - Pass 1: **Constraint completeness** — Is each constraint specific
     enough for an agent to act on? If vague, update it. If it contains
     multiple constraints, split it.
   - Pass 2: **Label accuracy** — Are the labels on each child appropriate?
     Remove irrelevant labels, add missing ones (only from the parent's
     tag set).

7. Close the parent decision bead:
   ```
   bd close <parent-id> --reason "Decomposed into N constraints" --json
   ```

8. Remove the ADR file:
   ```
   git rm $1
   ```
   The ADR content is preserved in the parent bead body and in git history.

9. Commit and sync:
   ```
    bd dolt commit
    git add .beads/
   git commit -S -m "Decompose ADR: <title>"
   ```

10. Present the final constraint structure for my review. Show each child
    bead with its title, description summary, and labels.
