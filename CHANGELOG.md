# Changelog

## 1.3.0 - 2026-08-08

### Added

- Record installed instruments in `.opencode/.omg-manifest.json` so setup can distinguish managed files from user-authored files.
- Add `setup --force` to explicitly replace locally modified instruments and remove modified retired files.

### Changed

- Preserve and report locally modified instruments instead of overwriting them during setup.
- Document the requirement-scoping pass and handoff document used when work moves between repositories.

### Fixed

- Remove instruments that a previous release installed but the current release no longer ships, without deleting user-authored or locally modified files.

## 1.2.0 - 2026-08-06

### Added

- Add frontmatter skeletons and default Hindsight shipping metadata to authored document templates.
- Add self-contained adjudication beads and canonical handoff documents for requirements that move between repositories.

### Changed

- Replace all-or-nothing test planning with cost-based verification choices: automated tests, deterministic gates, review obligations, or an explicit no-verification decision.
- Gate epic-blocking review findings by blast radius and keep unrelated findings outside the epic.
- Bound requirements to work verifiable in a deployable repository, with explicit ownership and relocation tracking for out-of-scope work.
- Make Hindsight document shipping asynchronous, operation-aware, safely resumable, and capable of batching documents from the tree.

### Fixed

- Preserve executable workflow scripts, resolve satellite paths from the correct repository, and fall back to ADR headings or IDs when titles are absent.
- Fix frontmatter extraction and multi-document Hindsight shipping payload assembly.

## 1.1.1 - 2026-07-20 [YANKED]

Yanked because it built on the `test: false` opt-out from 1.1.0, which has since been removed.

### Fixed

- Remove verification-planning beads deterministically when a repository opts out with `test: false`.
- Prevent unrelated review findings from blocking an epic and route disputed findings through self-contained adjudication beads.

## 1.1.0 - 2026-07-19 [YANKED]

Yanked because the `test: false` opt-out it introduced made verification all-or-nothing and has since been removed. Everything else here is carried forward.

### Added

- Add document frontmatter skeletons, default Hindsight shipping metadata, and a `test: false` opt-out for verification planning.

### Changed

- Resolve centralized satellite specs and terminal review/report beads consistently during decomposition.

### Fixed

- Preserve executable permissions on workflow scripts installed by setup.
- Resolve satellite OpenCode paths relative to the correct repository and fall back to ADR headings or IDs when titles are absent.

## 1.0.0 - 2026-07-18

### Changed

- Replace automatic `bd prime` system-prompt injection with a durable `/omg-build` foreman watchdog that preserves ownership across OpenCode restarts and resumes ready work after the user continues the restored session.
- Transfer an epic's watchdog ownership to a fresh `/omg-build` session while preventing multiple tracked owners.
- Gate then-chaining for tracked foreman sessions until `bd ready --parent <epic> --json` returns a valid empty array.
- Remove the redundant `then` follow-up from the shipped `/omg-build` command.

## 0.4.2 - 2026-06-28

### Fixed

- Forward `BEADS_*` environment variables into subagent shells so `bd` commands use the same backend as the primary session.

## 0.4.1 - 2026-06-28 [YANKED]

Yanked because it contained no user-facing changes.

## 0.4.0 - 2026-04-07

### Changed

- Update workflow files for beads 1.0.0 (`6179920`)

### Fixed

- Fix `npx` setup silently failing due to symlink path mismatch (`59dc8c8`)

## 0.3.1 - 2026-03-17

### Fixed
- Updated the setup CLI to copy the full packaged `opencode/` tree into `.opencode/`, so newly shipped workflow files like `omg-ensure-work-finished` are installed automatically.

### Added
- Added a setup CLI test covering recursive workflow file discovery.
- Added `mise.toml` to pin the Bun version used for local development.

### Changed
- Clarified the README so the setup command documents that it installs the packaged contents of `opencode/`.

## 0.3.0 - 2026-03-05

### Changed
- Migrated bundled beads workflow usage toward Dolt-native `bd` commands.
- Updated shipped workflow assets under `.opencode/` to align with `omg` issue prefix conventions.

### Fixed
- Removed stale beads hook shim files that were no longer used.

## 0.2.1 - 2026-03-01

### Changed
- Refined workflow completion guidance to better enforce finishing and verification steps.

## 0.2.0 - 2026-03-01

### Added
- Added npm plugin entry point for OpenCode auto-loading.

### Changed
- Improved shipped agent display names and cleaned up agent file frontmatter.

## 0.1.0 - 2026-02-26

Initial release of open-mardi-gras.

### Added
- Initial scaffolding with TypeScript build system
- HelloWorldPlugin for validation
- ESLint configuration with TypeScript support
- NPM package configuration for ESM-only distribution
