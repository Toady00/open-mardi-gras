# The OMG Workflow — Flowcharts

A descriptive map of the instruments in `opencode/` and the Gas City pack in
`gascity/`, drawn from their current text. The Gas City workflow below is separate
from the older OpenCode workflow in the numbered sections.

**This document is derived, not authoritative.** The instruments are the source of
truth. If a diagram and an instrument disagree, the instrument is right and this
file is stale. It is a reading aid and a review surface — not a spec, and nothing
should be built from it.

## Gas City initiative workflow

Conversation is the human interface. Initiative records use native Beads metadata
CAS and survive agent sessions. Rig-initiated documents live in that rig's
`docs/initiatives/<id>`; city-initiated documents use the city's same directory.
Approval and build initiation are separate human decisions.

Both PM and architect receive the shared `omg-hindsight` prompt fragment in city
and rig sessions. They first list available mental models and fetch the content
of those relevant to the conversation. As soon as they identify useful background
questions, they reflect; new context and questions can prompt further reflection
during the same conversation. Retrieved memory informs discussion and review,
while current Git documents and code remain authoritative for exact facts.

```mermaid
flowchart TD
    TALK["Human discusses initiative with PM or architect<br/>JSON IR, generated HTML, living Markdown summary"]
    IR{{"Human approves exact rendered IR revision"}}
    INITIAL["omg-docs: generate once<br/>PRD, HLD, necessary ADRs, successive specs"]
    EDIT["Later substantive edit<br/>invalidate readiness"]
    REFINE["omg-refine: one shared process<br/>Whole-set assessment and affected revisions<br/>Distinct PM and architect cross-review inside refinement"]
    NEED{{"Unresolved decision, candidate IR,<br/>or required findings after bounded attempts"}}
    QUEUE["Persistent approval-ready record<br/>Exact revision; authoring session can finish"]
    SPECS{{"Human approves selected specs through conversation"}}
    ACCEPTED["Accepted record and status publication<br/>No build launch"]
    START{{"Human explicitly requests a build in a selected rig"}}
    INTENT["Persist launch intent before native dispatch<br/>Repeated request returns receipt;<br/>ambiguous acknowledgement requires recovery"]
    RECOVER{"Launcher exited; inspect exact launch store<br/>Does workflow evidence exist?"}
    BIND["Recover the matching native workflow"]
    ABANDON["Human-authorized abandonment of failed launch<br/>Preserve attempt and source in history; no dispatch"]
    INSPECT["Resolve store access or inspect relocated graph storage<br/>Keep launch unresolved"]
    NATIVE["omg-build extends native build-from-plan-base<br/>Pinned specs to native requirements adapter<br/>Plan, decompose, implement, review and repair"]
    RECON["Reconcile every requirement against pinned specs<br/>Implementation and verification evidence; deviations and authority"]
    FINAL["Native finalization and optional code publication"]
    REPORT["Post-settlement architect report<br/>Success, partial, blocked and failed builds<br/>Assessed SHA; implemented vs reviewed vs published"]
    SHIP["Canonical remote Markdown revisions<br/>Existing Hindsight pipeline and receipts"]
    TALK --> IR --> INITIAL --> REFINE
    EDIT --> REFINE
    REFINE -->|"needs human"| NEED
    NEED -->|"decision; reconcile against approved baseline"| REFINE
    REFINE -->|"both lenses pass exact revision"| QUEUE
    QUEUE --> SPECS --> ACCEPTED
    SPECS -->|"changes"| EDIT
    ACCEPTED -.->|"later, separate request"| START
    START --> INTENT --> NATIVE --> RECON --> FINAL --> REPORT
    INTENT -->|"failed or lost acknowledgement"| RECOVER
    RECOVER -->|"yes, including closed or partial work"| BIND
    RECOVER -->|"no; exact-store absence confirmed"| ABANDON
    RECOVER -->|"cannot prove absence"| INSPECT
    ABANDON -.->|"new explicit request"| START
    NATIVE -->|"failure or blocked"| REPORT
    RECON -->|"required violation"| REPORT
    FINAL -->|"failure"| REPORT
    TALK -.->|"authored summary"| SHIP
    REFINE -.->|"drafts can publish repeatedly"| SHIP
    ACCEPTED -.-> SHIP
    REPORT --> SHIP
```

