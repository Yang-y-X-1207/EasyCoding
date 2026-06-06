/**
 * Coding-CLI Entry Point
 * Phase 4: Added task command
 * Phase: Claude Code style direct CLI
 */

import { Command } from "commander";
import { chat } from "./commands/chat";
import { taskCommands } from "./commands/task";

const program = new Command();

program
  .name("coding-cli")
  .description("AI Coding Assistant CLI")
  .version("0.8.0");

program
  .command("chat")
  .description("Start interactive chat with the coding assistant (via backend)")
  .option("-b, --backend <url>", "Backend URL", "http://localhost:8080")
  .option("-a, --account <id>", "Account ID", "default-user")
  .action(async (options) => {
    await chat({
      backendUrl: options.backend,
      accountId: options.account,
    });
  });

program
  .command("direct")
  .description("Direct chat with Claude API (no backend needed)")
  .option("-k, --api-key <key>", "Anthropic API Key")
  .option("-p, --project <path>", "Project path", ".")
  .option("-m, --model <model>", "Model", "claude-sonnet-4-7")
  .action(async (options) => {
    const { runDirectChat } = await import("./agent/claude_agent");
    await runDirectChat(options.project || ".", options.apiKey, options.model);
  });

program
  .command("task")
  .description("Task queue operations")
  .option("-b, --backend <url>", "Backend URL", "http://localhost:8080")
  .option("-a, --account <id>", "Account ID", "default-user")
  .action(async (options) => {
    await taskCommands(options.backend, options.account);
  });

// Default: show help
if (process.argv.length === 2) {
  program.help();
} else {
  program.parse();
}
