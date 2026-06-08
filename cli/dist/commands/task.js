"use strict";
/**
 * Task Command
 * Phase 4: Task queue operations
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
exports.taskCommands = taskCommands;
const readline = __importStar(require("readline"));
const client_1 = require("../gateway/client");
async function taskCommands(backendUrl, accountId) {
    const client = new client_1.GatewayClient(backendUrl);
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });
    const question = (prompt) => {
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
                }
                catch (error) {
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
                }
                catch (error) {
                    console.error("Failed to get task status:", error);
                }
                continue;
            }
            if (action === "cancel" && parts[1]) {
                const taskId = parts[1];
                try {
                    await client.cancelTask(taskId, accountId);
                    console.log(`Task ${taskId} cancelled`);
                }
                catch (error) {
                    console.error("Failed to cancel task:", error);
                }
                continue;
            }
            console.log("Unknown command. Type 'help' for available commands.");
        }
    }
    finally {
        rl.close();
    }
}
//# sourceMappingURL=task.js.map