/**
 * Prompt Optimizer Agent
 * Normalizes user input before sending to coding agent
 * Handles Chinese colloquialisms, extracts intent and paths
 */

import { LLMProviderClient, ProviderConfig } from "./llm_provider";

/**
 * Optimized command result
 */
export interface OptimizedCommand {
  /** The normalized command to execute */
  command: string;
  /** Whether the input was recognized as a tool command */
  isToolCommand: boolean;
  /** Original input */
  original: string;
  /** Intent description if not a direct command */
  intent?: string;
}

/**
 * Prompt Optimizer Agent
 * Converts natural language / Chinese colloquialisms into proper commands
 */
export class PromptOptimizer {
  private llm: LLMProviderClient | null = null;
  private model: string;

  constructor(config: ProviderConfig) {
    this.llm = new LLMProviderClient(config);
    this.model = config.model || "claude-sonnet-4-7";
  }

  /**
   * Optimize user input
   * First tries rule-based extraction, then falls back to LLM for complex cases
   */
  async optimize(input: string): Promise<OptimizedCommand> {
    const trimmed = input.trim();

    // Fast path: check if it's already a direct tool command
    if (this.isDirectToolCommand(trimmed)) {
      return {
        command: trimmed,
        isToolCommand: true,
        original: input,
      };
    }

    // Rule-based extraction for common patterns
    const ruleBased = this.tryRuleBasedExtraction(trimmed);
    if (ruleBased) {
      return ruleBased;
    }

    // LLM-based optimization for complex/natural language inputs
    if (this.looksLikeCommand(trimmed)) {
      return await this.optimizeWithLLM(trimmed);
    }

    // Not recognized as a command, return as-is for coding agent
    return {
      command: trimmed,
      isToolCommand: false,
      original: input,
    };
  }

  /**
   * Check if input is already a direct tool command
   */
  private isDirectToolCommand(input: string): boolean {
    const directCommands = [
      "read ", "write ", "ls", "grep ", "!",
      "exit", "clear", "history", "help",
      "src/", "lib/", "app/", "dist/", "test/",
      "package.json", "tsconfig.json", "*.ts", "*.js"
    ];

    for (const cmd of directCommands) {
      if (input.startsWith(cmd)) {
        return true;
      }
    }
    return false;
  }

