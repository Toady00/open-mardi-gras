---
description: Decompose a spec into child tasks under its epic, informed by architectural decisions
agent: bd-v2-decomposer
---

Decompose the specification at `$1` into child tasks under an epic.

Steps:

1. Read the spec file at `$1` thoroughly.

2. Find the existing epic for this spec:
   ```
   bd list --spec "$1" --json
   ```
   If no epic exists, ask me whether I want to create one. If I confirm:
   ```
   bd create "<Feature>" -t epic -p 1 --spec-id "$1" --body-file=$1 --json
   ```

3. Sync the epic body to match the current spec file content:
   ```
   bd update <epic-id> --body-file=$1
   ```

4. Check for related decision constraints on the epic:
   - Run `bd show <epic-id> --json` and look for dependencies with type
     `relates-to` that point to decision-type beads.
   - For each linked decision bead, run `bd show <bead-id> --json` to read
     the full constraint.
   - Use these constraints to inform how you scope and describe child tasks.
   If the epic has no `relates-to` decision links, skip this step.

5. Ensure the spec file and beads state are committed before proceeding.
   The spec file will be deleted at the end, so uncommitted changes would
   be lost:
   ```
    bd dolt commit
    git add $1 .beads/
    git status
   ```
   If there are uncommitted changes, commit them now:
   ```
   git commit -S -m "Sync spec and beads state before decomposition"
   ```

6. Create child tasks under the epic with rich markdown descriptions:
   ```
   bd create "<Task title>" -t task --parent <epic-id> -d "..." --json
   ```
   Use `--body-file` for long descriptions or `-d` with full markdown for
   shorter ones. When a decision constraint applies to a specific child
   task, include it directly in that task's description.

7. Wire blocking dependencies between children:
   ```
   bd dep add <dependent-child> <dependency-child>
   ```

8. Create a final "Code review" bead as a child of the epic:
   ```
   bd create "Code review: <feature>" -t task --parent <epic-id> --json
   ```
   - Blocked by ALL other child beads
   - Description:
     ```
     Invoke the reviewer agent (@bd-v2-reviewer) to perform a thorough code
     review of all changes in this epic. The reviewer will file beads for
     every finding using discovered-from links. Close this bead only when
     the review is complete.
     ```

9. Validate the dependency graph: `bd swarm validate <epic-id>`

10. Show the structure: `bd dep tree <epic-id>`

11. Run 4 refinement passes:
    - Pass 1: Description completeness — can an agent implement each bead
      without asking questions? If not, add the missing context.
    - Pass 2: Dependency correctness — missing ordering constraints?
      Unnecessary ones blocking parallelism? Fix them.
    - Pass 3: Scope sizing — split anything too large, merge anything too
      small.
    - Pass 4: Final polish — proofread titles, descriptions, acceptance
      criteria. Ensure the review bead blocks on everything.

12. Present the final structure for my review.

13. After I confirm the structure, remove the spec file:
    ```
    git rm $1
    ```
    The spec content is preserved in the epic body and in git history.
