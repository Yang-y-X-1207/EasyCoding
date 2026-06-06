/**
 * Claude Code Style Local CLI
 * Direct AI chat with local file operations
 */

import * as readline from "readline";
import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// ============ Claude API Client ============

class ClaudeClient {
  private apiKey: string;
  private model: string;

  constructor(apiKey: string, model = "claude-sonnet-4-7") {
    this.apiKey = apiKey;
    this.model = model;
  }

  async send(messages: Message[], systemPrompt: string): Promise<string> {
    const url = "https://api.anthropic.com/v1/messages";

    const headers = {
      "x-api-key": this.apiKey,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    };

    const payload = {
      model: this.model,
      max_tokens: 4096,
      system: systemPrompt,
      messages: messages.map(m => ({
        role: m.role,
        content: m.content,
      })),
    };

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json() as { error?: { message?: string } };
      throw new Error(err.error?.message || `API Error: ${response.status}`);
    }

    const data = await response.json() as { content?: Array<{ text: string }> };
    return data.content?.[0]?.text || "⚠️ 无响应";
  }
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

    return null; // Not a tool command
  }

  private readFile(filePath: string): string {
    const fullPath = this.resolvePath(filePath);
    try {
      const content = fs.readFileSync(fullPath, "utf-8");
      const lines = content.split("\n").length;
      return `📄 ${filePath} (${lines} 行)\n\`\`\`\n${content.slice(0, 2000)}${content.length > 2000 ? "\n...(截断)" : ""}\n\`\`\``;
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

  private resolvePath(filePath: string): string {
    return path.isAbsolute(filePath) ? filePath : path.join(this.projectPath, filePath);
  }
}

// ============ Main CLI ============

export async function runDirectChat(
  projectPath: string = ".",
  apiKey?: string,
  model: string = "claude-sonnet-4-7"
): Promise<void> {
  // Get API key
  let key = apiKey || process.env.ANTHROPIC_API_KEY || "";

  // Try to load from .env
  if (!key) {
    const envPath = path.join(projectPath, ".env");
    if (fs.existsSync(envPath)) {
      const envContent = fs.readFileSync(envPath, "utf-8");
      const match = envContent.match(/ANTHROPIC_API_KEY\s*=\s*(.+)/);
      if (match) key = match[1].trim();
    }
  }

  if (!key) {
    console.log("❌ 请设置 ANTHROPIC_API_KEY");
    console.log("   export ANTHROPIC_API_KEY=sk-ant-xxxxx");
    console.log("   或在 .env 文件中设置 ANTHROPIC_API_KEY=sk-ant-xxxxx");
    process.exit(1);
  }

  const client = new ClaudeClient(key, model);
  const tools = new ToolHandler(projectPath);
  const messages: Message[] = [];

  const systemPrompt = `你是 Coding-CLI，一个专业的 AI 编程助手。

你可以：
- 读取文件: read <path>
- 写入文件: write <path> <content>
- 执行命令: !<command>
- 列目录: ls [path]

请用中文回答。帮助用户完成代码编写、修改、分析等任务。
当前项目: ${path.resolve(projectPath)}`;

  console.log("🤖 Coding-CLI Agent (Claude Code Style)");
  console.log(`📁 项目: ${path.resolve(projectPath)}`);
  console.log("🔑 API: 已配置");
  console.log("");
  console.log("命令: exit=退出 | clear=清屏 | history=历史");
  console.log("工具: read <file> | write <file> <content> | !<cmd> | ls [dir]");
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
    const intro = await client.send(
      [{ role: "user", content: "用简短的话介绍你自己" }],
      systemPrompt
    );
    console.log(`🤖 ${intro}\n`);
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
   exit      - 退出
   clear     - 清屏
   history   - 显示历史
   read <f>  - 读取文件
   write <f> - 写入文件
   !<cmd>    - 执行命令
   ls [dir]  - 列目录
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

      // Send to Claude
      console.log("\n🤖 AI 思考中...\n");
      try {
        messages.push({ role: "user", content: input });
        const response = await client.send(messages, systemPrompt);
        console.log(`🤖 ${response}\n`);
        messages.push({ role: "assistant", content: response });
      } catch (e: any) {
        console.log(`❌ 错误: ${e.message}\n`);
      }
    }
  } finally {
    rl.close();
  }
}

// Export for use in index.ts
export { ClaudeClient, ToolHandler };