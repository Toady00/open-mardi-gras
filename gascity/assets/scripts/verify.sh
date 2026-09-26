#!/usr/bin/env bash
# Shared command and native formula check entrypoint. No runtime installation.
# Tools come from the caller's PATH as the controller or worker resolved it;
# this script never prepends its own directories.
set -euo pipefail
fail() { printf 'omg verify: %s\n' "$*" >&2; exit 1; }
for tool in jq yq git shasum python3; do command -v "$tool" >/dev/null || fail "missing $tool"; done
gc_bin="${GC_BIN:-gc}"
stage= root= work= check_bead= workflow= plan=
context=()
while (($#)); do
  case "$1" in
    --stage) stage="${2:?}"; shift 2;;
    --root) root="${2:?}"; shift 2;;
    --work) work="${2:?}"; shift 2;;
    --city|--rig) context+=("$1" "${2:?}"); shift 2;;
    --json) shift;;
    --plan) plan=1; shift;;
    *) fail "unknown argument $1";;
  esac
done
[[ -z "$plan" || "$stage" == report ]] || fail '--plan applies to the report stage only'
gc_call() { "$gc_bin" "$@" ${context[@]+"${context[@]}"} --json; }
bead() { gc_call bd show "$1" | jq -e 'if type == "array" then if length == 1 then .[0] else error("expected one bead") end else . end | select(.id != null)'; }
if [[ -z "$stage" ]]; then
  check_bead=$(bead "${GC_BEAD_ID:?GC_BEAD_ID or --stage required}")
  stage=$(jq -er '.metadata["omg.stage"]' <<<"$check_bead")
  if [[ "$stage" == work ]]; then
    convoy=$(jq -er '.metadata["omg.convoy"]' <<<"$check_bead")
    work=$(gc_call convoy status "$convoy" | jq -er '.children | if length == 1 then .[0].id else error("expected one convoy member") end')
    member=$(bead "$work")
    root=$(jq -er '.metadata["omg.artifact_root"]' <<<"$member")
  else
    root=$(jq -er '.metadata["omg.artifact_root"]' <<<"$check_bead")
  fi
