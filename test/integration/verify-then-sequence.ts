import {
  createClient,
  waitForIdle,
  assertMessageCount,
  assertContentPresent,
  assertContentOrder,
  runVerification,
  type MessageWithParts,
} from "./helpers.js";

runVerification("verify-then-sequence", async () => {
  const client = createClient();

  const session = await client.session.create({ body: { title: "verify-then-sequence" } });
  if (!session.data) throw new Error("Failed to create session");
  const sessionId = session.data.id;

  const cmdResult = await client.session.command({
    path: { id: sessionId },
    body: { command: "then-sequence", arguments: "" },
  });
  if (cmdResult.error) throw new Error(`Command failed: ${JSON.stringify(cmdResult.error)}`);

  await waitForIdle(client, sessionId, 90_000);

  const messagesResult = await client.session.messages({
    path: { id: sessionId },
  });
  if (!messagesResult.data) throw new Error("Failed to fetch messages");
  const messages = messagesResult.data as MessageWithParts[];

  const results: boolean[] = [];

  // 1. At least 6 messages (tolerance of 2)
  results.push(assertMessageCount(messages, 6, 2));

  // 2. Octopus-related content appears
  results.push(assertContentPresent(messages, "octop"));

  // 3. "done" appears (from /echo-back done)
  results.push(assertContentPresent(messages, "done"));

  // 4. Octopus content appears before "done" (sequence order)
  results.push(assertContentOrder(messages, "octop", "done"));

  // 5. "Summarize" appears in a user-role message (injected prompt)
  const userMessages = messages.filter((m) => m.info.role === "user");
  const hasSummarize = userMessages.some((m) =>
    m.parts
      .filter((p) => p.type === "text")
      .some((p) => (p as { text: string }).text.toLowerCase().includes("summarize")),
  );
  if (hasSummarize) {
    console.log('✓ PASS: "Summarize" found in a user-role message (injected prompt)');
    results.push(true);
  } else {
    console.log('✗ FAIL: "Summarize" not found in any user-role message');
    results.push(false);
  }

  return results;
});
