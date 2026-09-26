---
name: omg-development
description: Define and verify the development completion contract for application code, IaC, tests and pipeline changes. Use when authoring or reviewing OMG requirements and acceptance criteria, or planning and reconciling an OMG build.
---

# Development completion contract

Application code and infrastructure code follow the same development boundary.
An environment named dev is still a deployment target for the Terraform that
creates it. The agent delivers code and agreed pre-release evidence; CI/CD owns
promotion, deployment and environment-dependent verification. Findings further
along that process create new work rather than synchronously reopening this build.

## Author the contract

1. Preserve the intended behavior and stable requirement IDs. For each obligation,
   distinguish the deliverable from the evidence and when that evidence is collected.
2. Classify every requirement/AC into exactly one of:

   | Kind | Development obligation |
   | --- | --- |
   | `implementation` | Implement the requested code, configuration or behavior. |
   | `development-check` | Run the agreed development-stage check successfully. |
   | `verification-artifact` | Implement and review a test/script/pipeline job that runs downstream; test the artifact's own behavior locally as appropriate. |
   | `downstream-check` | Record the later execution obligation, its owner and stage. Its result is not a development gate. |

   Split mixed criteria when necessary. Delivering a smoke-test script and
   observing a deployed bucket pass that script are separate obligations.
   Do not turn every downstream check into a new script requirement: authoring an
   artifact is required only when the approved scope calls for it.
3. Describe this split in the PRD, HLD and AC prose. In the owning spec, include one
   fenced `omg-delivery` YAML block. Every ID has one owning spec/block; other docs
   can refer to it. The block is part of the human-reviewed Markdown and pinned
   Git snapshot, not a new frontmatter schema or a replacement requirements doc.

   ````markdown
   ```omg-delivery
   version: 1
   requirements:
     R1:
       kind: implementation
     B01:
       kind: development-check
     S01:
       kind: verification-artifact
     O01:
       kind: downstream-check
       owner: platform-operator
       stage: post-deployment
   ```
   ````

   Here R1 might configure encryption, B01 check the Terraform configuration
   without credentials, S01 deliver the deployment smoke test and its CI wiring,
   and O01 execute that test after promotion. O01 remains pending in the build
   report. A website uses exactly the same distinction.
4. Review both the prose and complete inventory. The block must account for all
   obligations and match their meanings. A failing development check cannot be
   moved downstream without a substantive spec revision and human approval.
   Requirement prefixes such as B/O are labels, not classifier rules.

## Choose development checks

Choose checks by component and the authorized environment, not a separate user
workflow. Application changes may use builds, lint, unit and controlled integration
tests. Terraform may use fmt/validate, provider mocks, module tests, policy checks
and configuration assertions. Pipeline and verification scripts can be tested with
fixtures and controlled success/failure responses. Match the check to the risk.

Even `terraform plan` may refresh state or query providers. Do not assume it is
credential-free or authorized against a real account. A disposable integration
environment is usable only when explicitly supplied and authorized for that stage.
Missing access to a deliberately downstream environment is not a development
failure. Missing evidence for an agreed development check still blocks completion.

## Build and report

The build plan must copy classification, owning source, and downstream owner/stage
from the approved specs. Decompose only the first three kinds into implementation
work, and retain the complete downstream inventory separately. Review evidence for
required verification artifacts includes their committed source paths, testability
and intended pipeline placement. Existence alone does not establish correctness.

Reconciliation accounts for every ID. Development obligations must be implemented
with the required local evidence. Downstream checks are `pending-downstream`, with
their approved owner/stage; they are not "implemented" merely because a procedure
was written. Do not claim deployment, live acceptance, or production readiness.

Follow the repository's agreed review/integration policy. A PR is optional:
local-only work ends in a local handoff, direct-branch work follows its commit/push
policy, and PR-based work follows its review/approval policy. Opening a PR does not
prove approval. Publication never widens deployment permissions. Reports distinguish
verified development, actual publication/integration evidence, and pending downstream
execution. OMG does not replace the CI/CD release pipeline.