Native formula checks repeat the complete refinement assignment, including both
reviews, up to three automatic attempts. Exhaustion returns the unresolved issue
to the human, not a false pass. Native scope teardown preserves reporting after
build failure and after the root settles. A terminal build root therefore does
not prove that its reporting assignment finished.

Readiness checks compare the reviewed Git inventory and bytes without invoking
`yq`; unresolved human decisions cannot be marked ready. Native check executables
resolve from pack asset layers. Abandonment requires confirmation that the original
launcher and its children have exited. Store errors and concurrent record changes
prevent it. City launches with relocated graph stores require native storage
inspection rather than inferring absence from an incomplete federated listing.

Hindsight receives eligible authored Markdown only. IR, HTML, comparison evidence,
raw reviews, chat, mail and bead chatter are excluded, including attachments.
Neither publication nor ingestion approves direction or starts implementation.

## Conventions used in every diagram

| Shape | Meaning |
|---|---|
| `[rectangle]` | An action an agent or script performs. It may branch on its own mechanical outcome — succeeded, failed, found something |
| `{diamond}` | A judgment the agent makes, or a condition it reads off the graph |
| `{{hexagon}}` | A human gate — the process pauses for a person |
| `([stadium])` | A terminal state |

**Dependency edges are always stated as "X waits on Y."** This matters: `bd dep add
<blocked> <blocker>` puts the *waiting* bead first, and getting the direction
backwards is the single most common wiring error in these instruments.

---

## 1. The lifecycle, end to end

Four largely independent processes. Only the middle two are the epic loop.

```mermaid
flowchart TD
    subgraph SETUP["Setup — once per repo"]
        ONB["/omg-onboard solo / centralized / satellite<br/>omg-onboarder"]
        HS["/omg-hindsight-setup<br/>omg-hindsight-architect"]
    end

    subgraph DOCS["Doc lane — produces the spec"]
        TPM["tpm-alignment formula<br/>omg-technical-program-manager"]
        SPEC["/omg-spec<br/>omg-product-manager"]
        SREV["/omg-spec-review<br/>omg-architect"]
        SHARD["/omg-spec-harden<br/>omg-implementation-writer"]
        SDEST["Author a relocation's destination<br/>omg-product-manager — handoff, spec<br/>omg-architect — design doc, ADR"]
        SNOF{{"HUMAN GATE<br/>destination type has no template —<br/>oc-smith authors one"}}
    end

    PLAN["/omg-decompose spec-path<br/>omg-decomposer"]
    G1{{"HUMAN GATE<br/>review the bead graph"}}
    BUILD["/omg-build epic-id<br/>omg-foreman"]
    DONE(["Epic closed"])
    G2{{"HUMAN GATE<br/>docs to Hindsight sync"}}

    ONB --> DOCS
    HS -.->|"optional"| DOCS
    TPM -->|"fans out into per-spec work"| SPEC
    SPEC --> SREV
    SREV -->|"findings change product scope"| SPEC
    SREV -->|"buildable; ADRs written"| SHARD
    SHARD -->|"repeatable pass"| SHARD
    SHARD -->|"a relocation needs a destination<br/>that does not exist yet"| SDEST
    SDEST -->|"pass resumes"| SHARD
    SHARD -->|"that destination's type<br/>has no template"| SNOF
    SNOF -.->|"template authored; re-run"| SHARD
    SHARD --> PLAN
    PLAN --> G1
    G1 --> BUILD
    BUILD --> DONE
    DONE --> G2
```

Two things worth noticing here:

- **Decomposition is handed a spec, not an epic.** `/omg-spec` explicitly creates
  no bead. The epic is minted at decomposition, once the spec and its ADRs are settled.
- **Nothing reaches durable memory automatically.** The docs→Hindsight sync is a
  human-invoked command, and a document ships only if it carries a `hindsight`
  frontmatter block. Everything else stays Git-only.

---

