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
import { PromptOptimizer } from "./prompt_optimizer";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// ============ Tool Handlers ============

class ToolHandler {
  constructor(private projectPath: string) {}

  async handleCommand(input: string): Promise<string | null> {
    const trimmed = input.trim();
    const lower = trimmed.toLowerCase();

    // ============ Tool Commands ============

    // Read file: read <path>
    if (trimmed.startsWith("read ")) {
      const filePath = trimmed.slice(5).trim();
      return this.smartRead(filePath);
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

      // Patterns like "读一下 <path>", "帮我看看 <path>", "麻烦看一下 <path>"
      // We need to strip filler words before parsing the path
      const chineseReadPatterns = [
        // Full patterns with filler words
        { pattern: /^读一下\s+/, cmd: "读" },
        { pattern: /^看一下\s+/, cmd: "看" },
        { pattern: /^看看\s+/, cmd: "看" },
        { pattern: /^帮我看\s+/, cmd: "看" },
        { pattern: /^帮我读\s+/, cmd: "读" },
        { pattern: /^帮我查看\s+/, cmd: "查看" },
        { pattern: /^麻烦看一下\s+/, cmd: "看" },
        { pattern: /^麻烦读一下\s+/, cmd: "读" },
        { pattern: /^请看一下\s+/, cmd: "看" },
        { pattern: /^请读一下\s+/, cmd: "读" },
        { pattern: /^打开\s+/, cmd: "打开" },
        { pattern: /^浏览\s+/, cmd: "浏览" },
        { pattern: /^导航到\s+/, cmd: "导航到" },
      ];

      for (const item of chineseReadPatterns) {
        if (item.pattern.test(trimmed)) {
          const rest = trimmed.replace(item.pattern, "").trim();
          if (rest) {
            return this.smartRead(rest);
          }
        }
      }

      // Simple commands: "看 <path>", "读 <path>", "查看 <path>", etc.
      const simpleCommands = ["看", "查看", "读取", "打开", "查", "读", "浏览", "导航到"];
      for (const cmd of simpleCommands) {
        if (trimmed.startsWith(cmd)) {
          const rest = trimmed.slice(cmd.length).trim();
          // Only treat as path if it doesn't start with common filler words
          if (rest && !rest.startsWith("一下") && !rest.startsWith("一下")) {
            return this.smartRead(rest);
          }
        }
      }

      // If no known command matched but first char is Chinese,
      // it might still be a file path starting with Chinese
      // e.g., "桌面/文件夹/file.txt"
      if (trimmed.includes("/") || trimmed.includes("\\")) {
        return this.smartRead(trimmed);
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

    // ============ Smart Path Detection ============
    // If input looks like a path, try to read it
    if (this.looksLikePath(trimmed)) {
      const result = this.smartRead(trimmed);
      // Only return if path exists, otherwise let LLM handle it
      if (!result.startsWith("⚠️ 路径不存在")) {
        return result;
      }
    }

    return null;
  }

  /**
   * Check if input looks like a file or directory path
   */
  private looksLikePath(input: string): boolean {
    // Skip if it's clearly a command
    if (input.startsWith("!") || input.startsWith("read ") || input.startsWith("write ") ||
        input.startsWith("grep ") || input.startsWith("ls")) {
      return false;
    }

    // Skip if it's very short (likely a single word command)
    if (input.length < 2) {
      return false;
    }

    // Check for common path indicators
    // 1. Has file extension (e.g., src/index.ts, package.json)
    if (this.hasFileExtension(input)) {
      return true;
    }

    // 2. Ends with path separator (directory)
    if (input.endsWith("/") || input.endsWith("\\")) {
      return true;
    }

    // 3. Contains path separators and looks like a file/dir reference
    if ((input.includes("/") || input.includes("\\")) && !input.includes(" ")) {
      return true;
    }

    // 4. Looks like a relative project path (e.g., src, src/utils, package.json)
    const commonPrefixes = ["src", "lib", "app", "dist", "build", "test", "tests", "docs", "config", "scripts", "tools", "backend", "cli", "memory", "workspace"];
    for (const prefix of commonPrefixes) {
      if (input === prefix || input.startsWith(prefix + "/") || input.startsWith(prefix + "\\")) {
        return true;
      }
    }

    return false;
  }

  /**
   * Check if string has a common file extension
   */
  private hasFileExtension(input: string): boolean {
    const extensions = [
      ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".txt", ".yaml", ".yml",
      ".py", ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs", ".rb", ".php",
      ".html", ".css", ".scss", ".less", ".xml", ".sql", ".sh", ".bash", ".bat",
      ".env", ".gitignore", ".dockerfile", "package.json", "tsconfig.json",
      "pom.xml", "build.gradle", "requirements.txt", "Cargo.toml", "Makefile"
    ];

    const lower = input.toLowerCase();
    for (const ext of extensions) {
      if (lower.endsWith(ext)) {
        return true;
      }
    }
    return false;
  }

  /**
   * Smart read: automatically detect if path is file or directory
   */
  private smartRead(inputPath: string): string {
    const fullPath = this.resolvePath(inputPath);

    // Check if path exists
    if (!fs.existsSync(fullPath)) {
      // Try without trailing slashes for directories
      const normalized = inputPath.replace(/[\/\\]+$/, "");
      if (normalized !== inputPath) {
        return this.smartRead(normalized);
      }
      return `⚠️ 路径不存在: ${inputPath}\n   相对于项目: ${this.projectPath}`;
    }

    // Check if it's a directory
    try {
      const stat = fs.statSync(fullPath);
      if (stat.isDirectory()) {
        return this.listDir(inputPath);
      }
      return this.readFile(inputPath);
    } catch (e: any) {
      return `⚠️ 无法读取: ${e.message}`;
    }
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
  const optimizer = new PromptOptimizer(config);
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
      let input: string;
      try {
        input = await question("You: ");
      } catch (e: any) {
        if (e.code === 'ERR_USE_AFTER_CLOSE') {
          console.log("\n\n❌ 输入流已关闭，程序退出");
          break;
        }
        throw e;
      }

      if (!input.trim()) continue;

      // Optimize user input with Prompt Optimizer Agent
      const optimized = await optimizer.optimize(input);
      const processedInput = optimized.command;

      // Log optimization if it was normalized
      if (optimized.intent) {
        console.log(`\n💡 ${optimized.intent}\n`);
      }

      const lower = processedInput.toLowerCase();

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
      const toolResult = await tools.handleCommand(processedInput);
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