fi
case "$stage" in contract|plan|decompose|work|quality|reconcile|finalize|report) ;; *) fail "unknown stage $stage";; esac
[[ "$root" = /* && -d "$root" ]] || fail 'artifact root must be an existing absolute directory'
hash() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
json() { jq -e 'type == "object"' "$root/$1.json" >/dev/null || fail "missing or invalid $1.json"; }
json baseline
baseline=$(<"$root/baseline.json")
initiative=$(jq -er '.initiative' <<<"$baseline")
operation=$(jq -er '.operation' <<<"$baseline")
city=$(jq -er '.city' <<<"$baseline")
state=$("$gc_bin" bd --city "$city" show "$initiative" --json | jq -er '(if type == "array" then .[0] else . end).metadata["omg.state"] | fromjson')
jq -e --arg op "$operation" --arg root "$root" --argjson b "$baseline" '
  .operations[$op] as $o | $o.kind == "start" and ($o.phase == "launching" or $o.phase == "launched" or $o.phase == "settled")
  and $o.artifact_root == $root and $o.approved.digest == $b.digest and $o.approved.revision == $b.revision
  and $o.repo == $b.repo and $o.approved_root == $b.approved_root
  and $o.publication == $b.publication
' <<<"$state" >/dev/null || fail 'baseline does not match the recorded build approval'
digest=$(jq -acS '.files' <<<"$baseline" | tr -d '\n' | shasum -a 256 | cut -d ' ' -f 1)
[[ "$digest" == "$(jq -r '.digest' <<<"$baseline")" ]] || fail 'baseline file inventory changed'
approved=$(jq -er '.approved_root' <<<"$baseline")
repo=$(jq -er '.repo' <<<"$baseline")
[[ "$approved" = /* && "$repo" = /* ]] || fail 'baseline paths must be absolute'
while IFS= read -r path; do
  [[ "$path" != /* && "$path" != *../* ]] || fail 'unsafe baseline path'
  expected=$(jq -er --arg p "$path" '.files[$p].sha256' <<<"$baseline")
  [[ -f "$approved/$path" && "$(hash "$approved/$path")" == "$expected" ]] || fail "approved file changed: $path"
done < <(jq -r '.files | keys[]' <<<"$baseline")
if [[ -n "$check_bead" && "$stage" != work ]]; then
  jq -e --arg i "$initiative" --arg o "$operation" '.metadata["omg.initiative"] == $i and .metadata["omg.operation"] == $o' <<<"$check_bead" >/dev/null || fail 'check belongs to a different operation'
fi
specs=()
while IFS= read -r source; do specs+=("$source"); done < <(jq -r '.files | to_entries[] | select(.value.type == "spec") | .key' <<<"$baseline")
contract=$(bash "$(dirname "${BASH_SOURCE[0]}")/delivery-contract.sh" "$approved" ${specs[@]+"${specs[@]}"}) || fail 'approved delivery contract is invalid; refine and approve it before rebuilding'
if [[ "$stage" == contract ]]; then printf '{"outcome":"pass"}\n'; exit 0; fi
if [[ "$stage" == report ]]; then
  # Post-settlement reporting completes for failed and partial builds too, so
  # nothing below depends on plan, work, quality or finalization records.
  jq -e --arg op "$operation" '.operations[$op].phase == "settled"' <<<"$state" >/dev/null || fail 'report requires the settled build operation; record initiative settle first'
  docs_repo=$(jq -er '.repo' <<<"$state")
  docs_dir=$(jq -er '.directory' <<<"$state")
  slug=$(jq -er '.slug' <<<"$state") || fail 'initiative record has no slug'
  [[ "$docs_repo" = /* && -d "$docs_repo" ]] || fail 'initiative repository must be an existing absolute directory'
  # The ledger writes docs/initiatives/<slug> with a lowercase slug; accept
  # exactly that shape rather than trusting a concatenated path.
  [[ "$docs_dir" =~ ^docs/initiatives/([a-z0-9][a-z0-9-]*)$ && "${BASH_REMATCH[1]}" == "$slug" ]] || fail 'initiative directory must be docs/initiatives/<slug> for the recorded slug'
  [[ "$operation" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || fail 'operation key is not a safe file name'
  report_path="$docs_dir/reports/$operation.md"
  json report
  report=$(<"$root/report.json")
  jq -e --arg o "$operation" --arg p "$report_path" --argjson s "$state" 'def text: type == "string" and length > 0;
    .operation == $o and .path == $p and (.id | text) and (.sha256 | text) and (.commit | text) and
    (.revision | text) and (.workflow | text) and .workflow == $s.operations[$o].workflow and
    (.build_outcome | IN("pass", "fail", "skipped", "canceled", "unknown"))
  ' <<<"$report" >/dev/null || fail 'report receipt must name this operation, its settled workflow, the canonical report path, identity, hash, commit, assessed revision and build outcome'
  workflow=$(jq -r '.workflow' <<<"$report")
  build_outcome=$(jq -r '.build_outcome' <<<"$report")
  # The receipt repeats the root's terminal gc.outcome exactly; a missing or
  # unrecognised value is reported as unknown, never as a pass.
  bead "$workflow" | jq -e --arg o "$operation" --arg i "$initiative" --arg out "$build_outcome" '
    .status == "closed" and .metadata["gc.kind"] == "workflow" and .metadata["gc.var.operation"] == $o and
    .metadata["gc.var.initiative"] == $i and
    ((.metadata["gc.outcome"] // "") as $actual |
      if $actual | IN("pass", "fail", "skipped", "canceled") then $out == $actual else $out == "unknown" end)
  ' >/dev/null || fail 'report must describe the terminal build root and its actual outcome'
  if [[ -n "$check_bead" ]]; then
    jq -e --arg w "$workflow" '.metadata["gc.root_bead_id"] == $w' <<<"$check_bead" >/dev/null || fail 'report receipt names another workflow'
  fi
  commit=$(jq -r '.commit' <<<"$report")
  revision=$(jq -r '.revision' <<<"$report")
  sha=$(jq -r '.sha256' <<<"$report")
  [[ "$commit" =~ ^[0-9a-f]{40,64}$ && "$revision" =~ ^[0-9a-f]{40,64}$ ]] || fail 'report commit and assessed revision need full commit SHAs'
  [[ "$(git -C "$repo" cat-file -t "$revision" 2>/dev/null)" == commit ]] && git -C "$repo" merge-base --is-ancestor "$revision" HEAD || fail 'assessed revision is not in the current code history'
  if [[ "$build_outcome" == pass ]]; then
    json publication
    jq -e --arg r "$revision" '.revision == $r' "$root/publication.json" >/dev/null || fail 'assessed revision must match the finalized publication receipt'
  fi
  [[ "$(git -C "$docs_repo" cat-file -t "$commit" 2>/dev/null)" == commit ]] && git -C "$docs_repo" merge-base --is-ancestor "$commit" HEAD || fail 'report commit is not in the initiative repository history'
  [[ $(git -C "$docs_repo" rev-list --parents -n 1 "$commit" | wc -w) -eq 2 ]] || fail 'report commit must be a single ordinary commit'
  [[ "$(git -C "$docs_repo" diff-tree --no-commit-id --name-only -r "$commit")" == "$report_path" ]] || fail 'report commit must change only the report'
  [[ "$(git -C "$docs_repo" cat-file -t "$commit:$report_path" 2>/dev/null)" == blob ]] || fail 'report commit does not contain the report'
  blob=$(mktemp "${TMPDIR:-/tmp}/omg-report.XXXXXX"); trap 'rm -f "$blob"' EXIT
  git -C "$docs_repo" show "$commit:$report_path" > "$blob"
  [[ "$(hash "$blob")" == "$sha" ]] || fail 'report hash does not match the committed report'
  [[ -f "$docs_repo/$report_path" && "$(hash "$docs_repo/$report_path")" == "$sha" ]] || fail 'report changed after its recorded commit'
  [[ -z "$(git -C "$docs_repo" status --porcelain --untracked-files=all -- "$report_path")" ]] || fail 'report working copy differs from its commit'
  yq --front-matter=extract -o=json '.' "$blob" 2>/dev/null | jq -e --argjson b "$baseline" --argjson r "$report" '
    .schema_version == 2 and .type == "build-report" and .status == "draft" and .source == "agent" and
    (.title | type == "string" and length > 0) and .id == $r.id and
    (.id | test("^[A-Za-z0-9][A-Za-z0-9._-]*$")) and (.id as $id | all($b.files[]; .id != $id))
  ' >/dev/null || fail 'report needs Hindsight schema 2 agent-authored build-report frontmatter with a unique identity'
  grep -qF -- "$revision" "$blob" && grep -qF -- "$operation" "$blob" || fail 'report must cite the assessed revision and the launch operation'
  # Report publication has no authority of its own. It is authorized only by
  # the build's finalized publication receipt for a passed root, and only when
  # the report lives in the same checkout whose code that receipt published:
  # the destination is exactly the receipt's ref (the PR branch for open_pr,
  # never the default). Every other case completes locally.
  # Policy first: does this run require publication at all? Only then is the
  # receipt's destination validated, and a malformed one is an error, never a
  # quiet fall-back to local.
  destination=
  if [[ "$build_outcome" == pass && "$(cd "$docs_repo" && pwd -P)" == "$(cd "$repo" && pwd -P)" ]] \
     && jq -e '.publication.push or .publication.open_pr' <<<"$baseline" >/dev/null; then
    destination=$(jq -er --argjson b "$baseline" --arg r "$revision" '
      select(.revision == $r and .development == "verified") |
      select(.status == (if $b.publication.open_pr then "pr-open" else "pushed" end)) | (.remote_ref // "")' "$root/publication.json" 2>/dev/null) \
      || fail 'code publication was authorized but the finalized publication receipt does not record it for the assessed revision'
    [[ "$destination" == */* ]] || fail "publication receipt remote_ref must be <remote>/<branch>, got '$destination'"
    remote_name=${destination%%/*}; branch_name=${destination#*/}
    [[ "$remote_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || fail "publication receipt remote_ref names an invalid remote '$remote_name'"
    git check-ref-format --branch "$branch_name" >/dev/null 2>&1 && [[ "$branch_name" != refs/* ]] || fail "publication receipt remote_ref names an invalid branch '$branch_name'"
  fi
  report_blob=$(git -C "$docs_repo" rev-parse "$commit:$report_path")
  if [[ -n "$plan" ]]; then
    jq -cn --arg d "$destination" --arg repo "$docs_repo" --arg c "$commit" --arg r "$revision" --arg p "$report_path" --arg blob "$report_blob" \
      '{outcome: "pass", destination: (if $d == "" then null else $d end), repo: $repo, commit: $c, revision: $r, path: $p, report_blob: $blob}'
    exit 0
  fi
  status=$(jq -r '.status' <<<"$report")
  if [[ -z "$destination" ]]; then
    [[ "$status" == local ]] && jq -e '.remote_ref == null' <<<"$report" >/dev/null || fail 'no build publication receipt authorizes this repository; the report stays local'
    printf '{"outcome":"pass"}\n'; exit 0
  fi
  # This check runs offline, in the controller sandbox. The remote was read and
  # written by `report publish` under the worker's own Git identity, which
  # recorded what it observed in .publication; only that retained proof and
  # the local objects it names are checked here.
  case "$status" in
    pushed) ;;
    failed) fail "authorized report publication to $destination failed and stays recoverable: $(jq -r '[.reason, .error] | map(select(type == "string" and length > 0)) | join(": ")' <<<"$report")";;
    local) fail "report is verified locally; publish it to $destination with report publish, then rerun this check";;
    *) fail "unknown report publication status $status";;
  esac
  jq -e --arg d "$destination" --arg c "$commit" --arg r "$revision" --arg blob "$report_blob" '
    .remote_ref == $d and (.publication | type == "object") and (.publication |
      .destination == $d and .pushed == $c and .observed == $c and .revision == $r and .report_blob == $blob and
      (.base | type == "string" and test("^[0-9a-f]{40,64}$")) and (.url | type == "string" and length > 0))
  ' <<<"$report" >/dev/null || fail "pushed receipt needs report publish evidence for $destination naming this report commit, blob and assessed revision"
  base=$(jq -r '.publication.base' <<<"$report")
  git -C "$docs_repo" cat-file -e "$base^{commit}" 2>/dev/null || fail 'recorded remote base is not available locally; rerun report publish'
  git -C "$docs_repo" merge-base --is-ancestor "$revision" "$base" || fail 'recorded remote base did not contain the finalized assessed revision'
  git -C "$docs_repo" merge-base --is-ancestor "$base" "$commit" || fail 'report commit does not descend from the recorded remote base'
  while IFS= read -r outgoing; do
    [[ -n "$outgoing" ]] || continue
    [[ $(git -C "$docs_repo" rev-list --parents -n 1 "$outgoing" | wc -w) -eq 2 && "$(git -C "$docs_repo" diff-tree --no-commit-id --name-only -r "$outgoing")" == "$report_path" ]] \
      || fail "outgoing commit $outgoing beyond the assessed revision is not a report-only commit"
  done < <(git -C "$docs_repo" rev-list "$base..$commit")
  printf '{"outcome":"pass"}\n'; exit 0
fi
json plan
jq -e 'def text: type == "string" and length > 0;
  (.requirements | type == "array" and length > 0) and
  all(.requirements[]; (.id | text) and (.source | text) and (.quote | text)) and
  ([.requirements[].id] | length == (unique | length))' "$root/plan.json" >/dev/null || fail 'plan needs unique requirements with source and exact quote'
jq -e --argjson contract "$contract" '
  [.requirements[] | {id,kind,source} +
    (if .kind == "downstream-check" then {owner,stage} else {} end)] | sort_by(.id) == $contract
' "$root/plan.json" >/dev/null || fail 'plan inventory/classification must exactly match the approved delivery contract; do not move development obligations downstream'
while IFS= read -r req; do
  source=$(jq -r '.source' <<<"$req")
  jq -e --arg s "$source" '.files[$s].type == "spec"' <<<"$baseline" >/dev/null || fail 'requirement source is not an approved spec'
  yq --front-matter=extract -o=json '.' "$approved/$source" | jq -e '.type == "spec"' >/dev/null || fail 'source is not a spec'
  jq -en --argjson r "$req" --rawfile doc "$approved/$source" '$doc | contains($r.quote) and contains($r.id)' >/dev/null || fail 'requirement quote or ID not found in approved spec'
done < <(jq -c '.requirements[]' "$root/plan.json")
[[ -s "$root/plan.md" ]] || fail 'missing implementation plan'
json plan-review
jq -e --arg h "$(hash "$root/plan.json")" --arg prose "$(hash "$root/plan.md")" '.verdict == "pass" and .plan_sha256 == $h and .prose_sha256 == $prose and .inventory_complete == true' "$root/plan-review.json" >/dev/null || fail 'independent plan review must pass for this plan and requirement inventory'
if [[ "$stage" == plan ]]; then printf '{"outcome":"pass"}\n'; exit 0; fi
json decomposition
jq -e --slurpfile p "$root/plan.json" 'def text: type == "string" and length > 0;
  (.convoy | text) and (.workflow | text) and (.items | type == "array" and length > 0) and
  all(.items[]; (.id | text) and (.requirements | type == "array" and length > 0)) and
  ([.items[].id] | length == (unique | length)) and
  ([.items[].requirements[]] | unique) == ([$p[0].requirements[] | select(.kind != "downstream-check") | .id] | sort) and
  (.downstream | type == "array") and
  ([.downstream[] | {id,owner,stage}] | sort_by(.id)) ==
    ([$p[0].requirements[] | select(.kind == "downstream-check") | {id,owner,stage}] | sort_by(.id))
' "$root/decomposition.json" >/dev/null || fail 'decomposition must assign all development obligations and separately retain the exact downstream inventory'
convoy=$(jq -r '.convoy' "$root/decomposition.json")
workflow=$(jq -r '.workflow' "$root/decomposition.json")
wf=$(bead "$workflow")
jq -e --arg c "$convoy" --arg o "$operation" --arg i "$initiative" '.metadata["gc.kind"] == "workflow" and .metadata["gc.var.operation"] == $o and .metadata["gc.var.initiative"] == $i and .metadata["gc.input_convoy_id"] == $c' <<<"$wf" >/dev/null || fail 'workflow must drain the recorded implementation convoy'
members=$(gc_call convoy status "$convoy")
jq -e --slurpfile d "$root/decomposition.json" '([.children[].id] | sort) == ([$d[0].items[].id] | sort)' <<<"$members" >/dev/null || fail 'convoy membership differs from decomposition'
while IFS= read -r id; do
  row=$(bead "$id")
  jq -e --arg r "$root" --arg o "$operation" '.metadata["omg.artifact_root"] == $r and .metadata["omg.operation"] == $o and (.metadata["gc.kind"] == null)' <<<"$row" >/dev/null || fail "work $id belongs to another run or is a control bead"
done < <(jq -r '.items[].id' "$root/decomposition.json")
if [[ "$stage" == decompose ]]; then printf '{"outcome":"pass"}\n'; exit 0; fi
head=$(git -C "$repo" rev-parse HEAD)
[[ -z "$(git -C "$repo" status --porcelain --untracked-files=all -- . ':(exclude).omg')" ]] || fail 'code must be committed before recording verification'
evidence() {
  local file="$1" revision
  jq -e --arg o "$operation" 'def text: type == "string" and length > 0;
    .operation == $o and (.revision | text) and
    (.checks | type == "array" and length > 0) and
    all(.checks[]; (.command | text) and .exit_code == 0 and (.log | text) and (.sha256 | text))' "$file" >/dev/null || fail "missing passing test evidence: $file"
  revision=$(jq -r '.revision' "$file")
  [[ "$revision" =~ ^[0-9a-f]{40,64}$ ]] || fail 'test evidence needs a full commit SHA'
  git -C "$repo" merge-base --is-ancestor "$revision" "$head" || fail 'tested revision is not in the current code history'
  while IFS= read -r row; do
    log=$(jq -r '.log' <<<"$row")
    [[ "$log" != /* && "$log" != *../* && -s "$root/$log" ]] || fail 'missing test log'
    [[ "$(hash "$root/$log")" == "$(jq -r '.sha256' <<<"$row")" ]] || fail 'test log changed'
  done < <(jq -c '.checks[]' "$file")
}
if [[ "$stage" == work ]]; then
  [[ "$work" =~ ^[a-zA-Z0-9._-]+$ ]] || fail 'work ID required'
  jq -e --arg id "$work" 'any(.items[]; .id == $id)' "$root/decomposition.json" >/dev/null || fail 'work not in decomposition'
  evidence "$root/work/$work.json"
  jq -e --arg w "$work" --arg h "$head" '.work == $w and .revision == $h' "$root/work/$work.json" >/dev/null || fail 'wrong or stale work receipt'
  printf '{"outcome":"pass"}\n'; exit 0
fi
python3 "$(dirname "${BASH_SOURCE[0]}")/verify_execution.py" --root "$root" ${context[@]+"${context[@]}"} >/dev/null || fail 'implementation execution validation failed'
while IFS= read -r id; do
  evidence "$root/work/$id.json"
  jq -e --arg id "$id" '.work == $id' "$root/work/$id.json" >/dev/null || fail 'work receipt belongs to another item'
done < <(jq -r '.items[].id' "$root/decomposition.json")
evidence "$root/tests.json"
jq -e --slurpfile p "$root/plan.json" '
  [.checks[] | (.requirements // [])[]] as $covered |
  ([$p[0].requirements[] | select(.kind == "development-check") | .id] - $covered | length) == 0 and
  ($covered - [$p[0].requirements[] | select(.kind != "downstream-check") | .id] | length) == 0
' "$root/tests.json" >/dev/null || fail 'development-check coverage is missing or claims downstream execution as local evidence'
jq -e --arg h "$head" '.revision == $h' "$root/tests.json" >/dev/null || fail 'integrated tests are stale'
json review
jq -e --arg h "$head" --arg tests "$(hash "$root/tests.json")" '.revision == $h and .tests_sha256 == $tests and .verdict == "pass" and (.findings | type == "array") and all(.findings[]; .required == false or (.required == true and .status == "resolved" and (.bead | type == "string" and length > 0)))' "$root/review.json" >/dev/null || fail 'review is stale, failing, or has unresolved required findings'
while IFS= read -r id; do
  bead "$id" | jq -e --arg o "$operation" '.status == "closed" and .metadata["omg.operation"] == $o' >/dev/null || fail "required finding $id remains open or belongs to another run"
done < <(jq -r '.findings[] | select(.required == true) | .bead' "$root/review.json")
findings=$(gc_call bd list --all --limit 0 --long)
jq -e --arg o "$operation" --slurpfile review "$root/review.json" '
  type == "array" and all(.[] | select(.metadata["omg.operation"] == $o and .metadata["omg.required"] == "true");
    . as $finding | .status == "closed" and any($review[0].findings[]; .required == true and .bead == $finding.id and .status == "resolved"))
' <<<"$findings" >/dev/null || fail 'required finding inventory is unresolved or missing from review'
if [[ "$stage" == reconcile || "$stage" == finalize ]]; then
  json reconciliation
  jq -e --arg h "$head" --arg review "$(hash "$root/review.json")" --slurpfile p "$root/plan.json" '
    .revision == $h and .review_sha256 == $review and
    ([.requirements[].id] | sort) == ([$p[0].requirements[].id] | sort) and
    all(.requirements[];
      . as $r | ($p[0].requirements[] | select(.id == $r.id)) as $p |
      ($r.evidence | type == "string" and length > 0) and
      (if $p.kind == "downstream-check" then
         $r.status == "pending-downstream" and $r.owner == $p.owner and $r.stage == $p.stage
       else $r.status == "implemented" and
         (if $p.kind == "verification-artifact" then
            ($r.artifacts | type == "array" and length > 0) and all($r.artifacts[]; type == "string" and length > 0)
          else true end)
       end))
  ' "$root/reconciliation.json" >/dev/null || fail 'reconciliation is stale, development is incomplete, or downstream status/ownership is misrepresented'
  while IFS= read -r artifact; do
    [[ "$artifact" != /* && "$artifact" != *../* && "$artifact" != .omg/* ]] || fail 'verification artifact must be a repository source path'
    [[ "$(git -C "$repo" cat-file -t "$head:$artifact" 2>/dev/null)" == blob ]] || fail "required verification artifact not committed: $artifact"
  done < <(jq -r '.requirements[] | (.artifacts // [])[]' "$root/reconciliation.json")
fi
if [[ "$stage" == finalize ]]; then
  json publication
  jq -e --arg h "$head" --argjson b "$baseline" '
    .revision == $h and .development == "verified" and
    ($b.publication.push | type == "boolean") and ($b.publication.open_pr | type == "boolean") and
    (if $b.publication.open_pr then
       .status == "pr-open" and (.pr_url | type == "string" and length > 0) and (.remote_ref | type == "string" and length > 0)
     elif $b.publication.push then
       .status == "pushed" and (.remote_ref | type == "string" and length > 0) and (.pr_url == null)
     else .status == "local" and .remote_ref == null and .pr_url == null end) and
    .deployed == false and .pr_approved == false
  ' "$root/publication.json" >/dev/null || fail 'publication must report only the authorized local/push/PR handoff; no deployment or PR-approval claim'
fi
printf '{"outcome":"pass"}\n'
