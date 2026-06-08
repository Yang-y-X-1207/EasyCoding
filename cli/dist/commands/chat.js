"use strict";
/**
 * Chat Command
 * Phase 3: SSE streaming + Evaluator Agent support
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
exports.chat = chat;
const readline = __importStar(require("readline"));
const client_1 = require("../gateway/client");
async function chat(config) {
    console.log("Coding-CLI Chat Mode (with AI Evaluator)");
    console.log("Type 'exit' to quit, 'history' to see messages, 'clear' to clear screen\n");
    const client = new client_1.GatewayClient(config.backendUrl);
    let sessionId;
    // Check backend health
    try {
        const health = await client.healthCheck();
        console.log(`Backend: ${health.status}\n`);
    }
    catch (error) {
        console.error("Cannot connect to backend:", error);
        process.exit(1);
    }
    // Create session
    try {
        const session = await client.createSession(config.accountId, "cli");
        sessionId = session.session_id;
        console.log(`Session: ${sessionId}\n`);
    }
    catch (error) {
        console.error("Failed to create session:", error);
        process.exit(1);
    }
    // Create readline interface
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });
    const question = (prompt) => {
        return new Promise((resolve) => {
            rl.question(prompt, resolve);
        });
    };
    const printHistory = async () => {
        if (!sessionId)
            return;
        try {
            const session = await client.getSession(sessionId);
            console.log("\n--- Chat History ---");
            for (const msg of session.messages || []) {
                console.log(`[${msg.role}] ${msg.content}`);
            }
            console.log("--- End History ---\n");
        }
        catch (error) {
            console.error("Failed to get history:", error);
        }
    };
    const printStreamEvents = (event) => {
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
            const request = {
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
            }
            catch (error) {
                console.error("\nError:", error);
            }
        }
    }
    finally {
        rl.close();
    }
}
//# sourceMappingURL=chat.js.map