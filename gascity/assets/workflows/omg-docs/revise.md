Load `omg-initiative`; read initiative `{{initiative}}` and the whole set, including
the product assessment and earlier required findings. This is the successive
technical assessment/writing assignment inside shared refinement. Apply the
skill's document-step protocol.

Assess technical impact against approved IR, requirements and current code. Revise
affected HLD, ADRs and specs, preserving product requirements. Apply the same cost
rule to corrections and review overhead. Any missing human decision returns via
`initiative decision --operation {{operation}} --note ...`, not an invented approval.
Apply `omg-development` to the technical ACs and each spec's omg-delivery inventory.
Correct mixed-stage criteria and include downstream owner/stage. Repository
publication policy may be local-only, direct-branch or PR-based; it never turns
live infrastructure verification into a development gate.

Validate the whole document set with the Hindsight schema. Commit only intended
initiative files and snapshot the resulting exact commit:

    gc {{omg_binding}} initiative snapshot {{initiative}} --operation {{operation}} --revision <full-commit-sha>

The next two steps are distinct cross-review assignments, not writing assignments.
Publish drafts under the agreed policy independently of readiness. Record revision
and paths on the bead. Complete through the document-step protocol.
