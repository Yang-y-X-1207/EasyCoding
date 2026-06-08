/**
 * Tool Registry & Executor
 * Manages tools and executes tool calls from LLM
 */

import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";
import { ToolDefinition, ToolCall } from "./llm_provider";

/**
 * Tool execution result
 */
export interface ToolResult {
  success: boolean;
  content: string;
  error?: string;
}

/**
 * Base Tool class
 */
export abstract class Tool {
  abstract name: string;
  abstract description: string;
  abstract parameters: ToolDefinition["parameters"];

  abstract execute(params: Record<string, any>): Promise<ToolResult> | ToolResult;

  toSchema(): ToolDefinition {
    return {
      name: this.name,
      description: this.description,
      parameters: this.parameters,
    };
  }
}

/**
 * Read File Tool
 */
export class ReadFileTool extends Tool {
  name = "read_file";
  description = "Read contents of a file from the filesystem";
  parameters = {
    type: "object",
    properties: {
      path: {
        type: "string",
        description: "The file path to read",
      },
    },
    required: ["path"],
  };

  constructor(private workspace: string) {
    super();
  }

  execute(params: Record<string, any>): ToolResult {
    const filePath = path.isAbsolute(params.path) ? params.path : path.join(this.workspace, params.path);

    if (!fs.existsSync(filePath)) {
      return { success: false, content: "", error: `File not found: ${params.path}` };
    }

    try {
      const stat = fs.statSync(filePath);
      if (stat.isDirectory()) {
        const items = fs.readdirSync(filePath);
        return {
          success: true,
          content: `📁 ${params.path}/\n` + items.slice(0, 50).map(item => {
            const itemPath = path.join(filePath, item);
            const s = fs.statSync(itemPath);
            return `   ${s.isDirectory() ? "📂" : "📄"} ${item}`;
          }).join("\n") + (items.length > 50 ? `\n   ... 还有 ${items.length - 50} 项` : ""),
        };
      }

      const content = fs.readFileSync(filePath, "utf-8");
      const lines = content.split("\n").length;
      return {
        success: true,
        content: `📄 ${params.path} (${lines} 行)\n\`\`\`\n${content.slice(0, 3000)}${content.length > 3000 ? "\n...(截断)" : ""}\n\`\`\``,
      };
    } catch (e: any) {
      return { success: false, content: "", error: `Failed to read file: ${e.message}` };
    }
  }
}

/**
 * Write File Tool
 */
export class WriteFileTool extends Tool {
  name = "write_file";
  description = "Write content to a file. Creates new file or overwrites existing.";
  parameters = {
    type: "object",
    properties: {
      path: {
        type: "string",
        description: "The file path to write",
      },
      content: {
        type: "string",
        description: "The content to write to the file",
      },
    },
    required: ["path", "content"],
  };

  constructor(private workspace: string) {
    super();
  }

  execute(params: Record<string, any>): ToolResult {
    const filePath = path.isAbsolute(params.path) ? params.path : path.join(this.workspace, params.path);

    try {
      const dir = path.dirname(filePath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(filePath, params.content, "utf-8");
      return { success: true, content: `✅ 已写入: ${params.path} (${params.content.length} 字符)` };
    } catch (e: any) {
      return { success: false, content: "", error: `Failed to write file: ${e.message}` };
    }
  }
}

/**
 * Execute Shell Command Tool
 */
export class ExecTool extends Tool {
  name = "exec";
  description = "Execute a shell command and return the output";
  parameters = {
    type: "object",
    properties: {
      command: {
        type: "string",
        description: "The shell command to execute",
      },
      working_dir: {
        type: "string",
        description: "Optional working directory for the command",
      },
    },
    required: ["command"],
  };

  constructor(private workspace: string) {
    super();
  }

  execute(params: Record<string, any>): ToolResult {
    const cwd = params.working_dir || this.workspace;

    try {
      const output = execSync(params.command, {
        cwd,
        encoding: "utf-8",
        timeout: 30000,
      });
      return {
        success: true,
        content: `🔧 执行: ${params.command}\n\`\`\`\n${output || "(无输出)"}\n\`\`\``,
      };
    } catch (e: any) {
      return {
        success: false,
        content: "",
        error: `Command failed: ${e.message}`,
      };
    }
  }
}

/**
 * List Directory Tool
 */
export class ListDirTool extends Tool {
  name = "list_dir";
  description = "List contents of a directory";
  parameters = {
    type: "object",
    properties: {
      path: {
        type: "string",
        description: "The directory path to list (defaults to workspace root)",
      },
    },
  };

