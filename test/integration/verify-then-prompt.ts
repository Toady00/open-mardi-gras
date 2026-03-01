import {
  createClient,
  waitForIdle,
  assertMessageCount,
  assertContentPresent,
  assertContentPresentInRole,
  assertContentOrder,
  runVerification,
  type MessageWithParts,
} from "./helpers.js";

runVerification("verify-then-prompt", async () => {
  const client = createClient();

  const session = await client.session.create({ body: { title: "verify-then-prompt" } });
  if (!session.data) throw new Error("Failed to create session");
  const sessionId = session.data.id;

  const cmdResult = await client.session.command({
    path: { id: sessionId },
    body: { command: "then-prompt", arguments: "" },
  });
  if (cmdResult.error) throw new Error(`Command failed: ${JSON.stringify(cmdResult.error)}`);

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
  results.push(assertContentPresentInRole(messages, "Now say goodbye", "user"));

  return results;
});