## 2. Plan phase — `/omg-decompose`

```mermaid
flowchart TD
    A(["/omg-decompose spec-path"]) --> B["decompose-mint.sh<br/>resolve spec, require frontmatter id,<br/>mint or reuse epic, mint ADR beads"]
    B -->|"failure"| BSTOP(["STOP — report to the human,<br/>take no further action"])
    B -->|"ok"| C{"epic had beads<br/>already?"}
    C -->|"no"| C1["mode = fresh mint"]
    C -->|"yes"| C2["mode = refinement"]
    C1 --> D
    C2 --> D
    D["Dispatch omg-test-planner<br/>epic id + mode — plan pass"]
    D --> E["Dispatch omg-build-planner<br/>epic id + mode"]
    E --> F["Decomposer reviews the settled graph<br/>bd children, bd comments<br/>cross-slice seams only"]
    F --> G{"problems found?"}

    G -->|"verification problems"| H["Dispatch omg-test-planner<br/>targeted-concern mode"]
    H --> I{"did the test set change?"}
    I -->|"yes"| J["Dispatch omg-build-planner<br/>refinement mode"]
    I -->|"no"| K
    J --> K{"build concerns outstanding?"}
    G -->|"build problems only"| K
    K -->|"yes"| L["Dispatch omg-build-planner<br/>targeted-concern mode"]
    K -->|"no"| F
    L --> F

    G -->|"none"| M["ensure-terminal-beads.sh<br/>exactly one Review, one Write build report"]
    M -->|"duplicate titles or missing body"| MSTOP["Fix the named failure and rerun"]
    MSTOP --> M
    M -->|"ok"| N["bd swarm validate epic<br/>bd dep tree --direction up epic"]
    N --> O{{"HUMAN GATE<br/>show the final structure,<br/>stop for review"}}
```

**The four concerns the decomposer hunts** — note that two of them look for *too
much* verification, which is the change this repo shipped in the verification-economy
work:

1. A spec obligation with an implementation bead that no test, gate, or review
   obligation covers, and no recorded no-verification decision explains.
2. A test bead that blocks no implementation bead.
3. Verification planned out of proportion to what it protects.
4. Verification whose mechanism does not fit its artifact.

**The re-review loop has no bound.** It runs until a review pass finds nothing.

---

## 3. The confidence planner's four outcomes

This is the vocabulary the planner reasons in. It is also where the workflow's
sharpest current gap lives, so the diagram traces each outcome all the way to
whatever actually discharges it.

```mermaid
flowchart TD
    OBL["A spec obligation<br/>that needs verification"] --> P{"Proportionality:<br/>cost to build, run, and maintain<br/>vs. cost of the failure it catches"}

    P -->|"executable code, and the<br/>ecosystem has real test tooling"| T["AUTOMATED TEST"]
    P -->|"declarative or config artifact"| GT["DETERMINISTIC GATE<br/>compiler, type checker, linter,<br/>validator, schema, policy check"]
    P -->|"prose — runbooks, docs,<br/>specs, agent instruments"| RO["REVIEW OBLIGATION<br/>a reading against a stated standard"]
    P -->|"costs more than it prevents"| NV["RECORDED NO-VERIFICATION<br/>DECISION"]

    T --> TB["Mint a test bead<br/>agent=omg-tester, parent=epic"]
    TB --> TW["IMPL waits on TEST"]
    TW --> TD(["Dispatched, authored, closed.<br/>ENFORCED"])

    GT --> GC["Comment on the epic"]
    GC --> GD(["Nothing mints a bead for it,<br/>routes it, or checks it ran.<br/>NOT ENFORCED"])

    RO --> RC["Comment on the epic"]
    RC --> RD(["The reviewer reads changed files,<br/>never the epic's recorded obligations.<br/>NOT ENFORCED"])

    NV --> NC["Comment on the epic"]
    NC --> ND(["Nothing is required.<br/>CORRECT BY DEFINITION"])
```

Hard rules bounding the top of this diagram:

- An automated test may be planned **only for executable code**, and **only** with
  the test framework and runner the language community already uses. The workflow
  never invents a testing methodology, harness, executor, or assertion framework.
