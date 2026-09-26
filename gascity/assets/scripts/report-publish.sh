#!/usr/bin/env bash
# Worker-side report publication. This runs in the architect's session with the
# worker's own Git identity (SSH agent, credential helpers, user gitconfig). The
# controller's formula check runs verify.sh in a sandbox without any of that, so
# every remote read and write happens here and is recorded in report.json as
# publication evidence for the offline check to inspect.
#
# Exit codes: 0 done (local or pushed), 1 blocked or failed (recorded on the
# receipt when possible), 2 the remote write succeeded but the receipt could not
# be persisted; rerun to record the already published report.
set -euo pipefail
# Tools come from the worker session's PATH; nothing is prepended here.
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
fail() { printf 'omg report: %s\n' "$*" >&2; exit 1; }
for tool in jq git; do command -v "$tool" >/dev/null || fail "missing $tool"; done
action=${1:-}; shift || true
[[ "$action" == publish ]] || fail 'usage: report publish --root <artifact-root> [--preflight] [--city <path>] [--rig <name>]'
root= preflight=
context=()
while (($#)); do
  case "$1" in
    --root) root="${2:?}"; shift 2;;
    --preflight) preflight=1; shift;;
    --city|--rig) context+=("$1" "${2:?}"); shift 2;;
    --json) shift;;
    *) fail "unknown argument $1";;
  esac
