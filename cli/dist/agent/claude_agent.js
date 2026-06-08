"use strict";
/**
 * Claude Code Style Local CLI
 * Direct AI chat with local file operations
 * Supports: OpenAI, Anthropic, Google Gemini, Azure
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
exports.loadProviderFromEnv = exports.LLMProviderClient = void 0;
exports.runDirectChat = runDirectChat;
const readline = __importStar(require("readline"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const child_process_1 = require("child_process");
const llm_provider_1 = require("./llm_provider");
Object.defineProperty(exports, "LLMProviderClient", { enumerable: true, get: function () { return llm_provider_1.LLMProviderClient; } });
Object.defineProperty(exports, "loadProviderFromEnv", { enumerable: true, get: function () { return llm_provider_1.loadProviderFromEnv; } });
// ============ Tool Handlers ============
class ToolHandler {
    constructor(projectPath) {
        this.projectPath = projectPath;
    }
    async handleCommand(input) {
        const trimmed = input.trim();
        const lower = trimmed.toLowerCase();
        // ============ Tool Commands ============
        // Read file: read <path>
        if (trimmed.startsWith("read ")) {
            const filePath = trimmed.slice(5).trim();
            return this.readFile(filePath);
        }
        // Write file: write <path> <content>
        if (trimmed.startsWith("write ")) {
            const parts = trimmed.slice(6).split(" ");
            if (parts.length >= 2) {
                const filePath = parts[0];
                const content = parts.slice(1).join(" ");
                return this.writeFile(filePath, content);
            }
            return "⚠️ 用法: write <path> <content>";
        }
        // Bash command: !<command>
        if (trimmed.startsWith("!")) {
            const cmd = trimmed.slice(1).trim();
            return this.runBash(cmd);
        }
        // List directory: ls [path]
        if (trimmed.startsWith("ls")) {
            const dirPath = trimmed.slice(2).trim() || ".";
            return this.listDir(dirPath);
        }
        // Grep search: grep <pattern> [path]
        if (trimmed.startsWith("grep ")) {
            const parts = trimmed.slice(4).trim().split(" ");
            if (parts.length >= 1) {
                const pattern = parts[0];
                const searchPath = parts[1] || ".";
                return this.grep(pattern, searchPath);
            }
        }
        // ============ Natural Language Tool Detection ============
        // Check for Chinese character at start (charCode > 127 means non-ASCII)
        const firstCharCode = trimmed.charCodeAt(0);
        const isChineseFirstChar = firstCharCode > 127;
        if (isChineseFirstChar && trimmed.length > 1) {
            // This is likely a Chinese command
            // Chinese characters commonly used for file operations:
            // 看(look/read), 查(check), 读(read), 打开(open), 创建(create), 写入(write)
            const chineseCommands = ["看", "查看", "读取", "打开", "查", "读"];
            for (const cmd of chineseCommands) {
                if (trimmed.startsWith(cmd)) {
                    // Found a Chinese read command
                    const rest = trimmed.slice(cmd.length).trim();
                    if (rest) {
                        // There seems to be a path after the command
                        // Try to parse it as a file path
                        const filePath = rest;
                        return this.readFile(filePath);
                    }
                }
            }
            // If no known command matched but first char is Chinese,
            // it might still be a file path starting with Chinese
            // e.g., "桌面/文件夹/file.txt"
            if (trimmed.includes("/") || trimmed.includes("\\")) {
                return this.readFile(trimmed);
            }
        }
        // "列目录/查看结构" - List directory
        if (lower.includes("目录") || lower.includes("结构") || lower.includes("文件夹") || lower === "ls") {
            return this.listDir(".");
        }
        // "运行/执行 + 命令" - Bash command
        if (lower.startsWith("运行 ") || lower.startsWith("执行 ")) {
            const cmd = trimmed.replace(/^(运行|执行)\s+/, "");
            return this.runBash(cmd);
        }
        return null;
    }
    readFile(filePath) {
        const fullPath = this.resolvePath(filePath);
        try {
            const content = fs.readFileSync(fullPath, "utf-8");
            const lines = content.split("\n").length;
            return `📄 ${filePath} (${lines} 行)\n\`\`\`\n${content.slice(0, 3000)}${content.length > 3000 ? "\n...(截断)" : ""}\n\`\`\``;
        }
        catch (e) {
            return `⚠️ 无法读取: ${e.message}`;
        }
    }
    writeFile(filePath, content) {
        const fullPath = this.resolvePath(filePath);
        try {
            const dir = path.dirname(fullPath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            fs.writeFileSync(fullPath, content, "utf-8");
            return `✅ 已写入: ${filePath}`;
        }
        catch (e) {
            return `⚠️ 无法写入: ${e.message}`;
        }
    }
    runBash(cmd) {
        try {
            const output = (0, child_process_1.execSync)(cmd, {
                cwd: this.projectPath,
                encoding: "utf-8",
                timeout: 30000,
            });
            return `🔧 执行: ${cmd}\n\`\`\`\n${output || "(无输出)"}\n\`\`\``;
        }
        catch (e) {
            return `⚠️ 命令失败: ${e.message}`;
        }
    }
    listDir(dirPath) {
        const fullPath = this.resolvePath(dirPath);
        try {
            const items = fs.readdirSync(fullPath);
            return `📁 ${dirPath}/\n` + items.slice(0, 50).map(item => {
                const itemPath = path.join(fullPath, item);
                const stat = fs.statSync(itemPath);
                return `   ${stat.isDirectory() ? "📂" : "📄"} ${item}`;
            }).join("\n") + (items.length > 50 ? `\n   ... 还有 ${items.length - 50} 项` : "");
        }
        catch (e) {
            return `⚠️ 无法列出: ${e.message}`;
        }
    }
    grep(pattern, searchPath) {
        try {
            const fullPath = this.resolvePath(searchPath);
            const result = (0, child_process_1.execSync)(`grep -rn "${pattern}" "${fullPath}" --include="*.ts" --include="*.js" --include="*.py" --include="*.java" 2>/dev/null | head -30`, {
                encoding: "utf-8",
                timeout: 10000,
            });
            return result || `没有找到匹配 "${pattern}" 的内容`;
        }
        catch (e) {
            return `⚠️ 搜索失败: ${e.message}`;
        }
    }
    resolvePath(filePath) {
        return path.isAbsolute(filePath) ? filePath : path.join(this.projectPath, filePath);
    }
}
// ============ Main CLI ============
async function runDirectChat(projectPath = ".", apiKey, model) {
    // Load config from env
    const envConfig = (0, llm_provider_1.loadFromEnvFile)(path.join(projectPath, ".env"));
    // Merge env variables into process.env
    for (const [key, value] of Object.entries(envConfig)) {
        if (!process.env[key]) {
            process.env[key] = value;
        }
    }
    // Try to get provider config
    let config = null;
    // Check command line args first
    if (apiKey) {
        // User provided API key, try to detect provider
        if (apiKey.startsWith("sk-")) {
            config = { provider: "anthropic", apiKey, model: model || "claude-sonnet-4-7" };
        }
        else if (apiKey.startsWith("sk-")) {
            config = { provider: "openai", apiKey, model: model || "gpt-4o" };
        }
        else {
            config = { provider: "anthropic", apiKey, model: model || "claude-sonnet-4-7" };
        }
    }
    else {
        config = (0, llm_provider_1.loadProviderFromEnv)();
    }
    if (!config) {
        console.log("❌ 未找到 LLM API 配置");
        console.log("");
        console.log("请设置以下任一环境变量:");
        console.log("  OpenAI:     export OPENAI_API_KEY=sk-xxxxx");
        console.log("  Anthropic:  export ANTHROPIC_API_KEY=sk-ant-xxxxx");
        console.log("  Google:      export GEMINI_API_KEY=xxxxx");
        console.log("  Azure:       export AZURE_OPENAI_KEY=xxxxx");
        console.log("  MiniMax:     export MINIMAX_API_KEY=sk-cp-xxxxx");
        console.log("");
        console.log("或创建 .env 文件:");
        console.log("  OPENAI_API_KEY=sk-xxxxx");
        console.log("  ANTHROPIC_API_KEY=sk-ant-xxxxx");
        console.log("  MINIMAX_API_KEY=sk-cp-xxxxx");
        process.exit(1);
    }
    const client = new llm_provider_1.LLMProviderClient(config);
    const tools = new ToolHandler(projectPath);
    const messages = [];
    const providerNames = {
        openai: "OpenAI GPT",
        anthropic: "Anthropic Claude",
        gemini: "Google Gemini",
        azure: "Azure OpenAI",
    };
    const systemPrompt = `你是 Coding-CLI，一个专业的 AI 编程助手。

你可以：
- 读取文件: read <path>
- 写入文件: write <path> <content>
- 执行命令: !<command>
- 列目录: ls [path]
- 搜索代码: grep <pattern> [path]

请用中文回答。帮助用户完成代码编写、修改、分析等任务。
当前项目: ${path.resolve(projectPath)}`;
    console.log("🤖 Coding-CLI Agent");
    console.log(`📁 项目: ${path.resolve(projectPath)}`);
    console.log(`🔧 Provider: ${providerNames[config.provider] || config.provider}`);
    console.log(`📝 Model: ${config.model}`);
    console.log("");
    console.log("命令: exit=退出 | clear=清屏 | history=历史 | help=帮助");
    console.log("工具: read <file> | write <file> | !<cmd> | ls [dir] | grep <pattern>");
    console.log("---\n");
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });
    const question = (prompt) => {
        return new Promise((resolve) => {
            rl.question(prompt, resolve);
        });
    };
    // Introduction
    try {
        const intro = await client.chat([{ role: "user", content: "用简短的话介绍你自己" }], systemPrompt);
        console.log(`🤖 ${intro.content}\n`);
    }
    catch (e) {
        console.log(`❌ 连接失败: ${e.message}`);
        process.exit(1);
    }
    try {
        while (true) {
            let input;
            try {
                input = await question("You: ");
            }
            catch (e) {
                if (e.code === 'ERR_USE_AFTER_CLOSE') {
                    console.log("\n\n❌ 输入流已关闭，程序退出");
                    break;
                }
                throw e;
            }
            if (!input.trim())
                continue;
            const lower = input.toLowerCase();
            // Special commands
            if (lower === "exit") {
                console.log("\n👋 再见!");
                break;
            }
            if (lower === "clear") {
                console.clear();
                continue;
            }
            if (lower === "history") {
                console.log("\n--- 对话历史 ---");
                messages.forEach((m, i) => {
                    console.log(`[${i + 1}] ${m.role}: ${m.content.slice(0, 80)}...`);
                });
                console.log("---\n");
                continue;
            }
            if (lower === "help") {
                console.log(`
📋 可用命令:
   exit        - 退出
   clear       - 清屏
   history     - 显示历史
   read <f>    - 读取文件
   write <f>   - 写入文件
   !<cmd>      - 执行命令
   ls [dir]    - 列目录
   grep <pat>  - 搜索代码
`);
                continue;
            }
            // Check for tool commands first
            const toolResult = await tools.handleCommand(input);
            if (toolResult) {
                console.log(`\n${toolResult}\n`);
                messages.push({ role: "user", content: input });
                messages.push({ role: "assistant", content: toolResult });
                continue;
            }
            // Send to LLM
            console.log("\n🤖 AI 思考中...\n");
            try {
                messages.push({ role: "user", content: input });
                const response = await client.chat(messages, systemPrompt);
                console.log(`🤖 ${response.content}\n`);
                messages.push({ role: "assistant", content: response.content });
            }
            catch (e) {
                console.log(`❌ 错误: ${e.message}\n`);
            }
        }
    }
    finally {
        rl.close();
    }
}
//# sourceMappingURL=claude_agent.js.map