#!/usr/bin/env bash
set -euo pipefail
# Native controller checks expose the store root; manual agent checks expose
# the rig root. Both must use the prepared rig-owned compatibility wrapper.
ROOT="${GC_STORE_PATH:-${GC_RIG_ROOT:-${GC_BEADS_SCOPE_ROOT:-}}}"
if [[ "$ROOT" != /* ]]; then
    printf '%s\n' 'OMG build artifact check requires an absolute GC_STORE_PATH or GC_RIG_ROOT.' >&2
    exit 1
fi
if [[ ! -x "$ROOT/.gc/scripts/checks/build-artifact-valid.sh" ]]; then
    printf '%s\n' 'OMG build validator is not prepared for this rig; run gc omg prepare-build --rig <rig>.' >&2
    exit 1
fi
exec "$ROOT/.gc/scripts/checks/build-artifact-valid.sh" "$@"
