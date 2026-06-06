/**
 * Coding-CLI Entry Point
 * Phase 1: Minimal CLI with chat command
 */

import { Command } from "commander";
import { chat } from "./commands/chat";

const program = new Command();

program
  .name("coding-cli")
  .description("AI Coding Assistant CLI")
  .version("0.1.0");

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

program.parse();