  constructor(private workspace: string) {
    super();
  }

  execute(params: Record<string, any>): ToolResult {
    const dirPath = params.path
      ? (path.isAbsolute(params.path) ? params.path : path.join(this.workspace, params.path))
      : this.workspace;

    try {
      const items = fs.readdirSync(dirPath);
      return {
        success: true,
        content: `📁 ${params.path || "."}/\n` + items.slice(0, 50).map(item => {
          const itemPath = path.join(dirPath, item);
          const stat = fs.statSync(itemPath);
          return `   ${stat.isDirectory() ? "📂" : "📄"} ${item}`;
        }).join("\n") + (items.length > 50 ? `\n   ... 还有 ${items.length - 50} 项` : ""),
      };
    } catch (e: any) {
      return { success: false, content: "", error: `Failed to list directory: ${e.message}` };
    }
  }
}

/**
 * Search Code Tool (grep)
 */
export class GrepTool extends Tool {
  name = "grep";
  description = "Search for a pattern in files";
  parameters = {
    type: "object",
    properties: {
      pattern: {
        type: "string",
        description: "The search pattern (regex supported)",
      },
      path: {
        type: "string",
        description: "The directory or file path to search in (defaults to workspace)",
      },
      file_pattern: {
        type: "string",
        description: "File pattern to match, e.g. '*.ts' or '*.py'",
      },
    },
    required: ["pattern"],
  };

  constructor(private workspace: string) {
    super();
  }

  execute(params: Record<string, any>): ToolResult {
    const searchPath = params.path
      ? (path.isAbsolute(params.path) ? params.path : path.join(this.workspace, params.path))
      : this.workspace;

    const filePattern = params.file_pattern || "*.{ts,js,py,java}";

    try {
      // Simple grep using find + grep
      const result = execSync(
        `find "${searchPath}" -type f -name "${filePattern}" -exec grep -n "${params.pattern}" {} \\; 2>/dev/null | head -50`,
        { encoding: "utf-8", timeout: 10000 }
      );
      return {
        success: true,
        content: result || `没有找到匹配 "${params.pattern}" 的内容`,
      };
    } catch (e: any) {
      return {
        success: false,
        content: "",
        error: `Search failed: ${e.message}`,
      };
    }
  }
}

/**
 * Tool Registry - manages all available tools
 */
export class ToolRegistry {
  private tools: Map<string, Tool> = new Map();

  constructor(workspace: string) {
    // Register default tools
    this.register(new ReadFileTool(workspace));
    this.register(new WriteFileTool(workspace));
    this.register(new ExecTool(workspace));
    this.register(new ListDirTool(workspace));
    this.register(new GrepTool(workspace));
  }

  register(tool: Tool): void {
    this.tools.set(tool.name, tool);
  }

  get(name: string): Tool | undefined {
    return this.tools.get(name);
  }

  has(name: string): boolean {
    return this.tools.has(name);
  }

  getDefinitions(): ToolDefinition[] {
    return Array.from(this.tools.values()).map(t => t.toSchema());
  }

  async execute(name: string, params: Record<string, any>): Promise<ToolResult> {
    const tool = this.tools.get(name);
    if (!tool) {
      return { success: false, content: "", error: `Tool not found: ${name}` };
    }

    try {
      const result = await tool.execute(params);
      return result;
    } catch (e: any) {
      return { success: false, content: "", error: `Tool execution failed: ${e.message}` };
    }
  }
}

/**
 * Execute a list of tool calls and return results
 */
export async function executeToolCalls(
  registry: ToolRegistry,
  toolCalls: ToolCall[]
): Promise<Array<{ tool_call_id: string; content: string; is_error: boolean }>> {
  const results = [];

  for (const tc of toolCalls) {
    const result = await registry.execute(tc.name, tc.arguments);

    // Format for LLM conversation
    let content: string;
    let is_error: boolean;

    if (result.success) {
      content = result.content;
      is_error = false;
    } else {
      content = `Error: ${result.error}`;
      is_error = true;
    }

    results.push({
      tool_call_id: tc.id,
      content,
      is_error,
    });
  }

  return results;
}