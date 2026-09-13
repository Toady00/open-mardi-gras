Load `omg-initiative`. For initiative `{{initiative}}`, perform a distinct product
cross-review assignment across the ENTIRE snapshot, including HLD, ADRs and specs.
Review against approved IR and binding requirements. Do not edit source documents
during review. Preserve `needs-human` and complete without a false pass if set.

Write a persisted review artifact under the repository's `.omg/` directory with
the reviewed commit, document digest, direction digest, verdict, evidence and
findings. Classify findings as justified required, optional, deferred with a
revisit trigger, or rejected. Only justified required findings block; each needs
credible omission cost and proportionate correction cost. Unresolved scope
decisions return to the human. Do not manufacture a pass by relabeling a binding
requirement violation. Record using:

    gc {{omg_binding}} initiative review {{initiative}} --role product --verdict <pass|required|human> --artifact <absolute-review-path>

For a human verdict also record `initiative decision --note ...`. Record
`gc.outcome=pass` when the review was successfully performed, including a required
verdict. The refinement checker, not step closure, determines review acceptance.
