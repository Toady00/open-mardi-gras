# List available recipes.
default:
    @just --list

# Install the docs tooling.
docs-setup:
    bun install --cwd tools/docs

# Regenerate omg_flowchart.html from omg_flowchart.md.
docs-build:
    node tools/docs/build-flowchart-html.mjs

# Sync the Gas City pack's vendored Archify skill.
archify-sync:
    just --justfile gascity/justfile archify-sync