- Prose never gets an automated test of its meaning, **including tests over its
  embedded code fences**. If a prose procedure's correctness is load-bearing enough
  to warrant executable verification, that is a signal the procedure should be a
  script — a design finding to raise, not a reason to test the prose.

See section 12, *What these diagrams expose*, for why the two "NOT ENFORCED"
outcomes are a live problem rather than a cosmetic one.

---

## 4. Canonical bead topology

The shape every epic converges on, before findings perturb it.

```mermaid
flowchart TD
    EPIC["EPIC — minted from the spec"]
    ADR["ADR beads — one per adr whose<br/>produced_for equals this spec.<br/>relates-to only, CLOSED at mint time.<br/>Not a child. Blocks nothing."]
    TEST["TEST bead<br/>agent=omg-tester"]
    IMPL["IMPL bead<br/>agent=omg-builder<br/>metadata: test_beads"]
    REVIEW["Review<br/>agent=omg-reviewer"]
    REPORT["Write build report<br/>agent=omg-reviewer"]

    EPIC -.->|"relates-to"| ADR
    EPIC -.->|"parent of"| TEST
    EPIC -.->|"parent of"| IMPL
    EPIC -.->|"parent of"| REVIEW
    EPIC -.->|"parent of"| REPORT

    IMPL ==>|"waits on"| TEST
    REVIEW ==>|"waits on"| IMPL
    REPORT ==>|"waits on"| REVIEW
```

- Solid double arrows are dependency edges; dotted arrows are parentage or a
  non-blocking `relates-to` link.
- **Review waits on every non-terminal child.** Report waits on Review. Nothing
  waits on Report.
- ADR beads are a deliberate exception: they are minted `relates-to` the epic and
  **closed immediately** — "a recorded ADR is a decided decision, not open work" — so
  they never enter the ready queue and never block anything. They exist to carry the
  decision and its `hindsight` state, not to be worked.
- Test beads that touch the same files are serialized: the later waits on the earlier.
- A behavior with no planned test gets no `test_beads` stamp on its implementation
  bead, and the builder falls back to the description plus the review bead's
  full-suite run.
- **A child bead blocks its epic regardless of wiring.** This is why non-blocking
  findings must never be filed as children — see section 10, *Review, findings,
  and the fix loop*.

---

## 5. Build phase — the foreman's loop

```mermaid
flowchart TD
    A(["/omg-build epic-id"]) --> B["Read build.mode from .workflow.yaml<br/>default one_agent"]
    B --> C["Orphan scan<br/>bd list --parent epic --status in_progress"]
    C -->|"orphans found"| REC["RECOVERY PATH — see section 6"]
    C -->|"clean"| D["bd ready --parent epic"]
    REC --> D
    D --> E{"ready queue empty?"}

    E -->|"no"| F["Select bead or beads<br/>per the build mode"]
    F --> G["bd state bead-id agent --json"]
    G -->|"no agent name"| GSTOP(["STOP — this is a defect.<br/>Surface it."])
    G -->|"agent resolved"| H["Dispatch to the agent the label names.<br/>Routing is by label only."]
    H --> I["Worker returns CLOSED<br/>or REOPENED AND BLOCKED"]
    I --> D

    E -->|"yes"| J{"bd epic close-eligible?"}
    J -->|"yes"| K(["Close the epic"])
    J -->|"no"| L["Any child still in_progress<br/>is crash-stranded"]
    L --> REC
```

**The foreman never trusts a worker's summary as the record of truth.** After every
dispatch it re-reads `bd ready`. The queue owns ordering and blocking; the foreman
holds no state of its own.

**The loop stops only** when the epic closes, or when the next required action hits
a real blocker: a human gate, a missing `agent` label, a denied permission, or an
unrecoverable tool failure. A turn boundary is never such a blocker.

### The three build modes

