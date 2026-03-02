# Mysterious Empty Files at Project Root

## Observed

After installing the plugin in an Elixir project and running decompose + work
workflows, two unexpected files appeared at the project root:

- `0` — empty file
- `:ok` — empty file

## Notes

- `:ok` is an Elixir atom/symbol, so this may be an Elixir tooling artifact
  rather than a plugin issue
- `0` could be a shell exit code being captured as a filename, possibly from
  a redirected command output (e.g., `echo $? > 0` or similar)
- Could also be the `bd` CLI or `yq` writing to unexpected file descriptors

## Status

Not yet reproduced in isolation. Could be this plugin, beads CLI, or
something unrelated to this project entirely. Needs further investigation
if it recurs.
