#!/usr/bin/env bash
# Shared command and native formula check entrypoint. No runtime installation.
# Tools come from the caller's PATH as the controller or worker resolved it;
# this script never prepends its own directories.
set -euo pipefail
fail() { printf 'omg verify: %s\n' "$*" >&2; exit 1; }
for tool in jq yq git shasum python3; do command -v "$tool" >/dev/null || fail "missing $tool"; done
gc_bin="${GC_BIN:-gc}"
stage= root= work= check_bead= workflow=
context=()
while (($#)); do
  case "$1" in
    --stage) stage="${2:?}"; shift 2;;
    --root) root="${2:?}"; shift 2;;
    --work) work="${2:?}"; shift 2;;
    --city|--rig) context+=("$1" "${2:?}"); shift 2;;
    --json) shift;;
    *) fail "unknown argument $1";;
  esac
done
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
case "$stage" in contract|plan|decompose|work|quality|reconcile|finalize) ;; *) fail "unknown stage $stage";; esac
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