  /**
   * Check if input looks like it might be a command
   */
  private looksLikeCommand(input: string): boolean {
    // Chinese characters at start
    const firstCharCode = input.charCodeAt(0);
    if (firstCharCode > 127) {
      return true;
    }

    // Contains path indicators
    if (input.includes("/") || input.includes("\\")) {
      return true;
    }

    // Common command patterns
    const patterns = [
      /^read\s+/i, /^write\s+/i, /^ls\s*/i, /^grep\s+/i,
      /^(帮我|请|麻烦)?\s*(看|读|查|打开|查看)/,
      /^(运行|执行)\s+/,
    ];

    for (const pattern of patterns) {
      if (pattern.test(input)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Try rule-based command extraction
   */
  private tryRuleBasedExtraction(input: string): OptimizedCommand | null {
    const lower = input.toLowerCase();

    // Chinese command patterns -> normalized commands
    const chinesePatterns: Array<{ pattern: RegExp; normalize: (match: RegExpMatchArray) => string }> = [
      // "读一下 <path>" -> "read <path>"
      { pattern: /^读一下\s+(.+)/, normalize: (m) => `read ${m[1]}` },
      { pattern: /^看一下\s+(.+)/, normalize: (m) => `read ${m[1]}` },
      { pattern: /^看看\s+(.+)/, normalize: (m) => `read ${m[1]}` },

      // "帮我看 <path>" -> "read <path>"
      { pattern: /^帮我看\s+(.+)/, normalize: (m) => `read ${m[1]}` },
      { pattern: /^帮我读\s+(.+)/, normalize: (m) => `read ${m[1]}` },
      { pattern: /^帮我查看\s+(.+)/, normalize: (m) => `read ${m[1]}` },

      // "麻烦看一下 <path>" -> "read <path>"
      { pattern: /^麻烦看一下\s+(.+)/, normalize: (m) => `read ${m[1]}` },
      { pattern: /^麻烦读一下\s+(.+)/, normalize: (m) => `read ${m[1]}` },

      // "请看一下 <path>" -> "read <path>"
      { pattern: /^请看一下\s+(.+)/, normalize: (m) => `read ${m[1]}` },
      { pattern: /^请读一下\s+(.+)/, normalize: (m) => `read ${m[1]}` },
      { pattern: /^请打开\s+(.+)/, normalize: (m) => `read ${m[1]}` },

      // "打开 <path>" -> "read <path>"
      { pattern: /^打开\s+(.+)/, normalize: (m) => `read ${m[1]}` },

      // "浏览 <path>" -> "read <path>"
      { pattern: /^浏览\s+(.+)/, normalize: (m) => `read ${m[1]}` },

      // "导航到 <path>" -> "read <path>"
      { pattern: /^导航到\s+(.+)/, normalize: (m) => `read ${m[1]}` },

      // "查看目录" -> "ls"
      { pattern: /^查看目录\s*$/, normalize: () => "ls" },
      { pattern: /^看看目录\s*$/, normalize: () => "ls" },
      { pattern: /^目录结构\s*$/, normalize: () => "ls" },

      // "运行 <command>" -> "!<command>"
      { pattern: /^运行\s+(.+)/, normalize: (m) => `!${m[1]}` },
      { pattern: /^执行\s+(.+)/, normalize: (m) => `!${m[1]}` },
    ];

    for (const item of chinesePatterns) {
      const match = input.match(item.pattern);
      if (match) {
        return {
          command: item.normalize(match),
          isToolCommand: true,
          original: input,
          intent: `Chinese command normalized: "${input}" -> "${item.normalize(match)}"`,
        };
      }
    }

    return null;
  }

  /**
   * Use LLM to optimize complex inputs
   */
  private async optimizeWithLLM(input: string): Promise<OptimizedCommand> {
    if (!this.llm) {
      // No LLM configured, return as-is
      return {
        command: input,
        isToolCommand: false,
        original: input,
      };
    }

    const systemPrompt = `You are a command normalizer for a coding CLI tool.

Your job is to convert user input into proper tool commands.

Available commands:
- read <path>: Read a file
- write <path> <content>: Write content to a file
- !<command>: Execute a shell command
- ls [path]: List directory contents
- grep <pattern> [path]: Search for pattern in files

Rules:
1. If input is already a valid command, return it as-is
2. If input is a file/directory path, convert to "read <path>"
3. If input is a Chinese command, extract the intent and path
4. If input is natural language about code, return it as-is (not a tool command)

Respond with ONLY the normalized command, nothing else.
If not a tool command, respond with "NOT_A_COMMAND"`;

    try {
      const response = await this.llm.chat(
        [{ role: "user", content: input }],
        systemPrompt
      );

      const normalized = response.content.trim();

      if (normalized === "NOT_A_COMMAND") {
        return {
          command: input,
          isToolCommand: false,
          original: input,
        };
      }

      return {
        command: normalized,
        isToolCommand: true,
        original: input,
        intent: `LLM normalized: "${input}" -> "${normalized}"`,
      };
    } catch (e) {
      // LLM failed, return original input
      return {
        command: input,
        isToolCommand: false,
        original: input,
      };
    }
  }
}

/**
 * Quick helper to create a PromptOptimizer from env config
 */
export function createPromptOptimizerFromEnv(): PromptOptimizer | null {
  const { loadProviderFromEnv } = require("./llm_provider");
  const config = loadProviderFromEnv();
  if (config) {
    return new PromptOptimizer(config);
  }
  return null;
}