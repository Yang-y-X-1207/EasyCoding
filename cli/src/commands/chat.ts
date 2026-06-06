/**
 * Chat Command
 * Phase 3: SSE streaming + Evaluator Agent support
 */

import * as readline from "readline";
import { GatewayClient, ChatStreamEvent } from "../gateway/client";
import { ChatRequest, Config } from "../types";

export async function chat(config: Config): Promise<void> {
  console.log("Coding-CLI Chat Mode (with AI Evaluator)");
  console.log("Type 'exit' to quit, 'history' to see messages, 'clear' to clear screen\n");

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

  // Create session
  try {
    const session = await client.createSession(config.accountId, "cli");
    sessionId = session.session_id;
    console.log(`Session: ${sessionId}\n`);
  } catch (error) {
    console.error("Failed to create session:", error);
    process.exit(1);
  }

  // Create readline interface
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

  const printStreamEvents = (event: ChatStreamEvent) => {
    switch (event.event) {
      case "start":
        process.stdout.write("\n");
        break;
      case "processing":
        process.stdout.write("🔄 thinking... ");
        break;
      case "clarification":
        console.log("\n📋 " + event.data.reply.replace(/\n/g, "\n📋 "));
        break;
      case "response":
        console.log("\n🤖 " + event.data.reply.replace(/\n/g, "\n   "));
        break;
      case "done":
        if (event.data.message_count) {
          console.log(`\n[Messages: ${event.data.message_count}]`);
        }
        break;
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

      if (message.toLowerCase() === "clear") {
        console.clear();
        continue;
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

      // Send with streaming
      console.log("");
      try {
        await client.sendChatStream(request, printStreamEvents);
        console.log("");
      } catch (error) {
        console.error("\nError:", error);
      }
    }
  } finally {
    rl.close();
  }
}
