/**
 * Task Command
 * Phase 4: Task queue operations
 */

import * as readline from "readline";
import { GatewayClient } from "../gateway/client";

interface TaskStatus {
  task_id: string;
  status: string;
  message: string;
  queue_position?: number;
}

export async function taskCommands(
  backendUrl: string,
  accountId: string
): Promise<void> {
  const client = new GatewayClient(backendUrl);
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = (prompt: string): Promise<string> => {
    return new Promise((resolve) => {
      rl.question(prompt, resolve);
    });
  };

  const printHelp = () => {
    console.log(`
Task Commands:
  status <task_id>   - Check task status
  queue              - Show queue status
  cancel <task_id>   - Cancel your task
  help               - Show this help
  exit                - Exit
`);
  };

  printHelp();

  try {
    while (true) {
      const cmd = await question("\nTask> ");

      const parts = cmd.trim().split(/\s+/);
      const action = parts[0]?.toLowerCase();

      if (action === "exit" || action === "quit") {
        break;
      }

      if (action === "help") {
        printHelp();
        continue;
      }

      if (action === "queue") {
        try {
          const status = await client.getTaskQueueStatus();
          console.log(`
Queue Status:
  Length: ${status.queue_length}
  Processing: ${status.processing || "None"}
  Recent completed: ${status.completed_recent}
  Active signatures: ${status.signatures_active}
`);
        } catch (error) {
          console.error("Failed to get queue status:", error);
        }
        continue;
      }

      if (action === "status" && parts[1]) {
        const taskId = parts[1];
        try {
          const status = await client.getTaskStatus(taskId);
          console.log(`
Task ${taskId}:
  Status: ${status.status}
  ${status.message}
  ${status.queue_position ? `Position in queue: ${status.queue_position}` : ""}
`);
        } catch (error) {
          console.error("Failed to get task status:", error);
        }
        continue;
      }

      if (action === "cancel" && parts[1]) {
        const taskId = parts[1];
        try {
          await client.cancelTask(taskId, accountId);
          console.log(`Task ${taskId} cancelled`);
        } catch (error) {
          console.error("Failed to cancel task:", error);
        }
        continue;
      }

      console.log("Unknown command. Type 'help' for available commands.");
    }
  } finally {
    rl.close();
  }
}
