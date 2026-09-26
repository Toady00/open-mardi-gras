Load `omg-initiative`. For initiative `{{initiative}}`, perform a distinct product
cross-review assignment across the ENTIRE snapshot, including HLD, ADRs and specs.
Review against approved IR and binding requirements. Do not edit source documents
during review. Apply the skill's document-step protocol; an existing human gate
interrupts this assignment without repeating its investigation.

Write a persisted review artifact under the repository's `.omg/` directory with
the reviewed commit, document digest, direction digest, verdict, evidence and
findings. Classify findings as justified required, optional, deferred with a
revisit trigger, or rejected. Only justified required findings block; each needs
credible omission cost and proportionate correction cost. Unresolved scope
decisions return to the human. Do not manufacture a pass by relabeling a binding
requirement violation. Record using:

    gc {{omg_binding}} initiative review {{initiative}} --operation {{operation}} --role product --verdict <pass|required|human> --artifact <absolute-review-path>

For a human verdict add `--note` with the question and recommendation; the command
records the decision and notifies the conversation, even before a snapshot exists.
Complete through the document-step protocol. A required verdict permits another
checked revision; a human verdict interrupts the run instead of spending retries.
Review the prose and structured delivery inventory against `omg-development`.
Reject inappropriate deployment gates and unauthorized deferral of development
obligations. Required downstream test artifacts must remain development deliverables;
their later results must not be synchronous completion gates.
