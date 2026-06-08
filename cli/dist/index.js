"use strict";
/**
 * Coding-CLI Entry Point
 * Phase 4: Added task command
 * Phase: Claude Code style direct CLI
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const commander_1 = require("commander");
const chat_1 = require("./commands/chat");
const task_1 = require("./commands/task");
const program = new commander_1.Command();
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
    await (0, chat_1.chat)({
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
    const { runDirectChat } = await Promise.resolve().then(() => __importStar(require("./agent/claude_agent")));
    await runDirectChat(options.project || ".", options.apiKey, options.model);
});
program
    .command("task")
    .description("Task queue operations")
    .option("-b, --backend <url>", "Backend URL", "http://localhost:8080")
    .option("-a, --account <id>", "Account ID", "default-user")
    .action(async (options) => {
    await (0, task_1.taskCommands)(options.backend, options.account);
});
// Default: show help
if (process.argv.length === 2) {
    program.help();
}
else {
    program.parse();
}
//# sourceMappingURL=index.js.map