| Mode | Selection | Behavior |
|---|---|---|
| `one_agent` (default) | `.workflow.yaml` `build.mode` | Sequential. Reuses one `task_id` for `omg-builder` only; every other agent gets fresh context. |
| `one_agent_fresh_context` | `.workflow.yaml` | Sequential. Every bead gets a brand-new subagent session; `task_id` is never reused. |
| `multi_agents` | `.workflow.yaml` | Fans out across every ready bead concurrently, waits for all to return, then loops. **Experimental** — concurrent writes can clobber, so shared-file work must be blocked apart. |

### The dispatch lifecycle contract

Every worker dispatch is **a single turn**, and the bead comes back in exactly one
of two states:

```mermaid
flowchart LR
    D["Dispatch"] --> S{"terminal state"}
    S --> A(["CLOSED"])
    S --> B(["REOPENED AND BLOCKED<br/>by a new bead"])
    S -.->|"contract violation"| C["in_progress"]
    S -.->|"contract violation"| E["reopened and UNBLOCKED"]
```

The two violation states are what strand a bead. `in_progress` looks like live work
to the foreman and gets recovered as a crash; reopened-unblocked re-enters the ready
queue immediately and re-dispatches the same unfinished work forever.

---

## 6. Recovery path

```mermaid
flowchart TD
    A["A child bead left in_progress<br/>by an interrupted run"] --> B{"does it already carry a<br/>RECLAIMED: comment?"}
    B -->|"yes — this is the second failure"| C["bd gate create --type=human --blocks id<br/>reason: twice-failed recovery"]
    C --> D(["HUMAN GATE — stop for this bead.<br/>Never dispatch a third time."])
    B -->|"no"| E["bd comment id RECLAIMED: ..."]
    E --> F["bd update id --status open, clear assignee"]
    F --> G["Re-dispatch fresh by the existing agent label"]
```

Recovery adds **no routing logic**. The `agent` label still decides the handler. A
worker picking up a bead marked `RECLAIMED:` first checks whether the work is already
complete — and if so, just closes it.

---

## 7. The builder's flow

```mermaid
flowchart TD
    A["Foreman dispatches omg-builder"] --> B["bd update id --claim<br/>claim FIRST"]
    B --> C["bd show id — read the full bead"]
    C --> D{"does bead metadata<br/>carry test_beads?"}
    D -->|"yes"| E["Read run_selector off the test bead.<br/>NEVER read the test source."]
    D -->|"no"| F["Build to the description.<br/>The review bead's full-suite run<br/>is the backstop."]
    E --> G["Implement exactly what the bead describes"]
    F --> G
    G --> H["Run only the focused target"]
    H --> I{"outcome"}

    I -->|"green"| J["File any discovered work<br/>as beads, immediately"]
    J --> K["Comment: deviations, discoveries,<br/>decisions, discovered-work ids"]
    K --> L(["bd close — CLOSED"])

    I -->|"the planned test is<br/>wrong or impossible"| M["File a summons bead<br/>agent=omg-test-planner"]
    M --> N["MY BEAD waits on SUMMONS<br/>reset mine to open, clear assignee"]
    N --> O(["REOPENED AND BLOCKED"])

    I -->|"I broke a test from<br/>an earlier epic"| P["file-adjudication.sh<br/>mints the PM adjudication bead"]
    P --> Q["MY BEAD waits on ADJUDICATION<br/>reset mine to open"]
    Q --> O

    I -.->|"FORBIDDEN"| X["Edit the test<br/>or force it green"]
```

The two escape hatches are the whole point of this diagram. A builder that cannot
make a test pass has exactly two legitimate moves — summon the confidence planner, or
file for PM adjudication — and one forbidden one.

---

## 8. The tester's flow

