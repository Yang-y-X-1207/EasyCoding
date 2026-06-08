/**
 * LLM Provider - Multi-vendor support
 * Supports: OpenAI, Anthropic, Google Gemini, Azure OpenAI, MiniMax
 */

export type LLMProvider = "openai" | "anthropic" | "gemini" | "azure" | "minimax";

interface LLMConfig {
  provider: LLMProvider;
  apiKey: string;
  baseUrl?: string;
  model?: string;
}

interface LLMResponse {
  content: string;
  stop_reason?: string;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
  };
  error?: string;
  tool_calls?: ToolCall[];
}

/**
 * Tool call request from LLM
 */
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

/**
 * Tool definition for LLM
 */
export interface ToolDefinition {
  name: string;
  description: string;
  parameters: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
}

export class LLMProviderClient {
  private config: LLMConfig;

  constructor(config: LLMConfig) {
    // Provide defaults for model
    if (!config.model) {
      switch (config.provider) {
        case "openai":
          config.model = "gpt-4o";
          break;
        case "anthropic":
          config.model = "claude-sonnet-4-7";
          break;
        case "gemini":
          config.model = "gemini-1.5-flash";
          break;
        case "azure":
          config.model = "gpt-4";
          break;
        case "minimax":
          config.model = "abab5.5-chat";
          break;
      }
    }
    this.config = config;
  }

  async chat(
    messages: Array<{ role: string; content: string }>,
    system?: string,
    tools?: ToolDefinition[]
  ): Promise<LLMResponse> {
    switch (this.config.provider) {
      case "openai":
        return this.openaiChat(messages, system, tools);
      case "anthropic":
        return this.anthropicChat(messages, system, tools);
      case "gemini":
        return this.geminiChat(messages, system, tools);
      case "azure":
        return this.azureChat(messages, system, tools);
      case "minimax":
        return this.minimaxChat(messages, system, tools);
      default:
        throw new Error(`Unknown provider: ${this.config.provider}`);
    }
  }

  // ============ OpenAI ============

  private async openaiChat(
    messages: Array<{ role: string; content: string }>,
    system?: string,
    tools?: ToolDefinition[]
  ): Promise<LLMResponse> {
    const url = this.config.baseUrl || "https://api.openai.com/v1/chat/completions";

    const allMessages = system
      ? [{ role: "system", content: system }, ...messages]
      : messages;

    const requestBody: any = {
      model: this.config.model || "gpt-4o",
      messages: allMessages,
      max_tokens: 4096,
    };

    if (tools && tools.length > 0) {
      requestBody.tools = tools.map(t => ({
        type: "function",
        function: {
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        },
      }));
    }

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${this.config.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const err = await response.json() as { error?: { message?: string } };
      throw new Error(err.error?.message || `OpenAI API Error: ${response.status}`);
    }

    const data = await response.json() as {
      choices?: Array<{
        message?: { content?: string; tool_calls?: Array<{ id?: string; function?: { name?: string; arguments?: string } }> };
        finish_reason?: string;
      }>;
      usage?: { prompt_tokens?: number; completion_tokens?: number };
    };

    const choice = data.choices?.[0];
    const message = choice?.message;

    // Extract tool calls if present
    let tool_calls: ToolCall[] | undefined;
    if (message?.tool_calls && message.tool_calls.length > 0) {
      tool_calls = message.tool_calls.map(tc => ({
        id: tc.id || `tc-${Date.now()}`,
        name: tc.function?.name || "unknown",
        arguments: tc.function?.arguments ? JSON.parse(tc.function.arguments) : {},
      }));
    }

    return {
      content: message?.content || "⚠️ 无响应",
      stop_reason: choice?.finish_reason || undefined,
      tool_calls,
      usage: {
        input_tokens: data.usage?.prompt_tokens,
        output_tokens: data.usage?.completion_tokens,
      },
    };
  }

  // ============ Anthropic ============

