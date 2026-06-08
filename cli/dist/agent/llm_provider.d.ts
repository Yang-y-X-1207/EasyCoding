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
    usage?: {
        input_tokens?: number;
        output_tokens?: number;
    };
}
export declare class LLMProviderClient {
    private config;
    constructor(config: LLMConfig);
    chat(messages: Array<{
        role: string;
        content: string;
    }>, system?: string): Promise<LLMResponse>;
    private openaiChat;
    private anthropicChat;
    private geminiChat;
    private azureChat;
    private minimaxChat;
}
export interface ProviderConfig {
    provider: LLMProvider;
    apiKey: string;
    model?: string;
    baseUrl?: string;
}
export declare function loadProviderFromEnv(): ProviderConfig | null;
export declare function loadFromEnvFile(envPath: string): Record<string, string>;
export {};
//# sourceMappingURL=llm_provider.d.ts.map