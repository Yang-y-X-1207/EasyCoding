/**
 * Claude Code Style Local CLI
 * Direct AI chat with local file operations
 * Supports: OpenAI, Anthropic, Google Gemini, Azure
 */

import * as readline from "readline";
import * as path from "path";
import { LLMProviderClient, loadProviderFromEnv, loadFromEnvFile, ProviderConfig, ToolCall } from "./llm_provider";
import { PromptOptimizer } from "./prompt_optimizer";
import { ToolRegistry, executeToolCalls } from "./tool_registry";

interface Message {
  role: "user" | "assistant" | "tool";
  content: string;
  tool_call_id?: string;
  tool_name?: string;
}

// ============ Response Parser ============

/**
 * Handle direct tool commands (e.g., "read src/index.ts", "!ls -la")
 */
async function handleDirectCommand(registry: ToolRegistry, input: string): Promise<string | null> {
  const trimmed = input.trim();
  const lower = trimmed.toLowerCase();

  // "read <path>" command
  if (trimmed.startsWith("read ")) {
    const filePath = trimmed.slice(5).trim();
    const result = await registry.execute("read_file", { path: filePath });
    return result.success ? result.content : `⚠️ ${result.error}`;
  }

  // "write <path> <content>" command
  if (trimmed.startsWith("write ")) {
    const parts = trimmed.slice(6).split(" ");
    if (parts.length >= 2) {
      const filePath = parts[0];
      const content = parts.slice(1).join(" ");
      const result = await registry.execute("write_file", { path: filePath, content });
      return result.success ? result.content : `⚠️ ${result.error}`;
    }
    return "⚠️ 用法: write <path> <content>";
  }

  // "!<command>" shell execution
  if (trimmed.startsWith("!")) {
    const cmd = trimmed.slice(1).trim();
    const result = await registry.execute("exec", { command: cmd });
    return result.success ? result.content : `⚠️ ${result.error}`;
  }

  // "ls [path]" command
  if (trimmed.startsWith("ls")) {
    const dirPath = trimmed.slice(2).trim() || ".";
    const result = await registry.execute("list_dir", { path: dirPath });
    return result.success ? result.content : `⚠️ ${result.error}`;
  }

  // "grep <pattern> [path]" command
  if (trimmed.startsWith("grep ")) {
    const parts = trimmed.slice(4).trim().split(" ");
    if (parts.length >= 1) {
      const pattern = parts[0];
      const searchPath = parts[1] || ".";
      const result = await registry.execute("grep", { pattern, path: searchPath });
      return result.success ? result.content : `⚠️ ${result.error}`;
    }
  }

  return null;
}

/**
 * Parse LLM response to detect failure indicators
 */
function parseResponse(content: string, stopReason?: string): { success: boolean; displayContent: string } {
  const trimmed = content.trim();

  // If the API reported an error stop_reason, treat as failure
  if (stopReason === "error" || stopReason === "incomplete") {
    return {
      success: false,
      displayContent: `❌ API错误: ${stopReason}\n\n${trimmed || "LLM返回错误，请稍后重试。"}`,
    };
  }

  // Patterns indicating task failure or inability to complete
  const failurePatterns = [
    /无法完成/i,
    /无法做到/i,
    /做不到/i,
    /无法执行/i,
    /无法处理/i,
    /无法回答/i,
    /无法帮你/i,
    /做不到的/i,
    /无法胜任/i,
    /超出能力范围/i,
    /无法访问/i,
    /没有权限/i,
    /无法读取/i,
    /找不到/i,
    /不存在/i,
    /无法创建/i,
    /无法写入/i,
    /失败了/i,
  ];

  // Check if response explicitly says it can't complete the task
  for (const pattern of failurePatterns) {
    if (pattern.test(trimmed)) {
      return {
        success: false,
        displayContent: `❌ ${trimmed}`,
      };
    }
  }

  // Check for explicit refusal patterns
  const refusalPatterns = [
    /我不能/i,
    /我不可以/i,
    /我无法/i,
    /我没有办法/i,
    /抱歉.*无法/i,
    /对不起.*无法/i,
  ];

  for (const pattern of refusalPatterns) {
    if (pattern.test(trimmed)) {
      return {
        success: false,
        displayContent: `❌ ${trimmed}`,
      };
    }
  }

  // Response seems fine
  return {
    success: true,
    displayContent: `🤖 ${trimmed}`,
  };
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
  const registry = new ToolRegistry(projectPath);
  const messages: Message[] = [];

  const providerNames: Record<string, string> = {
    openai: "OpenAI GPT",
    anthropic: "Anthropic Claude",
    gemini: "Google Gemini",
    azure: "Azure OpenAI",
  };

  const systemPrompt = `你是 Coding-CLI，一个专业的 AI 编程助手。

当你需要读取文件、执行命令或写入文件时，请使用可用的工具。
你可以使用的工具包括：read_file, write_file, exec, list_dir, grep

当用户要求你创建文件或写入内容时，请使用 write_file 工具。
当用户要求读取文件内容时，请使用 read_file 工具。
当用户要求执行命令时，请使用 exec 工具。

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

      // Check for direct tool commands first (e.g., "read src/index.ts")
      const directResult = await handleDirectCommand(registry, processedInput);
      if (directResult) {
        console.log(`\n${directResult}\n`);
        messages.push({ role: "user", content: input });
        messages.push({ role: "assistant", content: directResult });
        continue;
      }

      // Send to LLM with tools
      console.log("\n🤖 AI 思考中...\n");
      try {
        messages.push({ role: "user", content: input });

        // Get tool definitions
        const toolDefs = registry.getDefinitions();

        // Call LLM with tools
        const response = await client.chat(messages, systemPrompt, toolDefs);

        // If LLM returned tool calls, execute them
        if (response.tool_calls && response.tool_calls.length > 0) {
          console.log(`\n🔧 执行 ${response.tool_calls.length} 个工具...\n`);

          // Execute tool calls
          const toolResults = await executeToolCalls(registry, response.tool_calls);

          // Add assistant message with tool calls
          messages.push({
            role: "assistant",
            content: response.content || "",
            // Keep tool_calls info in the message for context
          });

          // Add tool results as tool messages
          for (const result of toolResults) {
            messages.push({
              role: "tool",
              content: result.content,
              tool_call_id: result.tool_call_id,
              tool_name: response.tool_calls.find(tc => tc.id === result.tool_call_id)?.name,
            });
          }

          // Get final response from LLM after tool execution
          const finalResponse = await client.chat(messages, systemPrompt);
          const parsed = parseResponse(finalResponse.content, finalResponse.stop_reason);
          console.log(`\n${parsed.displayContent}\n`);
          messages.push({ role: "assistant", content: finalResponse.content });
        } else {
          // No tool calls, just display the response
          const parsed = parseResponse(response.content, response.stop_reason);
          console.log(`\n${parsed.displayContent}\n`);
          messages.push({ role: "assistant", content: response.content });
        }
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