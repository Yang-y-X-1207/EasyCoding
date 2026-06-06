/**
 * Chat Command
 * Phase 2: Session-aware interactive chat with conversation history
 */

import * as readline from "readline";
import { GatewayClient } from "../gateway/client";
import { ChatRequest, Config } from "../types";

export async function chat(config: Config): Promise<void> {
  console.log("Coding-CLI Chat Mode (with Memory)");
  console.log("Type 'exit' to quit, 'history' to see messages\n");

  const client = new GatewayClient(config.backendUrl);
  let sessionId: string | undefined;

  // Check backend health
  try {
    const health = await client.healthCheck();
    console.log(`Backend: ${health.status}`);
  } catch (error) {
    console.error("Cannot connect to backend:", error);
    process.exit(1);
  }

  // Create or resume session
  try {
    // Try to create a new session
    const session = await client.createSession(config.accountId, "cli");
    sessionId = session.session_id;
    console.log(`Session created: ${sessionId}\n`);
  } catch (error) {
    console.error("Failed to create session:", error);
    process.exit(1);
  }

  // Create readline interface for interactive input
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = (prompt: string): Promise<string> => {
    return new Promise((resolve) => {
      rl.question(prompt, resolve);
    });
  };

  const printHistory = async () => {
    if (!sessionId) return;

    try {
      const session = await client.getSession(sessionId);
      console.log("\n--- Chat History ---");
      for (const msg of session.messages || []) {
        console.log(`[${msg.role}] ${msg.content}`);
      }
      console.log("--- End History ---\n");
    } catch (error) {
      console.error("Failed to get history:", error);
    }
  };

  try {
    while (true) {
      const message = await question("You: ");

      if (message.toLowerCase() === "exit") {
        console.log("Goodbye!");
        break;
      }

      if (message.toLowerCase() === "history") {
        await printHistory();
        continue;
      }

      if (!message.trim()) {
        continue;
      }

      // Build request with session
      const request: ChatRequest = {
        action: "chat",
        channel: "cli",
        account_id: config.accountId,
        session_id: sessionId,
        params: { message },
        metadata: { client: "coding-cli" },
      };

      // Send to backend
      try {
        const response = await client.sendChat(request);
        console.log(`\nAssistant: ${response.data.reply}\n`);
        console.log(`[Messages in session: ${response.data.message_count}]\n`);
      } catch (error) {
        console.error("Error:", error);
      }
    }
  } finally {
    rl.close();
  }
}