```mermaid
flowchart TD
    A["Foreman dispatches omg-tester"] --> B{"does the stack have<br/>conventional test tooling?"}
    B -->|"no"| C["STOP. Never invent a methodology,<br/>harness, executor, or assertion framework."]
    C --> ESC["File a bead<br/>agent=omg-test-planner"]
    B -->|"yes"| D{"is there a guide in<br/>test-writing/guides?"}
    D -->|"no"| E["Tell the user no guide exists.<br/>Use universal principles plus<br/>the local suite's conventions."]
    D -->|"yes"| F["Follow the stack guide"]
    E --> G
    F --> G{"which way does<br/>the wiring point?"}
    G -->|"TEST blocks IMPL"| H["Write the test.<br/>Observe it FAIL against the<br/>unimplemented behavior."]
    G -->|"IMPL blocks TEST"| I["Write and run the post-fix test"]
    H --> J["Stamp run_selector onto the test bead"]
    I --> J
    J --> K(["bd close — CLOSED"])

    G -->|"this verification costs more<br/>to build, run, and maintain<br/>than the failure it prevents"| ESC
    ESC --> L["MY BEAD waits on the planner bead<br/>reset mine to open, clear assignee"]
    L --> M(["REOPENED AND BLOCKED"])
```

The tester is the **sole test author** in the workflow. Builders write no tests; the
confidence planner mints them and the foreman dispatches them here.

---

## 9. Summons resolution — `summons-stuck-builder`

One summons file serves two escalators, and almost every branch resolves differently
depending on which one it was. That polymorphism is the reason this path is worth its
own diagram.

```mermaid
flowchart TD
    S["Summons bead<br/>agent=omg-test-planner"] --> R{"who escalated?"}
    R -->|"BUILDER — a planned test<br/>is wrong or impossible"| RB["The disputed test bead is a<br/>DIFFERENT, already-closed bead.<br/>The waiting bead is the builder's fix."]
    R -->|"TESTER — the verification costs<br/>more than it prevents"| RT["The disputed test bead IS<br/>the escalating bead.<br/>Waiting bead and disputed bead are one."]

    RB --> D{"the planner's ruling"}
    RT --> D

    D -->|"UPHOLD"| U["Comment the waiting bead.<br/>No wiring changes at all.<br/>It returns to the queue as planned."]

    D -->|"RE-PLAN as a corrected test"| RP{"escalator?"}
    RP -->|"builder"| RPB["Mint a replacement TEST, agent=omg-tester.<br/>WAITING BEAD waits on TEST.<br/>The closed wrong assertion stays in the suite."]
    RP -->|"tester"| RPT["Re-title and re-describe the SAME bead in place.<br/>No new bead. Never block it on its own replacement."]

    D -->|"RE-PLAN as a gate or<br/>review obligation"| RG{"escalator?"}
    RG -->|"builder"| RGB["Comment the epic.<br/>Mint a REMOVAL bead, agent=omg-tester.<br/>WAITING BEAD waits on REMOVAL."]
    RG -->|"tester"| RGT["Comment the epic.<br/>Close the waiting bead directly.<br/>No removal bead — nothing was authored."]

    D -->|"RETIRE the verification"| RE{"escalator?"}
    RE -->|"builder — test already in suite"| REB["Mint a REMOVAL bead, agent=omg-tester.<br/>WAITING BEAD waits on REMOVAL."]
    RE -->|"tester — nothing authored yet"| RET["Comment the epic.<br/>Close the waiting bead directly."]

    U --> Z(["Close the summons — always"])
    RPB --> Z
    RPT --> Z
    RGB --> Z
    RGT --> Z
    REB --> Z
    RET --> Z
    Z --> INV["INVARIANT: never leave a bead open<br/>that nothing will ever close.<br/>The builder path leaves the waiting bead open<br/>only when it now waits on a new bead."]
```

Why the builder and tester branches diverge so sharply: for a **builder**, the
waiting bead is a fix that legitimately stays open and waits. For a **tester**, the
waiting bead is the very thing being ruled on. Same variable, opposite roles — which
is exactly the ambiguity that produced two epic-wedging bugs before the placeholders
were split apart.

---

## 10. Review, findings, and the fix loop

