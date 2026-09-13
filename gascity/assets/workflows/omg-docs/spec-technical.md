Load `omg-initiative`; read initiative `{{initiative}}`, approved IR directly,
PRD, HLD, ADRs, and draft specs. Preserve `needs-human` without authoring if set.
Complete the specs with interfaces, data shapes, compatibility/migration needs,
error behavior, observability and verification obligations proportionate to the
requirements. Preserve requirement identity and product intent. Specs must be
buildable, but implementation planning remains a separate native build stage.

Publish eligible drafts under the agreed policy. Initial generation ALWAYS enters
shared refinement, even without a supplied change request. Do not mark this set
ready yourself. Record paths and revision; set `gc.outcome=pass` before closing.