  private async anthropicChat(
    messages: Array<{ role: string; content: string; tool_call_id?: string; tool_name?: string }>,
    system?: string,
    tools?: ToolDefinition[]
  ): Promise<LLMResponse> {
    const url = this.config.baseUrl || "https://api.anthropic.com/v1/messages";

    // Convert messages to Anthropic format
    // Anthropic expects tool results as tool_result blocks in user messages
    const anthropicMessages = this._convertMessagesForAnthropic(messages);

    const payload: any = {
      model: this.config.model || "claude-sonnet-4-7",
      max_tokens: 4096,
      messages: anthropicMessages,
    };

    if (system) {
      payload.system = system;
    }

    // Add tools if provided (Anthropic uses tools format)
    if (tools && tools.length > 0) {
      payload.tools = tools.map(t => ({
        name: t.name,
        description: t.description,
        input: t.parameters,
      }));
    }

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "x-api-key": this.config.apiKey,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json() as { error?: { message?: string } };
      throw new Error(err.error?.message || `Anthropic API Error: ${response.status}`);
    }

    const data = await response.json() as {
      content?: Array<{ type?: string; text?: string; name?: string; input?: any; id?: string }>;
      usage?: { input_tokens?: number; output_tokens?: number };
      stop_reason?: string;
      error?: { type?: string; message?: string };
    };

    // Check for API errors
    if (data.error) {
      return {
        content: "",
        stop_reason: "error",
        error: data.error.message || `Anthropic API Error: ${data.error.type}`,
        usage: {
          input_tokens: data.usage?.input_tokens,
          output_tokens: data.usage?.output_tokens,
        },
      };
    }

    // Extract text content and tool calls
    let textContent = "";
    let tool_calls: ToolCall[] | undefined;

    if (data.content) {
      for (const block of data.content) {
        if (block.type === "text") {
          textContent += block.text || "";
        } else if (block.type === "tool_use") {
          if (!tool_calls) tool_calls = [];
          tool_calls.push({
            id: block.id || `tc-${Date.now()}`,
            name: block.name || "unknown",
            arguments: block.input || {},
          });
        }
      }
    }

