import {
  createClient,
  waitForIdle,
  assertMessageCount,
  assertContentPresent,
  assertContentOrder,
  runVerification,
  type MessageWithParts,
} from "./helpers.js";

runVerification("verify-then-prompt", async () => {
  const client = createClient();

  const session = await client.session.create({ body: { title: "verify-then-prompt" } });
  if (!session.data) throw new Error("Failed to create session");
  const sessionId = session.data.id;

  await client.session.command({
    path: { id: sessionId },
    body: { command: "then-prompt", arguments: "" },
  });

  await waitForIdle(client, sessionId);

  const messagesResult = await client.session.messages({
    path: { id: sessionId },
  });
  if (!messagesResult.data) throw new Error("Failed to fetch messages");
  const messages = messagesResult.data as MessageWithParts[];

  const results: boolean[] = [];

  // 1. At least 4 messages (tolerance of 1)
  results.push(assertMessageCount(messages, 4, 1));

  // 2. "goodbye" appears in the message history
  results.push(assertContentPresent(messages, "goodbye"));

  // 3. "hello" appears before "goodbye"
  results.push(assertContentOrder(messages, "hello", "goodbye"));

  // 4. "Now say goodbye" appears in a user-role message (injected by plugin)
  const userMessages = messages.filter((m) => m.info.role === "user");
  const hasInjectedGoodbye = userMessages.some((m) =>
    m.parts
      .filter((p) => p.type === "text")
      .some((p) => (p as { text: string }).text.toLowerCase().includes("now say goodbye")),
  );
  if (hasInjectedGoodbye) {
    console.log('✓ PASS: "Now say goodbye" found in a user-role message (injected by plugin)');
    results.push(true);
  } else {
    console.log('✗ FAIL: "Now say goodbye" not found in any user-role message');
    results.push(false);
  }

  return results;
});
