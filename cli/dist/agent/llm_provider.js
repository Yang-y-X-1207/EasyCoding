"use strict";
/**
 * LLM Provider - Multi-vendor support
 * Supports: OpenAI, Anthropic, Google Gemini, Azure OpenAI, MiniMax
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.LLMProviderClient = void 0;
exports.loadProviderFromEnv = loadProviderFromEnv;
exports.loadFromEnvFile = loadFromEnvFile;
class LLMProviderClient {
    constructor(config) {
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
    async chat(messages, system) {
        switch (this.config.provider) {
            case "openai":
                return this.openaiChat(messages, system);
            case "anthropic":
                return this.anthropicChat(messages, system);
            case "gemini":
                return this.geminiChat(messages, system);
            case "azure":
                return this.azureChat(messages, system);
            case "minimax":
                return this.minimaxChat(messages, system);
            default:
                throw new Error(`Unknown provider: ${this.config.provider}`);
        }
    }
    // ============ OpenAI ============
    async openaiChat(messages, system) {
        const url = this.config.baseUrl || "https://api.openai.com/v1/chat/completions";
        const allMessages = system
            ? [{ role: "system", content: system }, ...messages]
            : messages;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${this.config.apiKey}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                model: this.config.model || "gpt-4o",
                messages: allMessages,
                max_tokens: 4096,
            }),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error?.message || `OpenAI API Error: ${response.status}`);
        }
        const data = await response.json();
        return {
            content: data.choices?.[0]?.message?.content || "⚠️ 无响应",
            usage: {
                input_tokens: data.usage?.prompt_tokens,
                output_tokens: data.usage?.completion_tokens,
            },
        };
    }
    // ============ Anthropic ============
    async anthropicChat(messages, system) {
        const url = this.config.baseUrl || "https://api.anthropic.com/v1/messages";
        const payload = {
            model: this.config.model || "claude-sonnet-4-7",
            max_tokens: 4096,
            messages: messages.map(m => ({
                role: m.role === "assistant" ? "assistant" : "user",
                content: m.content,
            })),
        };
        if (system) {
            payload.system = system;
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
            const err = await response.json();
            throw new Error(err.error?.message || `Anthropic API Error: ${response.status}`);
        }
        const data = await response.json();
        return {
            content: data.content?.[0]?.text || "⚠️ 无响应",
            usage: {
                input_tokens: data.usage?.input_tokens,
                output_tokens: data.usage?.output_tokens,
            },
        };
    }
    // ============ Google Gemini ============
    async geminiChat(messages, system) {
        const model = this.config.model || "gemini-1.5-flash";
        const url = this.config.baseUrl || `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
        const contents = messages.map(m => ({
            role: m.role === "user" ? "user" : "model",
            parts: [{ text: m.content }],
        }));
        const payload = {
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
            const err = await response.json();
            throw new Error(err.error?.message || `Gemini API Error: ${response.status}`);
        }
        const data = await response.json();
        return {
            content: data.candidates?.[0]?.content?.parts?.[0]?.text || "⚠️ 无响应",
        };
    }
    // ============ Azure OpenAI ============
    async azureChat(messages, system) {
        if (!this.config.baseUrl) {
            throw new Error("Azure OpenAI requires baseUrl (deployment endpoint)");
        }
        const allMessages = system
            ? [{ role: "system", content: system }, ...messages]
            : messages;
        const response = await fetch(this.config.baseUrl, {
            method: "POST",
            headers: {
                "api-key": this.config.apiKey,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                messages: allMessages,
                max_tokens: 4096,
            }),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error?.message || `Azure API Error: ${response.status}`);
        }
        const data = await response.json();
        return {
            content: data.choices?.[0]?.message?.content || "⚠️ 无响应",
        };
    }
    // ============ MiniMax ============
    async minimaxChat(messages, system) {
        // MiniMax uses OpenAI-compatible API
        const url = this.config.baseUrl || "https://api.minimax.chat/v1/chat/completions";
        const allMessages = system
            ? [{ role: "system", content: system }, ...messages]
            : messages;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${this.config.apiKey}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                model: this.config.model || "MiniMax-01",
                messages: allMessages,
                max_tokens: 4096,
            }),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error?.message || `MiniMax API Error: ${response.status}`);
        }
        const data = await response.json();
        return {
            content: data.choices?.[0]?.message?.content || "⚠️ 无响应",
            usage: {
                input_tokens: data.usage?.prompt_tokens,
                output_tokens: data.usage?.completion_tokens,
            },
        };
    }
}
exports.LLMProviderClient = LLMProviderClient;
function loadProviderFromEnv() {
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
function loadFromEnvFile(envPath) {
    try {
        const fs = require("fs");
        const path = require("path");
        if (fs.existsSync(envPath)) {
            const content = fs.readFileSync(envPath, "utf-8");
            const result = {};
            content.split("\n").forEach((line) => {
                const match = line.match(/^(\w+)\s*=\s*(.+)/);
                if (match) {
                    result[match[1]] = match[2].trim();
                }
            });
            return result;
        }
    }
    catch (e) {
        // Ignore
    }
    return {};
}
//# sourceMappingURL=llm_provider.js.map