    return {
      content: textContent || "⚠️ 无响应",
      stop_reason: data.stop_reason || "end_turn",
      tool_calls,
      usage: {
        input_tokens: data.usage?.input_tokens,
        output_tokens: data.usage?.output_tokens,
      },
    };
  }

  // ============ Google Gemini ============

  private async geminiChat(
    messages: Array<{ role: string; content: string }>,
    system?: string,
    _tools?: ToolDefinition[]
  ): Promise<LLMResponse> {
    // Gemini tools support would require function declarations format
    // For now, we'll skip tool support for Gemini (requires different payload structure)
    const model = this.config.model || "gemini-1.5-flash";
    const url = this.config.baseUrl || `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;

    const contents = messages.map(m => ({
      role: m.role === "user" ? "user" : "model",
      parts: [{ text: m.content }],
    }));

    const payload: any = {
      contents,
    };

    if (system) {
      payload.systemInstruction = { parts: [{ text: system }] };
    }

    const response = await fetch(`${url}?key=${this.config.apiKey}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json() as { error?: { message?: string } };
      throw new Error(err.error?.message || `Gemini API Error: ${response.status}`);
    }

    const data = await response.json() as {
      candidates?: Array<{ content?: { parts?: Array<{ text?: string; functionCall?: { name?: string; args?: any } }> }; finish_reason?: string }>;
    };

    // Extract text and function calls
    let textContent = "";
    let tool_calls: ToolCall[] | undefined;

    const parts = data.candidates?.[0]?.content?.parts || [];
    for (const part of parts) {
      if (part.text) {
        textContent += part.text;
      } else if (part.functionCall) {
        if (!tool_calls) tool_calls = [];
        tool_calls.push({
          id: `tc-${Date.now()}`,
          name: part.functionCall.name || "unknown",
          arguments: part.functionCall.args || {},
        });
      }
    }

    return {
      content: textContent || "⚠️ 无响应",
      stop_reason: data.candidates?.[0]?.finish_reason || undefined,
      tool_calls,
    };
  }

  // ============ Azure OpenAI ============

  private async azureChat(
    messages: Array<{ role: string; content: string }>,
    system?: string,
    tools?: ToolDefinition[]
  ): Promise<LLMResponse> {
    if (!this.config.baseUrl) {
      throw new Error("Azure OpenAI requires baseUrl (deployment endpoint)");
    }

    const allMessages = system
      ? [{ role: "system", content: system }, ...messages]
      : messages;

    const requestBody: any = {
      messages: allMessages,
      max_tokens: 4096,
    };

    if (tools && tools.length > 0) {
      requestBody.tools = tools.map(t => ({
        type: "function",
        function: {
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        },
      }));
    }

    const response = await fetch(this.config.baseUrl, {
      method: "POST",
      headers: {
        "api-key": this.config.apiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const err = await response.json() as { error?: { message?: string } };
      throw new Error(err.error?.message || `Azure API Error: ${response.status}`);
    }

    const data = await response.json() as {
      choices?: Array<{
        message?: { content?: string; tool_calls?: Array<{ id?: string; function?: { name?: string; arguments?: string } }> };
        finish_reason?: string;
      }>;
    };

    const choice = data.choices?.[0];
    const message = choice?.message;

    let tool_calls: ToolCall[] | undefined;
    if (message?.tool_calls && message.tool_calls.length > 0) {
      tool_calls = message.tool_calls.map(tc => ({
        id: tc.id || `tc-${Date.now()}`,
        name: tc.function?.name || "unknown",
        arguments: tc.function?.arguments ? JSON.parse(tc.function.arguments) : {},
      }));
    }

    return {
      content: message?.content || "⚠️ 无响应",
      stop_reason: choice?.finish_reason || undefined,
      tool_calls,
    };
  }

  // ============ MiniMax ============

  private async minimaxChat(
    messages: Array<{ role: string; content: string }>,
    system?: string,
    tools?: ToolDefinition[]
  ): Promise<LLMResponse> {
    // MiniMax uses OpenAI-compatible API
    const url = this.config.baseUrl || "https://api.minimax.chat/v1/chat/completions";

    const allMessages = system
      ? [{ role: "system", content: system }, ...messages]
      : messages;

    const requestBody: any = {
      model: this.config.model || "MiniMax-01",
      messages: allMessages,
      max_tokens: 4096,
    };

    if (tools && tools.length > 0) {
      requestBody.tools = tools.map(t => ({
        type: "function",
        function: {
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        },
      }));
    }

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${this.config.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const err = await response.json() as { error?: { message?: string } };
      throw new Error(err.error?.message || `MiniMax API Error: ${response.status}`);
    }

    const data = await response.json() as {
      choices?: Array<{
        message?: { content?: string; tool_calls?: Array<{ id?: string; function?: { name?: string; arguments?: string } }> };
        finish_reason?: string;
      }>;
      usage?: { prompt_tokens?: number; completion_tokens?: number };
    };

    const choice = data.choices?.[0];
    const message = choice?.message;

    let tool_calls: ToolCall[] | undefined;
    if (message?.tool_calls && message.tool_calls.length > 0) {
      tool_calls = message.tool_calls.map(tc => ({
        id: tc.id || `tc-${Date.now()}`,
        name: tc.function?.name || "unknown",
        arguments: tc.function?.arguments ? JSON.parse(tc.function.arguments) : {},
      }));
    }

    return {
      content: message?.content || "⚠️ 无响应",
      stop_reason: choice?.finish_reason || undefined,
      tool_calls,
      usage: {
        input_tokens: data.usage?.prompt_tokens,
        output_tokens: data.usage?.completion_tokens,
      },
    };
  }

  /**
   * Convert messages to Anthropic format
   * Tool results must be formatted as tool_result blocks in user messages
   */
  private _convertMessagesForAnthropic(
    messages: Array<{ role: string; content: string; tool_call_id?: string; tool_name?: string }>
  ): any[] {
    const result: any[] = [];
    let i = 0;

    while (i < messages.length) {
      const msg = messages[i];

      if (msg.role === "system") {
        // System messages are handled separately in the payload
        i++;
        continue;
      }

      if (msg.role === "tool") {
        // Tool results need to be embedded in a user message
        // Find the previous user message or create a new one
        const toolResultBlock = {
          type: "tool_result",
          tool_use_id: msg.tool_call_id || "",
          content: msg.content || "",
        };

        // Check if previous message is a user message
        if (result.length > 0 && result[result.length - 1].role === "user") {
          const lastMsg = result[result.length - 1];
          if (Array.isArray(lastMsg.content)) {
            lastMsg.content.push(toolResultBlock);
          } else {
            lastMsg.content = [
              { type: "text", text: lastMsg.content || "" },
              toolResultBlock,
            ];
          }
        } else {
          // Create new user message with tool result
          result.push({
            role: "user",
            content: [toolResultBlock],
          });
        }
        i++;
        continue;
      }

      if (msg.role === "assistant") {
        // Assistant messages need content blocks (like nanobot's _assistant_blocks)
        const contentBlocks: any[] = [];

        if (msg.content) {
          contentBlocks.push({ type: "text", text: msg.content });
        }

        // Handle tool_calls in OpenAI format: { id, function: { name, arguments } }
        // Only include for the LAST assistant message to prevent errors in subsequent turns
        const isLastMessage = i === messages.length - 1;
        const toolCalls = (msg as any).tool_calls;
        if (toolCalls && Array.isArray(toolCalls) && isLastMessage) {
          for (const tc of toolCalls) {
            if (!tc || typeof tc !== 'object') continue;
            const func = tc.function || {};
            const args = func.arguments;
            contentBlocks.push({
              type: "tool_use",
              id: tc.id || `tc-${Date.now()}`,
              name: func.name || "unknown",
              input: typeof args === 'object' ? args : {},
            });
          }
        }

        result.push({
          role: "assistant",
          content: contentBlocks.length > 0 ? contentBlocks : undefined,
        });
        i++;
        continue;
      }

      if (msg.role === "user") {
        const contentBlocks: any[] = [];
        const content = msg.content as string | any[] | undefined;

        if (typeof content === "string") {
          contentBlocks.push({ type: "text", text: content });
        } else if (Array.isArray(content)) {
          // Content might already be blocks
          for (const block of content) {
            if (typeof block === "string") {
              contentBlocks.push({ type: "text", text: block });
            } else {
              contentBlocks.push(block);
            }
          }
        }

        result.push({
          role: "user",
          content: contentBlocks.length > 0 ? contentBlocks : [{ type: "text", text: "" }],
        });
        i++;
        continue;
      }

      i++;
    }

    return result;
  }
}

// ============ Config Loader ============

export interface ProviderConfig {
  provider: LLMProvider;
  apiKey: string;
  model?: string;
  baseUrl?: string;
}

export function loadProviderFromEnv(): ProviderConfig | null {
  // Check OpenAI
  const openaiKey = process.env.OPENAI_API_KEY || process.env.OPENAI_KEY;
  if (openaiKey) {
    return {
      provider: "openai",
      apiKey: openaiKey,
      model: process.env.OPENAI_MODEL || "gpt-4o",
      baseUrl: process.env.OPENAI_BASE_URL,
    };
  }

  // Check Anthropic
  const anthropicKey = process.env.ANTHROPIC_API_KEY;
  if (anthropicKey) {
    return {
      provider: "anthropic",
      apiKey: anthropicKey,
      model: process.env.ANTHROPIC_MODEL || "claude-sonnet-4-7",
      baseUrl: process.env.ANTHROPIC_BASE_URL,
    };
  }

  // Check Google Gemini
  const geminiKey = process.env.GEMINI_API_KEY;
  if (geminiKey) {
    return {
      provider: "gemini",
      apiKey: geminiKey,
      model: process.env.GEMINI_MODEL || "gemini-1.5-flash",
    };
  }

  // Check Azure
  const azureKey = process.env.AZURE_OPENAI_KEY;
  const azureUrl = process.env.AZURE_OPENAI_ENDPOINT;
  if (azureKey && azureUrl) {
    return {
      provider: "azure",
      apiKey: azureKey,
      model: process.env.AZURE_OPENAI_DEPLOYMENT || "gpt-4",
      baseUrl: azureUrl,
    };
  }

  // Check MiniMax
  const minimaxKey = process.env.MINIMAX_API_KEY || process.env.MINIMAX_API_TOKEN;
  if (minimaxKey) {
    return {
      provider: "minimax",
      apiKey: minimaxKey,
      model: process.env.MINIMAX_MODEL || "abab5.5-chat",
      baseUrl: process.env.MINIMAX_BASE_URL || "https://api.minimax.chat/v1/chat/completions",
    };
  }

  return null;
}

export function loadFromEnvFile(envPath: string): Record<string, string> {
  try {
    const fs = require("fs");
    const path = require("path");
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, "utf-8");
      const result: Record<string, string> = {};
      content.split("\n").forEach((line: string) => {
        const match = line.match(/^(\w+)\s*=\s*(.+)/);
        if (match) {
          result[match[1]] = match[2].trim();
        }
      });
      return result;
    }
  } catch (e) {
    // Ignore
  }
  return {};
}