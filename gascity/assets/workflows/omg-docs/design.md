Load `omg-initiative`; read initiative `{{initiative}}`, its approved IR directly,
discussion summary, and PRD. Preserve `needs-human` without authoring if set.
Write the initial HLD and only ADRs justified by consequential decisions. Cover
system boundaries, components, interactions, data ownership, failure behavior,
deployment, security constraints, alternatives and tradeoffs under expected use.
Check current code where exact facts matter. Distinguish approved direction from
pending proposals. Propose a separate candidate IR for scope changes; never
overwrite an approved baseline or infer human approval.

Keep drafts Hindsight-compatible. Publish eligible drafts under the agreed policy.
Record paths and revision; set `gc.outcome=pass` before closing.