done
[[ "$root" = /* && -d "$root" ]] || fail 'artifact root must be an existing absolute directory'
receipt_file="$root/report.json"

# Every receipt write goes through here. A write that does not land durably is
# reported by the caller; nothing prints success before the rename returns.
write_receipt() {
  local filter="$1"; shift
  local tmp
  tmp=$(mktemp "$root/.report.XXXXXX" 2>&1) || { receipt_error="cannot create a temporary receipt in $root: $tmp"; return 1; }
  if ! jq "$@" "$filter" "$receipt_file" >"$tmp" 2>"$tmp.err"; then
    receipt_error="cannot render the receipt: $(tr -d '\n' <"$tmp.err")"; rm -f "$tmp" "$tmp.err"; return 1
  fi
  rm -f "$tmp.err"
  if ! mv -f "$tmp" "$receipt_file" 2>"$tmp.err"; then
    receipt_error="cannot replace $receipt_file: $(tr -d '\n' <"$tmp.err")"; rm -f "$tmp" "$tmp.err"; return 1
  fi
  rm -f "$tmp.err"
}
receipt_error=

# Local artifact validation is shared with the controller check; only the
# publication disposition is decided here.
plan=$(bash "$here/verify.sh" --stage report --root "$root" --plan ${context[@]+"${context[@]}"}) || exit 1
destination=$(jq -r '.destination // empty' <<<"$plan")
if [[ -z "$destination" ]]; then
  # Not authorized (or no longer authorized): the receipt must read local. A
  # stale pushed/failed disposition from a previous run is normalized so the
  # offline check sees the current truth; a clean local receipt is left alone.
  if jq -e '.status == "local" and .remote_ref == null and (has("reason") or has("error") or has("publication") | not)' "$receipt_file" >/dev/null; then
    stale=false
  else
    stale=true
  fi
  if [[ -n "$preflight" ]]; then
    jq -cn --argjson n "$stale" '{status: "preflight", destination: null, normalize: $n}'
    exit 0
  fi
  if $stale; then
    write_receipt 'del(.reason, .error, .publication) | .status = "local" | .remote_ref = null' \
      || { printf 'omg report: %s\n' "$receipt_error" >&2; jq -cn --arg e "$receipt_error" '{status: "failed", destination: null, reason: "receipt", error: $e}'; exit 1; }
  fi
  jq -cn --argjson n "$stale" '{status: "local", destination: null, normalized: $n}'
  exit 0
fi
repo=$(jq -r '.repo' <<<"$plan")
commit=$(jq -r '.commit' <<<"$plan")
revision=$(jq -r '.revision' <<<"$plan")
report_path=$(jq -r '.path' <<<"$plan")
report_blob=$(jq -r '.report_blob' <<<"$plan")
remote=${destination%%/*}
branch=${destination#*/}
rgit() { git -C "$repo" "$@"; }
errors=$(mktemp "${TMPDIR:-/tmp}/omg-report-publish.XXXXXX"); trap 'rm -f "$errors"' EXIT
# Credentials embedded in a URL never reach a receipt or an error.
redact() { sed -E 's#(://)[^/@]*@#\1#g'; }
stderr_text() { tr -d '\r' <"$errors" | sed -e '/^$/d' | tail -n 20 | redact; }

# Every failure of an actual publication attempt is recorded on the receipt so
# the controller check reports the real blocker and the local commit stays
# recoverable on the report step. A preflight only reports: it never replaces
# the receipt, which may still hold an earlier successful publication.
record_failure() {
  local reason="$1" error="$2" base="${3:-}"
  if [[ -n "$preflight" ]]; then
    printf 'omg report: %s\n' "$error" >&2
    jq -cn --arg d "$destination" --arg reason "$reason" --arg error "$error" '{status: "failed", preflight: true, destination: $d, reason: $reason, error: $error}'
    exit 1
  fi
  if write_receipt '
      del(.publication) | .status = "failed" | .remote_ref = null | .reason = $reason | .error = $error |
      .publication = ({destination: $d, url: $u} + (if $base == "" then {} else {base: $base} end))' \
      --arg d "$destination" --arg u "${url:-}" --arg reason "$reason" --arg error "$error" --arg base "$base"; then
    jq -cn --arg d "$destination" --arg reason "$reason" --arg error "$error" '{status: "failed", destination: $d, reason: $reason, error: $error}'
  else
    printf 'omg report: %s\n' "$receipt_error" >&2
    jq -cn --arg d "$destination" --arg reason "$reason" --arg error "$error" --arg re "$receipt_error" \
      '{status: "failed", destination: $d, reason: $reason, error: $error, receipt_error: $re}'
  fi
  exit 1
}

# One effective endpoint. The authority named a remote whose fetch URL the code
# receipt was read against; a different or additional push URL would publish
# to a repository nobody authorized, so the configuration is rejected as
# ambiguous rather than widened.
fetch_url=$(rgit remote get-url "$remote" 2>"$errors") || { url=; record_failure remote_config "unknown remote $remote in $repo: $(stderr_text)"; }
push_urls=$(rgit remote get-url --push --all "$remote" 2>"$errors") || { url=; record_failure remote_config "cannot read push URLs of remote $remote: $(stderr_text)"; }
url=$(redact <<<"$fetch_url")
[[ $(wc -l <<<"$push_urls") -eq 1 ]] || record_failure remote_config "remote $remote has several push URLs; report publication needs one endpoint: $(redact <<<"$push_urls" | tr '\n' ' ')"
[[ "$push_urls" == "$fetch_url" ]] || record_failure remote_config "remote $remote push URL $(redact <<<"$push_urls") differs from its fetch URL $url; report publication needs one endpoint"
endpoint=$fetch_url

listing=$(rgit ls-remote --heads "$endpoint" "refs/heads/$branch" 2>"$errors") || record_failure remote "cannot read $url: $(stderr_text)"
base=$(awk -v ref="refs/heads/$branch" '$2 == ref { print $1 }' <<<"$listing")
[[ "$base" =~ ^[0-9a-f]{40,64}$ ]] || record_failure missing_branch "remote branch $destination does not exist on $url"
if ! rgit cat-file -e "$base^{commit}" 2>/dev/null; then
  rgit fetch --quiet --no-tags --no-recurse-submodules "$endpoint" "refs/heads/$branch" 2>"$errors" || record_failure remote "cannot fetch $destination from $url: $(stderr_text)" "$base"
  rgit cat-file -e "$base^{commit}" 2>/dev/null || record_failure remote "fetched $destination but its tip $base is not readable locally" "$base"
fi
rgit merge-base --is-ancestor "$revision" "$base" \
  || record_failure revision_not_published "remote branch $destination at $base does not contain the finalized assessed revision $revision; the code publication receipt no longer matches the remote" "$base"
if [[ "$base" != "$commit" ]]; then
  rgit merge-base --is-ancestor "$base" "$commit" \
    || record_failure diverged "remote branch $destination moved to $base, which the report commit $commit does not descend from; recreate the report on the published tip" "$base"
fi
outgoing=()
while IFS= read -r candidate; do
  [[ -n "$candidate" ]] || continue
  [[ $(rgit rev-list --parents -n 1 "$candidate" | wc -w) -eq 2 && "$(rgit diff-tree --no-commit-id --name-only -r "$candidate")" == "$report_path" ]] \
    || record_failure outgoing "outgoing commit $candidate is not a report-only commit; only report commits may be published beyond the assessed revision $revision" "$base"
  outgoing+=("$candidate")
done < <(rgit rev-list "$base..$commit")

if [[ -n "$preflight" ]]; then
  jq -cn --arg d "$destination" --arg u "$url" --arg c "$commit" --arg base "$base" --arg r "$revision" \
    --argjson outgoing "$(printf '%s\n' ${outgoing[@]+"${outgoing[@]}"} | jq -R . | jq -s 'map(select(length > 0))')" \
    '{status: "preflight", destination: $d, url: $u, commit: $c, base: $base, revision: $r, outgoing: $outgoing}'
  exit 0
fi

if [[ "$base" != "$commit" ]]; then
  # Push the validated SHA to the validated endpoint and ref only, and only if
  # the remote still reads the tip that was just inspected; a concurrent move is
  # rejected, never merged over. Tag following and submodule recursion are
  # disabled so no configuration can add a second write.
  rgit -c push.followTags=false -c push.recurseSubmodules=no push --quiet --no-follow-tags --recurse-submodules=no \
    --force-with-lease="refs/heads/$branch:$base" "$endpoint" "$commit:refs/heads/$branch" 2>"$errors" \
    || record_failure push "push of $commit to $destination was rejected: $(stderr_text)" "$base"
fi
listing=$(rgit ls-remote --heads "$endpoint" "refs/heads/$branch" 2>"$errors") || record_failure remote "pushed $commit but cannot re-read $destination: $(stderr_text)" "$base"
observed=$(awk -v ref="refs/heads/$branch" '$2 == ref { print $1 }' <<<"$listing")
[[ "$observed" == "$commit" ]] || record_failure unverified "pushed $commit but $destination now reads ${observed:-nothing}" "$base"

if ! write_receipt '
    del(.reason, .error) | .status = "pushed" | .remote_ref = $d |
    .publication = {destination: $d, remote: $remote, branch: $branch, url: $u, base: $base, pushed: $c,
                    observed: $observed, revision: $r, report_blob: $blob, at: $at}' \
    --arg d "$destination" --arg remote "$remote" --arg branch "$branch" --arg u "$url" --arg base "$base" \
    --arg c "$commit" --arg observed "$observed" --arg r "$revision" --arg blob "$report_blob" --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"; then
  printf 'omg report: %s published to %s but the receipt was not persisted: %s\n' "$commit" "$destination" "$receipt_error" >&2
  jq -cn --arg d "$destination" --arg c "$commit" --arg base "$base" --arg observed "$observed" --arg e "$receipt_error" \
    '{status: "receipt_failed", destination: $d, commit: $c, base: $base, observed: $observed, error: $e}'
  exit 2
fi
jq -cn --arg d "$destination" --arg c "$commit" --arg base "$base" '{status: "pushed", destination: $d, commit: $c, base: $base}'
