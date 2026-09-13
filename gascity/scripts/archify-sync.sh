#!/usr/bin/env bash
set -euo pipefail

pack_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
pin="$pack_root/upstream/archify.json"
destination="$pack_root/skills/archify"

repository="$(jq -er '.repository | strings | select(length > 0)' "$pin")"
commit="$(jq -er '.commit | strings' "$pin")"
subdirectory="$(jq -er '.subdirectory | strings | select(length > 0)' "$pin")"
if [[ ! "$commit" =~ ^[0-9a-f]{40}$ ]]; then
    printf '%s\n' 'Archify pin must contain a full lowercase commit SHA.' >&2
    exit 1
fi

# This is an upstream-owned snapshot. Local edits and obsolete files are removed.
rm -rf -- "$destination"

checkout="$(mktemp -d "${TMPDIR:-/tmp}/omg-archify.XXXXXX")"
trap 'rm -rf -- "$checkout"' EXIT
git init --quiet "$checkout"
git -C "$checkout" remote add origin "$repository"
git -C "$checkout" fetch --quiet --depth=1 origin "$commit"
if [[ "$(git -C "$checkout" rev-parse 'FETCH_HEAD^{commit}')" != "$commit" ]]; then
    printf '%s\n' 'Fetched commit does not match the Archify pin.' >&2
    exit 1
fi

mkdir -p "$destination"
git -C "$checkout" archive "$commit:$subdirectory" | tar -x -C "$destination"
test -f "$destination/SKILL.md"
test -f "$destination/LICENSE"
printf 'Synced Archify at %s\n' "$commit"
