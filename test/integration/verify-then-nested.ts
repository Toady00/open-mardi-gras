import {
  createClient,
  waitForIdle,
  assertMessageCount,
  assertContentPresent,
  assertContentOrder,
  runVerification,
  type MessageWithParts,
} from "./helpers.js";

runVerification("verify-then-nested", async () => {
  const client = createClient();

  const session = await client.session.create({ body: { title: "verify-then-nested" } });
  if (!session.data) throw new Error("Failed to create session");
  const sessionId = session.data.id;

  const cmdResult = await client.session.command({
    path: { id: sessionId },
    body: { command: "then-nested", arguments: "" },
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

  // 2. Outer command response is present
  results.push(assertContentPresent(messages, "outer"));

  // 3. Inner chain's goodbye response is present
  results.push(assertContentPresent(messages, "goodbye"));

  // 4. Outer response appears before goodbye (chain order)
  results.push(assertContentOrder(messages, "outer", "goodbye"));

  // 5. "Now say goodbye" appears in a user-role message (inner chain injection)
  const userMessages = messages.filter((m) => m.info.role === "user");
  const hasInjectedGoodbye = userMessages.some((m) =>
    m.parts
      .filter((p) => p.type === "text")
      .some((p) => (p as { text: string }).text.toLowerCase().includes("now say goodbye")),
  );
  if (hasInjectedGoodbye) {
    console.log('✓ PASS: "Now say goodbye" found in a user-role message (inner chain injection)');
    results.push(true);
  } else {
    console.log('✗ FAIL: "Now say goodbye" not found in any user-role message');
    results.push(false);
  }

  return results;
});
