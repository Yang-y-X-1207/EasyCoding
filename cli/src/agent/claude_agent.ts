/**
 * Claude Code Style Local CLI
 * Direct AI chat with local file operations
 * Supports: OpenAI, Anthropic, Google Gemini, Azure
 */

import * as readline from "readline";
import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import { LLMProviderClient, loadProviderFromEnv, loadFromEnvFile, ProviderConfig } from "./llm_provider";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// ============ Tool Handlers ============

class ToolHandler {
  constructor(private projectPath: string) {}

  async handleCommand(input: string): Promise<string | null> {
    const trimmed = input.trim();

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

    return null;
  }

  private readFile(filePath: string): string {
    const fullPath = this.resolvePath(filePath);
    try {
      const content = fs.readFileSync(fullPath, "utf-8");
      const lines = content.split("\n").length;
      return `📄 ${filePath} (${lines} 行)\n\`\`\`\n${content.slice(0, 3000)}${content.length > 3000 ? "\n...(截断)" : ""}\n\`\`\``;
    } catch (e: any) {
      return `⚠️ 无法读取: ${e.message}`;
    }
  }

  private writeFile(filePath: string, content: string): string {
    const fullPath = this.resolvePath(filePath);
    try {
      const dir = path.dirname(fullPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(fullPath, content, "utf-8");
      return `✅ 已写入: ${filePath}`;
    } catch (e: any) {
      return `⚠️ 无法写入: ${e.message}`;
    }
  }

  private runBash(cmd: string): string {
    try {
      const output = execSync(cmd, {
        cwd: this.projectPath,
        encoding: "utf-8",
        timeout: 30000,
      });
      return `🔧 执行: ${cmd}\n\`\`\`\n${output || "(无输出)"}\n\`\`\``;
    } catch (e: any) {
      return `⚠️ 命令失败: ${e.message}`;
    }
  }

  private listDir(dirPath: string): string {
    const fullPath = this.resolvePath(dirPath);
    try {
      const items = fs.readdirSync(fullPath);
      return `📁 ${dirPath}/\n` + items.slice(0, 50).map(item => {
        const itemPath = path.join(fullPath, item);
        const stat = fs.statSync(itemPath);
        return `   ${stat.isDirectory() ? "📂" : "📄"} ${item}`;
      }).join("\n") + (items.length > 50 ? `\n   ... 还有 ${items.length - 50} 项` : "");
    } catch (e: any) {
      return `⚠️ 无法列出: ${e.message}`;
    }
  }

  private grep(pattern: string, searchPath: string): string {
    try {
      const fullPath = this.resolvePath(searchPath);
      const result = execSync(`grep -rn "${pattern}" "${fullPath}" --include="*.ts" --include="*.js" --include="*.py" --include="*.java" 2>/dev/null | head -30`, {
        encoding: "utf-8",
        timeout: 10000,
      });
      return result || `没有找到匹配 "${pattern}" 的内容`;
    } catch (e: any) {
      return `⚠️ 搜索失败: ${e.message}`;
    }
  }

  private resolvePath(filePath: string): string {
    return path.isAbsolute(filePath) ? filePath : path.join(this.projectPath, filePath);
  }
}

// ============ Main CLI ============

export async function runDirectChat(
  projectPath: string = ".",
  apiKey?: string,
  model?: string
): Promise<void> {
  // Load config from env
  const envConfig = loadFromEnvFile(path.join(projectPath, ".env"));

  // Merge env variables into process.env
  for (const [key, value] of Object.entries(envConfig)) {
    if (!process.env[key]) {
      process.env[key] = value;
    }
  }

  // Try to get provider config
  let config: ProviderConfig | null = null;

  // Check command line args first
  if (apiKey) {
    // User provided API key, try to detect provider
    if (apiKey.startsWith("sk-")) {
      config = { provider: "anthropic", apiKey, model: model || "claude-sonnet-4-7" };
    } else if (apiKey.startsWith("sk-")) {
      config = { provider: "openai", apiKey, model: model || "gpt-4o" };
    } else {
      config = { provider: "anthropic", apiKey, model: model || "claude-sonnet-4-7" };
    }
  } else {
    config = loadProviderFromEnv();
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

  const client = new LLMProviderClient(config);
  const tools = new ToolHandler(projectPath);
  const messages: Message[] = [];

  const providerNames: Record<string, string> = {
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

  const question = (prompt: string): Promise<string> => {
    return new Promise((resolve) => {
      rl.question(prompt, resolve);
    });
  };

  // Introduction
  try {
    const intro = await client.chat(
      [{ role: "user", content: "用简短的话介绍你自己" }],
      systemPrompt
    );
    console.log(`🤖 ${intro.content}\n`);
  } catch (e: any) {
    console.log(`❌ 连接失败: ${e.message}`);
    process.exit(1);
  }

  try {
    while (true) {
      const input = await question("You: ");

      if (!input.trim()) continue;

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
      } catch (e: any) {
        console.log(`❌ 错误: ${e.message}\n`);
      }
    }
  } finally {
    rl.close();
  }
}

// Export for use in index.ts
export { LLMProviderClient, loadProviderFromEnv };