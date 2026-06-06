/**
 * Coding-CLI Entry Point
 * Phase 4: Added task command
 */

import { Command } from "commander";
import { chat } from "./commands/chat";
import { taskCommands } from "./commands/task";

const program = new Command();

program
  .name("coding-cli")
  .description("AI Coding Assistant CLI")
  .version("0.4.0");

program
  .command("chat")
  .description("Start interactive chat with the coding assistant")
  .option("-b, --backend <url>", "Backend URL", "http://localhost:8080")
  .option("-a, --account <id>", "Account ID", "default-user")
  .action(async (options) => {
    await chat({
      backendUrl: options.backend,
      accountId: options.account,
    });
  });

program
  .command("task")
  .description("Task queue operations")
  .option("-b, --backend <url>", "Backend URL", "http://localhost:8080")
  .option("-a, --account <id>", "Account ID", "default-user")
  .action(async (options) => {
    await taskCommands(options.backend, options.account);
  });

// Default: run chat
if (process.argv.length === 2) {
  chat({ backendUrl: "http://localhost:8080", accountId: "default-user" });
} else {
  program.parse();
}
