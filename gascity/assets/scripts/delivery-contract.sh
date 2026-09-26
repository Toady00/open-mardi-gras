#!/usr/bin/env bash
# Read the approved execution classification from spec bodies, not inferred ID prefixes.
set -euo pipefail
root="${1:?document root required}"; shift
fail() { printf 'omg delivery contract: %s\n' "$*" >&2; exit 1; }
(($#)) || fail 'no specs supplied'
inventory='[]'
for source in "$@"; do
  block=$(awk '
    /^```omg-delivery[[:space:]]*$/ { if (++count > 1) exit 2; inside=1; next }
    inside && /^```[[:space:]]*$/ { inside=0; closed=1; next }
    inside { print }
    END { if (count != 1 || inside || !closed) exit 2 }
  ' "$root/$source") || fail "$source requires exactly one closed omg-delivery YAML block; refine and approve the contract"
  parsed=$(printf '%s\n' "$block" | yq -p=yaml -o=json '.') || fail "invalid YAML in $source"
  keysets=$(printf '%s\n' "$block" | yq -p=yaml -o=json '[.. | select(tag == "!!map") | keys]')
  jq -e 'all(.[]; length == (unique | length))' <<<"$keysets" >/dev/null || fail "duplicate YAML keys in $source"
  jq -e 'def text: type == "string" and length > 0;
    .version == 1 and (.requirements | type == "object" and length > 0) and
    all(.requirements | to_entries[];
      (.key | test("^[A-Za-z0-9][A-Za-z0-9._:-]*$")) and
      (.value | type == "object") and
      (.value.kind | IN("implementation", "development-check", "verification-artifact", "downstream-check")) and
      (if .value.kind == "downstream-check" then
        (.value.owner | text) and (.value.stage | text)
       else .value.owner == null and .value.stage == null end))
  ' <<<"$parsed" >/dev/null || fail "invalid development/downstream classification in $source"
  rows=$(jq --arg s "$source" '[.requirements | to_entries[] |
    {id:.key, kind:.value.kind, source:$s} +
    (if .value.kind == "downstream-check" then {owner:.value.owner,stage:.value.stage} else {} end)]' <<<"$parsed")
  inventory=$(jq -n --argjson old "$inventory" --argjson new "$rows" '$old + $new')
done
jq -e '([.[].id] | length == (unique | length)) and any(.[]; .kind != "downstream-check")' <<<"$inventory" >/dev/null || fail 'IDs must have one owning spec, and development work must exist'
jq -c 'sort_by(.id)' <<<"$inventory"
