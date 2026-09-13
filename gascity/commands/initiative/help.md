# initiative

Durable records behind OMG conversations. Agents use this command on the human's
behalf; approval and explicit build initiation are separate.

```text
gc omg initiative init --slug SLUG [--title TITLE] [--rig RIG]
gc omg initiative list
gc omg initiative show BEAD
gc omg initiative direction BEAD --revision SHA --file IR --file HTML --authority TEXT
gc omg initiative generate BEAD --authority TEXT
gc omg initiative refine BEAD --authority TEXT
gc omg initiative revise BEAD
gc omg initiative snapshot BEAD --revision SHA
gc omg initiative review BEAD --role product|technical --verdict pass|required|human --artifact PATH
gc omg initiative ready BEAD
gc omg initiative decision BEAD --note TEXT
gc omg initiative accept BEAD --authority TEXT
gc omg initiative start BEAD --rig RIG --authority TEXT [--push true] [--open-pr true]
gc omg initiative materialize BEAD [--input specs]
gc omg initiative recover BEAD --operation KEY --workflow ROOT --authority TEXT
gc omg initiative settle BEAD --operation KEY --workflow ROOT
```

Use the actual import binding in place of `omg`. For launch operations under a
different binding also pass `--binding <name>`. All output is JSON except
`materialize`, which prints the absolute frozen-input directory. Its default is
approved direction; `--input specs` selects the accepted document snapshot.

`--authority` records the human's actual instruction and a session/message
reference. It is an audit record, not authentication. Agents must not invent it.
`direction` requires adjacent same-stem JSON/HTML pairs at an exact commit. It
preserves earlier approved baselines. `accept` records approval without changing
files or launching work; publish accepted statuses separately. `start` requires
explicit build authority and returns an existing receipt for repeated requests
against the same accepted revision and rig.

Init infers the initiating rig from `GC_RIG`, otherwise uses the city. An explicit
empty `--rig ''` selects city scope. The owner repository must be a Git root.
Records use the city work store and native metadata CAS; publication uses the
owner repository's normal Git policy. Runtime requires `gc`, Git, Python 3,
Mike Farah's `yq`, and a working city Beads backend with metadata CAS support.

If launch acknowledgement is lost, the record remains `launching`. Do not repeat
the external operation blindly. Inspect native state and recover the matching
workflow. A conflict or transport failure exits nonzero. No background process
or custom dispatcher is started by this command.
