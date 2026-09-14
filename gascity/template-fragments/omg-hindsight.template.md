{{define "omg-hindsight" -}}
## Build context with Hindsight

You have read access to the shared Hindsight memory bank through
`gc hindsight read`. The configured bank is `$HINDSIGHT_BANK`. Use it actively
while building context for conversations, requirements, designs and reviews.
This guidance applies to both city and rig sessions throughout the conversation.

### Discover relevant mental models first

When building context for a new conversation or resuming one without its context,
list the available mental models:

```sh
gc hindsight read mental-model list "$HINDSIGHT_BANK"
```

Inspect the catalog and select the models you judge relevant to the topic,
affected repositories, constraints or decisions. Fetch the content of each
selected model; listing its name is not enough. Use the returned IDs rather than
assuming a fixed set of models exists:

```sh
TMP=$(mktemp -d)
gc hindsight read -o json mental-model get "$HINDSIGHT_BANK" "<selected-model-id>" > "$TMP/model.json"
jq -r '.content' "$TMP/model.json"
```

If the topic is still unclear, keep the catalog available and fetch relevant
models as the scope becomes apparent. As the conversation expands, fetch other
models that become relevant. Refresh the catalog when resuming after a gap or
when the available context may have changed.

### Reflect as the conversation develops

As soon as you know what background information would help, make a reflect call
about that topic. Do not wait for a finished task statement or a request to write
a document:

```sh
gc hindsight read memory reflect "$HINDSIGHT_BANK" "<specific background question>" --budget mid
```

Reflect again whenever new information, constraints, alternatives or questions
make additional background useful. You do not need a new task or permission to
reflect again. Let the evolving conversation drive the queries; reuse useful
answers rather than repeating the same query mechanically.

Scope queries to the affected repositories and domains when useful. For example,
`--tags repo:<rig>,scope:platform --tags-match any_strict` includes that rig and
platform context. Include other affected repos or business context as appropriate
for cross-rig conversations. `any_strict` matches any selected tag; adding an
accepted-status tag to that list would broaden the query, not restrict it.
Use `memory recall` for targeted factual lookups when synthesis is unnecessary.
This conversation-driven cadence governs PM and architect reads, including when
consulting Hindsight reference skills that describe a once-per-task cadence.

Use the retrieved context in your reasoning, identifying relevant decisions,
constraints and unresolved questions. Hindsight is derived memory; consult current
Git documents and code for exact facts. Drafts are proposals, accepted documents
record direction, and build reports describe implementation at a stated revision.
If the bank is unconfigured or a read fails, surface the gap and use available
documents and code without claiming that memory was checked successfully.
The archivist owns bank writes; these commands are read-only.
{{- end}}
