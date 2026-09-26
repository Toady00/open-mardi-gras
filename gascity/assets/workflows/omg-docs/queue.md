Load `omg-initiative` and apply its document-step protocol to initiative
`{{initiative}}`, operation `{{operation}}`. If no human decision is outstanding,
run `gc {{omg_binding}} initiative ready {{initiative}} --operation {{operation}}`.
It requires passing product and technical reviews of the exact current set.

Record the result and complete the step through the protocol. Do not approve
documents or start a build. Settlement sends the readiness result and next action
to the originating conversation; no worker remains busy waiting for the human.
