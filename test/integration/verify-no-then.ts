import {
  createClient,
  waitForIdle,
  assertMessageCount,
  assertContentPresent,
  assertRoleSequence,
  runVerification,
  type MessageWithParts,
} from "./helpers.js";

runVerification("verify-no-then", async () => {
  const client = createClient();

  const session = await client.session.create({ body: { title: "verify-no-then" } });
  if (!session.data) throw new Error("Failed to create session");
  const sessionId = session.data.id;

  const cmdResult = await client.session.command({
    path: { id: sessionId },
    body: { command: "echo-back", arguments: "hello" },
  });
  if (cmdResult.error) throw new Error(`Command failed: ${JSON.stringify(cmdResult.error)}`);

  await waitForIdle(client, sessionId);

  const messagesResult = await client.session.messages({
    path: { id: sessionId },
  });
  if (!messagesResult.data) throw new Error("Failed to fetch messages");
  const messages = messagesResult.data as MessageWithParts[];

  const results: boolean[] = [];

  // 1. Exactly 2 messages (user command + assistant response)
  results.push(assertMessageCount(messages, 2));

  // 2. "hello" appears in the assistant response (not just the user command)
  const assistantMessages = messages.filter((m) => m.info.role === "assistant");
  results.push(assertContentPresent(assistantMessages, "hello"));

  // 3. Correct role alternation
  results.push(assertRoleSequence(messages, ["user", "assistant"]));

  return results;
});
