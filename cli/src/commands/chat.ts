/**
 * Chat Command
 * Phase 1: Interactive chat with Backend
 */

import * as readline from "readline";
import { GatewayClient } from "../gateway/client";
import { ChatRequest, Config } from "../types";

export async function chat(config: Config): Promise<void> {
  console.log("Coding-CLI Chat Mode");
  console.log("Type 'exit' to quit\n");

  const client = new GatewayClient(config.backendUrl);
  let sessionId: string | undefined;

  // Check backend health
  try {
    const health = await client.healthCheck();
    console.log(`Backend: ${health.status}\n`);
  } catch (error) {
    console.error("Cannot connect to backend:", error);
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

  try {
    while (true) {
      const message = await question("You: ");

      if (message.toLowerCase() === "exit") {
        console.log("Goodbye!");
        break;
      }

      if (!message.trim()) {
        continue;
      }

      // Build request
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
        sessionId = response.data.session_id;
      } catch (error) {
        console.error("Error:", error);
      }
    }
  } finally {
    rl.close();
  }
}
