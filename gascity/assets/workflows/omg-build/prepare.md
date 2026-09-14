This is mechanical preparation for the explicitly requested OMG build, initiative
`{{initiative}}`, operation `{{operation}}`. Read the initiative record to confirm
this operation and its target rig. Run:

    gc {{omg_binding}} prepare-build --rig <operation's rig> --binding {{omg_binding}}

`initiative start` already runs this before dispatch; repeat it here so direct
formula launches and resumed setup use the same verified path. It resolves the
installed native validator, checks its Python/schema dependencies, and provides
the legacy `.gc/scripts/checks/build-artifact-valid.sh` path used by nested native
formulas. Do not copy the validator or its schemas yourself, bypass the gate,
or overwrite a conflicting operator-owned file.

Confirm `{{artifact_root}}`, `{{requirements_path}}`, and `{{approved_root}}` are
absolute paths as supplied by `initiative start`. Do not proceed with relative
artifact paths: controller and worker current directories differ. Record the
preparation result, including checker, wrapper and interpreter, on this bead.
Set `gc.outcome=pass` before closing on success. On failure preserve the diagnostic
and set `gc.outcome=fail`; the post-settlement report must describe the blocked
build. Do not close the workflow root yourself or begin implementation here.
