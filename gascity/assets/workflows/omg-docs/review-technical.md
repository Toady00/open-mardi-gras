Load `omg-initiative`. For initiative `{{initiative}}`, perform a distinct technical
cross-review assignment across the ENTIRE snapshot, including PRD and product
requirements. Review against approved IR and current code where facts matter.
Do not edit source documents. Preserve `needs-human` without a false pass if set.

Persist a review under `.omg/` with exact reviewed commit/digest, direction digest,
verdict, evidence and findings. Apply the same required/optional/deferred/rejected
cost rule as product review. A prior writing assignment earns no presumption of
correctness. Fresh sessions are optional, not a required third reviewer persona.

    gc {{omg_binding}} initiative review {{initiative}} --role technical --verdict <pass|required|human> --artifact <absolute-review-path>

For a human verdict also record `initiative decision --note ...`. Use
`gc.outcome=pass` when the review was performed. Required findings cause the native
check loop to repeat assessment, affected revision and BOTH cross-reviews.
