{{define "omg-workflow" -}}
## OMG initiative workflow

Load the `omg-initiative` skill for initiative discussion, visual exploration,
document generation/refinement, approval, or build handoff. Conversation is the
human interface. Resume from the initiative record and artifacts, not remembered
chat. A rig initiative lives in that rig's `docs/initiatives/<id>`; a city
initiative lives in the city's same relative directory.

Only the human approves direction and specs. Those are distinct decisions.
Neither approval, publishing accepted documents, nor Hindsight ingestion starts
a build. You may suggest the build, then wait for the human to explicitly request
its initiation. Record the exact instruction before launching it.

Ship useful, sufficiently reliable software. For substantive recommendations,
weigh credible omission cost under expected use against implementation effort,
delay, and maintenance. Hypothetical possibility alone cannot block completion.
Classify findings as justified required, optional, deferred with an observable
revisit trigger, or rejected. Only required findings block readiness. Requirements
remain binding unless the human changes them. Apply this test to workflow overhead
too. Record useful deferrals in eligible prose, not a bead for every hypothetical.

The approved JSON IR is primary. Read it directly; summaries fill gaps and cannot
override it. Flag conflicting prose and ask about unspecified material decisions.
Before presenting visuals ask what an agent given only the diagram would build.
Check containment, abstraction levels, authority, entry/exit conditions, and loops.
A process and one internal activity must not appear as peer stages. Shared
refinement contains cross-review. Correct misleading topology and regenerate
HTML; prose cannot repair it. Keep OMG instructions outside vendored Archify.

Hindsight is derived context. Git is the document authority. Drafts are proposals;
accepted documents establish direction, not implementation. Build reports describe
the assessed code revision, not forever-current code. Missing reports leave
implementation unconfirmed. Check current documents and code when exact facts matter.
Only eligible authored Markdown ships. JSON/HTML, visual comparisons, screenshots,
receipts, raw chats, mail, and bead chatter stay outside ingestion, including as
attachments. The archivist owns ingestion through the existing Hindsight pipeline.
{{- end}}
