#!/usr/bin/env bash
set -euo pipefail
exec python3 -c '
import json, os, subprocess, sys
result = subprocess.check_output(["gc", "bd", "show", os.environ["GC_BEAD_ID"], "--json"])
bead = json.loads(result)
if isinstance(bead, list):
    bead = bead[0]
meta = bead["metadata"]
sys.exit(subprocess.call(["gc", meta["omg.binding"], "initiative", "check", meta["omg.initiative"]]))
'
