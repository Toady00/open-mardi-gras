import {
  createClient,
  waitForIdle,
  assertMessageCount,
  assertContentPresent,
  assertContentOrder,
  runVerification,
  type MessageWithParts,
} from "./helpers.js";

runVerification("verify-then-command", async () => {
  const client = createClient();

  const session = await client.session.create({ body: { title: "verify-then-command" } });
  if (!session.data) throw new Error("Failed to create session");
  const sessionId = session.data.id;

  await client.session.command({
    path: { id: sessionId },
    body: { command: "then-command", arguments: "" },
  });

  await waitForIdle(client, sessionId);

  const messagesResult = await client.session.messages({
    path: { id: sessionId },
  });
  if (!messagesResult.data) throw new Error("Failed to fetch messages");
  const messages = messagesResult.data as MessageWithParts[];

  const results: boolean[] = [];

  // 1. At least 4 messages (tolerance of 2)
  results.push(assertMessageCount(messages, 4, 2));

  // 2. "farewell" appears (from /echo-back farewell)
  results.push(assertContentPresent(messages, "farewell"));

  // 3. "hello" appears before "farewell" (chain order)
  results.push(assertContentOrder(messages, "hello", "farewell"));

  return results;
});
