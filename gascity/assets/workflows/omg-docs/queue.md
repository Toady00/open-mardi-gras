Read initiative `{{initiative}}`. If `needs-human`, preserve that verdict. Otherwise
run `gc {{omg_binding}} initiative ready {{initiative}}`; it requires matching
passing product and technical reviews of the exact current document set.

This leaves a persistent record for a later conversation. Do not wait in an agent
polling loop. Do not approve documents, change their status to accepted, or start
a build. Draft publication is independent. Record the result and set
`gc.outcome=pass` before closing.
