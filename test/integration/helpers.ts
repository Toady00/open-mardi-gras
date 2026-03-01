import {
  createOpencodeClient,
  type OpencodeClient,
  type Message,
  type Part,
  type TextPart,
} from "@opencode-ai/sdk";

export type { OpencodeClient };

export type MessageWithParts = {
  info: Message;
  parts: Part[];
};

export function createClient(port = 4200): OpencodeClient {
  return createOpencodeClient({ baseUrl: `http://localhost:${port}` });
}

export async function waitForIdle(
  client: OpencodeClient,
  sessionId: string,
  timeoutMs = 60_000,
): Promise<void> {
  const { stream } = await client.event.subscribe();

  const timeoutPromise = new Promise<never>((_, reject) => {
    setTimeout(
      () => reject(new Error(`Timed out waiting for session ${sessionId} to go idle`)),
      timeoutMs,
    );
  });

  const eventLoop = async (): Promise<void> => {
    try {
      for await (const event of stream) {
        if (
          event.type === "session.idle" &&
          event.properties.sessionID === sessionId
        ) {
          return;
        }
      }
    } finally {
      await stream.return(undefined as void);
    }
  };

  await Promise.race([eventLoop(), timeoutPromise]);
}

function getTextContent(msg: MessageWithParts): string {
  return msg.parts
    .filter((p): p is TextPart => p.type === "text")
    .map((p) => p.text)
    .join("");
}

export function assertMessageCount(
  messages: MessageWithParts[],
  expected: number,
  tolerance = 0,
): boolean {
  const count = messages.length;
  const low = expected - tolerance;
  const high = expected + tolerance;
  if (count >= low && count <= high) {
    console.log(
      `✓ PASS: message count ${count} is within ${expected} ± ${tolerance}`,
    );
    return true;
  }
  console.log(
    `✗ FAIL: message count ${count} is outside ${expected} ± ${tolerance}`,
  );
  return false;
}

export function assertContentPresent(
  messages: MessageWithParts[],
  substring: string,
): boolean {
  const lower = substring.toLowerCase();
  const found = messages.some((m) =>
    getTextContent(m).toLowerCase().includes(lower),
  );
  if (found) {
    console.log(`✓ PASS: content contains "${substring}"`);
    return true;
  }
  console.log(`✗ FAIL: content does not contain "${substring}"`);
  return false;
}

export function assertContentAbsent(
  messages: MessageWithParts[],
  substring: string,
): boolean {
  const lower = substring.toLowerCase();
  const found = messages.some((m) =>
    getTextContent(m).toLowerCase().includes(lower),
  );
  if (!found) {
    console.log(`✓ PASS: content does not contain "${substring}"`);
    return true;
  }
  console.log(`✗ FAIL: content unexpectedly contains "${substring}"`);
  return false;
}

export function assertContentOrder(
  messages: MessageWithParts[],
  substringA: string,
  substringB: string,
): boolean {
  const lowerA = substringA.toLowerCase();
  const lowerB = substringB.toLowerCase();
  const indexA = messages.findIndex((m) =>
    getTextContent(m).toLowerCase().includes(lowerA),
  );
  const indexB = messages.findIndex((m) =>
    getTextContent(m).toLowerCase().includes(lowerB),
  );

  if (indexA === -1) {
    console.log(
      `✗ FAIL: "${substringA}" not found in any message — cannot verify order`,
    );
    return false;
  }
  if (indexB === -1) {
    console.log(
      `✗ FAIL: "${substringB}" not found in any message — cannot verify order`,
    );
    return false;
  }
  if (indexA < indexB) {
    console.log(
      `✓ PASS: "${substringA}" (msg ${indexA}) appears before "${substringB}" (msg ${indexB})`,
    );
    return true;
  }
  console.log(
    `✗ FAIL: "${substringA}" (msg ${indexA}) does not appear before "${substringB}" (msg ${indexB})`,
  );
  return false;
}

export function assertRoleSequence(
  messages: MessageWithParts[],
  expectedRoles: string[],
): boolean {
  const actualRoles = messages.map((m) => m.info.role);
  const match =
    actualRoles.length === expectedRoles.length &&
    actualRoles.every((r, i) => r === expectedRoles[i]);
  if (match) {
    console.log(
      `✓ PASS: role sequence matches [${expectedRoles.join(", ")}]`,
    );
    return true;
  }
  console.log(
    `✗ FAIL: role sequence [${actualRoles.join(", ")}] does not match expected [${expectedRoles.join(", ")}]`,
  );
  return false;
}

export async function runVerification(
  name: string,
  fn: () => Promise<boolean[]>,
): Promise<void> {
  console.log(`\n=== ${name} ===\n`);
  try {
    const results = await fn();
    const passed = results.filter(Boolean).length;
    const total = results.length;
    console.log(`\n--- ${passed}/${total} checks passed ---`);
    process.exit(passed === total ? 0 : 1);
  } catch (err) {
    console.error(`\n✗ FATAL: ${err}`);
    process.exit(1);
  }
}
