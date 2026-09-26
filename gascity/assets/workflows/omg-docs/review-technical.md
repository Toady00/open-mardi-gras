Load `omg-initiative`. For initiative `{{initiative}}`, perform a distinct technical
cross-review assignment across the ENTIRE snapshot, including PRD and product
requirements. Review against approved IR and current code where facts matter.
Do not edit source documents. Apply the skill's document-step protocol; an existing
human gate interrupts this assignment without repeating its investigation.

Persist a review under `.omg/` with exact reviewed commit/digest, direction digest,
verdict, evidence and findings. Apply the same required/optional/deferred/rejected
cost rule as product review. A prior writing assignment earns no presumption of
correctness. Fresh sessions are optional, not a required third reviewer persona.

    gc {{omg_binding}} initiative review {{initiative}} --operation {{operation}} --role technical --verdict <pass|required|human> --artifact <absolute-review-path>

For a human verdict add `--note` with the question and recommendation; the command
records the decision and notifies the conversation, even before a snapshot exists.
Complete through the document-step protocol. Required findings repeat assessment,
affected revision and both reviews; a human verdict interrupts instead of retrying.
Use `omg-development` to check appropriate local evidence for each component,
including Terraform, and exact agreement between prose and delivery blocks.
Review test/pipeline artifacts separately from downstream execution. Concrete
CI/CD promotion and target-environment verification remain outside this development run.
