# Using the OMG Workflow

OMG provides a guided path from repository setup, through product and architecture documents, to an implemented and reviewed feature. The agents, commands, and skills under this repository's `opencode/` directory contain the detailed procedures; this guide is the short path through them.

## 1. Install the workflow

Run the setup command in the repository you want to onboard:

```bash
npx @toady00/open-mardi-gras setup
```

The setup command:

- Copies every shipped agent, command, and skill from `opencode/` into the target repository's `.opencode/` directory.
- Creates or updates `.opencode/opencode.json` and adds `@toady00/open-mardi-gras` to its `plugin` array.
- Preserves the other settings and plugin entries already in that config.
- Avoids adding a duplicate when the plugin is already configured, including when it is version-pinned.

Run setup again after upgrading to refresh the installed instruments. Restart opencode after setup so it loads the plugin and the new instruments.

## 2. Onboard the repository

Run the onboarding command with the repository's role:

```text
/omg-onboard <solo|centralized|satellite>
```

Use `solo` for a single repository. For a multi-repository platform, use `centralized` for the shared documentation repository and `satellite` for each repository that owns code and builds features.

Follow the onboarder's questions and instructions. It discovers existing configuration, fills the genuine gaps, establishes `.workflow.yaml`, configures Beads where the selected mode needs it, wires centralized documentation access for satellites, and verifies that the resulting setup works. This should guide you through most of the wiring, including directing you to `/omg-hindsight-setup` when the repository's Hindsight bank or tagging guidance still needs to be established.

Restart opencode if onboarding changes configuration that is loaded at startup.

## 3. Develop the documents

Use `omg-product-manager` and `omg-architect` to develop the durable documents that explain what should be built and why.

- `omg-product-manager` produces and refines PRDs, roadmaps, user stories, specs, and handoffs. It owns the product problem, user value, scope, and success criteria.
- `omg-architect` produces and reviews design documents and ADRs. It owns buildability, system constraints, tradeoffs, risks, and architectural decisions.

You can work with either agent directly for broader document development. When the initiative is understood well enough to become a buildable specification, start the command flow:

```text
/omg-spec <what you want to build>
/omg-spec-review <spec-path>
```

`/omg-spec` routes to the product manager to clarify the problem and write the spec. `/omg-spec-review` routes to the architect to review that spec for buildability and verifiability and to record an ADR only when the review exposes a durable architectural decision. Iterate between product and architecture until the important questions are settled.

For a feature owned by a particular code repository, run this flow in that repository. In a centralized setup, reserve the centralized repository for genuinely cross-cutting documents that are not tied to one codebase.

## 4. Harden the spec

```text
/omg-spec-harden <spec-path>
```

The hardening command folds settled architectural decisions into the spec and resolves gaps, contradictions, edge cases, missing acceptance criteria, and open questions.

It also holds the spec to the bound OMG works within: an epic is done when the repository contains everything the feature needs and the repository's own verification surface is green. A requirement that can only be verified against a running system — a load test, a chaos exercise, an alarm drill — is outside that bound, and hardening will stop and settle each one with you rather than passing it to a builder who cannot do it. Such a requirement either leaves outright or relocates to a named destination, recorded in the spec's Relocated Requirements section: another system's spec, a backlog item, or a handoff document that the product manager authors on request. Expect to be asked; the command will not invent a destination on its own.

Repeat it as needed. The result should be an implementation contract that a coding agent can follow without having to guess.

## 5. Plan and build

Turn the hardened spec into an executable work graph:

```text
/omg-decompose <spec-path>
```

The decomposer creates the epic, plans verification, creates and connects the implementation work, and presents the resulting graph for review.

After approving the plan, run:

```text
/omg-build <epic-id>
```

The foreman dispatches the planned work to the appropriate builder, tester, product, architecture, and review agents. It drives the build and review loop until the epic is complete or reaches a blocker that needs human input. The terminal work writes a build report; the build command does not automatically publish documents to Hindsight.

## Command Reference

| Command | Purpose |
|---|---|
| `/omg-onboard <mode>` | Discover, configure, and verify a repository's workflow wiring |
| `/omg-hindsight-setup` | Establish the bank architecture or author `hindsight.md` against an existing bank |
| `/omg-spec <idea>` | Have the product manager clarify the problem and write a spec |
| `/omg-spec-review <spec>` | Have the architect review buildability and record warranted ADRs |
| `/omg-spec-harden <spec>` | Scope the spec to what the repository owns and finish it as a complete implementation contract |
| `/omg-decompose <spec>` | Create and validate the epic's implementation and verification plan |
| `/omg-build <epic>` | Orchestrate implementation, testing, review, and the build report |