```mermaid
flowchart TD
    A["Review bead becomes ready:<br/>every non-terminal child is done"] --> B["Foreman dispatches omg-reviewer"]
    B --> C["Identify changed scope<br/>git diff, bd show epic"]
    C --> D["Read every changed file in full"]
    D --> E["Run the full suite when<br/>the bead body says to"]
    E --> F["Classify each finding P0 to P4"]
    F --> G{"priority"}

    G -->|"P2, P3, P4"| I["Standalone bead OUTSIDE the epic:<br/>no --parent, no dep on the review,<br/>no agent label, discovered-from only"]

    G -->|"P0 or P1 — blocks the epic"| H{"what is the<br/>finding's subject?"}
    H -->|"code"| J["Mint FIX, agent=omg-builder<br/>Mint TEST, agent=omg-tester<br/>FIX waits on TEST<br/>REVIEW waits on FIX"]
    H -->|"prose or declarative"| K["Mint FIX only — no test bead.<br/>REVIEW waits on FIX."]
    H -->|"it broke an earlier<br/>epic's guarantee"| L["file-adjudication.sh<br/>REVIEW waits on ADJUDICATION<br/>see section 11"]

    I --> M{"any blocking findings?"}
    J --> M
    K --> M
    L --> M
    M -->|"no"| N(["Close the review bead"])
    M -->|"yes"| O["Reopen the review, status open.<br/>It re-enters ready when<br/>its blockers close."]
    O --> A
    N --> P["Write build report becomes ready"]
```

### The priority scale

| P | Definition | Blocks? |
|---|---|---|
| P0 | Security vulnerability, data-loss risk, crash in the happy path | Yes |
| P1 | Correctness bug in what this epic promises, or a failure whose recovery costs more than the fix | Yes |
| P2 | Performance, missing important tests, poor naming | No |
| P3 | Style, minor refactor, docs gaps | No |
| P4 | Nits, suggestions, nice-to-haves | No |

### Regression by default

For a blocking finding whose subject is **code**, the regression test is minted
alongside the fix at filing time and authored **before** it — so it is observed
failing against the reproducible defect, which is the only evidence a regression test
catches anything. No separate verification-planning dispatch is spent deciding
whether to test it: setting the finding to P0/P1 *was* the blast-radius judgment, and
re-deciding it from less context is the loop's principal amplifier.

For prose or a declarative artifact, no test bead is minted at all — the
review-and-fix cycle is itself the verification.

### The report and epic close

```mermaid
flowchart TD
    A["Write build report bead<br/>agent=omg-reviewer"] --> B["Read every child bead's comments"]
    B --> C["Synthesize against<br/>doc-templates build-report template"]
    C --> D["Write to docs-base/build-report/id.md<br/>including a hindsight frontmatter block"]
    D --> E(["Close the report bead"])
    E --> F["Ready queue drains"]
    F --> G["bd epic close-eligible"]
    G --> H(["Epic closes"])
    H -.->|"separate, human-invoked"| I{{"docs to Hindsight sync"}}
```

The report bead does **not** close the epic, and writing the report ships nothing.
The report contains: Summary, Deviations from Spec, Discovered Constraints, Decisions
Made During the Build, Discovered Work, Outcome.

---

## 11. Adjudication — when a change collides with a prior guarantee

The product manager owns the question "was that behavior still supposed to hold?" It
is a product judgment, not a build defect for someone else to patch around.

```mermaid
flowchart TD
    T["A change collides with a guarantee<br/>an earlier epic made"] --> W{"discovered when?"}
    W -->|"mid-build, on a failing test"| AB["adjudicate-build.md"]
    W -->|"at review time, after<br/>the epic's work closed"| AR["adjudicate-review.md"]
    AB --> PM["Dispatch omg-product-manager.<br/>Consult HINDSIGHT for why the prior<br/>guarantee exists before ruling.<br/>Never rule from own context alone."]
    AR --> PM
    PM --> RULE{"the ruling"}

    RULE -->|"THE PROMISE STANDS<br/>build path"| S1["Comment the implementation bead.<br/>It resets open and rebuilds to honor it."]
    RULE -->|"THE PROMISE STANDS<br/>review path"| S2["Mint FIX, agent=omg-builder<br/>Mint SUMMONS, agent=omg-test-planner<br/>FIX waits on SUMMONS<br/>REVIEW waits on FIX"]
    RULE -->|"THE PROMISE IS STALE<br/>build path"| S3["Mint TEST_UPDATE, agent=omg-tester<br/>BLOCKED BEAD waits on TEST_UPDATE"]
    RULE -->|"THE PROMISE IS STALE<br/>review path"| S4["Mint TEST_UPDATE, agent=omg-tester<br/>REVIEW waits on TEST_UPDATE"]
    RULE -->|"TOO CLOSE TO CALL"| S5["bd gate create --type=human<br/>--blocks this bead"]

    S5 --> HG(["HUMAN GATE — the PM's one bounded<br/>exception to returning a closed bead"])
    S1 --> CL(["Close the adjudication bead"])
    S2 --> CL
    S3 --> CL
    S4 --> CL
    S2 --> SPV["The SUMMONS routes to<br/>summons-plan-verification — see below"]
```

