Load `omg-initiative`; read initiative `{{initiative}}`, its approved IR directly,
discussion summary, and PRD. Apply the skill's document-step protocol.
Create missing HLD/necessary ADRs or reconcile partial drafts without discarding
unaffected content. Author only ADRs justified by consequential decisions. Cover
system boundaries, components, interactions, data ownership, failure behavior,
deployment, security constraints, alternatives and tradeoffs under expected use.
Check current code where exact facts matter. Distinguish approved direction from
pending proposals. Propose a separate candidate IR for scope changes; never
overwrite an approved baseline or infer human approval.
Use `omg-development` to describe the development/release boundary and interfaces
to existing CI/CD. Do not design an AI deployment orchestrator. Distinguish tests
and pipeline jobs to deliver from results collected only after promotion.

Keep drafts Hindsight-compatible. Publish eligible drafts under the agreed policy.
Record paths and revision; complete through the document-step protocol.
