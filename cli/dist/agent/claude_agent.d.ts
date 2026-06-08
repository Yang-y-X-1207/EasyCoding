/**
 * Claude Code Style Local CLI
 * Direct AI chat with local file operations
 * Supports: OpenAI, Anthropic, Google Gemini, Azure
 */
import { LLMProviderClient, loadProviderFromEnv } from "./llm_provider";
export declare function runDirectChat(projectPath?: string, apiKey?: string, model?: string): Promise<void>;
export { LLMProviderClient, loadProviderFromEnv };
//# sourceMappingURL=claude_agent.d.ts.map