### The PM path keeps its planner summons — deliberately

Regression-by-default — section 10, *Review, findings, and the fix loop* —
applies to review findings and **not** here. The
asymmetry is the point: **default where the judgment is predictable, dispatch where it
is not.** A review finding is a confirmed defect in code this epic changed, and the
reviewer already did the blast-radius work. A broken-promise ruling is not that — the
"fix" might be restoring prior behavior, adjusting a boundary, or reconciling two
guarantees that now conflict, and there is often no reproducible defect to pin a
regression test to.

```mermaid
flowchart TD
    A["Summons: plan verification<br/>for a PM-adjudicated fix"] --> B{"the planner's choice"}
    B -->|"automated test,<br/>designed BEFORE the fix"| C["Mint TEST, agent=omg-tester<br/>FIX waits on TEST"]
    B -->|"automated test,<br/>run AFTER the fix"| D["Mint TEST, agent=omg-tester<br/>TEST waits on FIX<br/>REVIEW waits on TEST"]
    B -->|"deterministic gate"| E["No bead. No edge.<br/>Comment the epic."]
    B -->|"review obligation"| F["No bead. No edge.<br/>Comment the epic."]
    B -->|"no verification"| G["No bead. No edge.<br/>Comment the epic."]
    C --> Z(["Close the summons — always"])
    D --> Z
    E --> Z
    F --> Z
    G --> Z
```

The before/after ordering distinction in the first two branches is load-bearing, and
the wiring differs completely between them. Note the direction flip: in the
before-case the fix waits on the test; in the after-case the test waits on the fix and
the review waits on the test.

---

## 12. What these diagrams expose

Drawing the whole thing makes two gaps visible that are hard to see while reading any
single instrument. Both are recorded here as observations, not as decisions.

**Two of the four verification outcomes are recorded and never discharged.**
Section 3, *The confidence planner's four outcomes*, traces
it: a deterministic gate and a review obligation each produce a comment on the epic
and nothing else. Nothing mints a bead for a gate, nothing checks at review that it
ran, nothing confirms it exists. The review bead runs "the full test suite," which
does not necessarily include a validator or a linter. The danger is not that they do
nothing — it is that they **claim** something. "Gate for X: `terraform validate`
catches it" reads as coverage. That is manufactured confidence, which is precisely
what the confidence planner exists to prevent.

Drawing section 4, *Canonical bead topology*, alongside section 10, *Review,
findings, and the fix loop*, sharpens it further: those decisions are recorded as comments
**on the epic**, and the report-writer bead reads "every *child* bead's comments." The
epic is not its own child. So a gate or review obligation chosen at plan time is read
once — by the decomposer's own re-review pass — and then by nothing else, ever. It
does not reach the build report either.

**Nothing bounds the review-fix cycle.** The loop in section 10, *Review,
findings, and the fix loop* — review finds a blocking finding,
mints a fix, reopens itself, runs again — has no termination condition other than a
review pass that finds nothing. The decomposer's re-review loop in section 2,
*Plan phase*, has the same shape.
Fix-round convergence is specified in the PRD and is not built.

---

## Related documents

- `docs/prd/prd.platform.verification-economy.0001.md` — the product case for the
  four-outcome vocabulary and the proportionality judgment
- `docs/spec/spec.platform.verification-economy.0001.md` — the build contract for the
  thirteen instrument changes those outcomes required
- `docs/prd/prd.platform.test-planning.0002.md` — verification ownership, phasing, the
  dispatch lifecycle contract, and crash recovery
