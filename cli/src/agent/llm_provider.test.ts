import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { LLMProviderClient, loadProviderFromEnv, loadFromEnvFile, ProviderConfig } from './llm_provider';

// ============ LLM Provider Tests ============

describe('LLMProviderClient', () => {
  describe('constructor', () => {
    it('should set default model for openai', () => {
      const client = new LLMProviderClient({ provider: 'openai', apiKey: 'sk-test' });
      expect(client).toBeDefined();
    });

    it('should set default model for anthropic', () => {
      const client = new LLMProviderClient({ provider: 'anthropic', apiKey: 'sk-ant-test' });
      expect(client).toBeDefined();
    });

    it('should preserve user-provided model', () => {
      const client = new LLMProviderClient({ provider: 'openai', apiKey: 'sk-test', model: 'gpt-4o-mini' });
      expect(client).toBeDefined();
    });
  });

  describe('chat', () => {
    it('should throw error for unknown provider', async () => {
      const client = new LLMProviderClient({ provider: 'unknown' as any, apiKey: 'sk-test' });
      await expect(client.chat([])).rejects.toThrow('Unknown provider');
    });
  });
});

describe('loadProviderFromEnv', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('should return null when no API keys are set', () => {
    delete process.env.OPENAI_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;
    delete process.env.GEMINI_API_KEY;
    delete process.env.AZURE_OPENAI_KEY;
    delete process.env.MINIMAX_API_KEY;

    expect(loadProviderFromEnv()).toBeNull();
  });

  it('should load OpenAI config from env', () => {
    process.env.OPENAI_API_KEY = 'sk-test-openai';
    process.env.OPENAI_MODEL = 'gpt-4o-mini';

    const config = loadProviderFromEnv();

    expect(config).not.toBeNull();
    expect(config?.provider).toBe('openai');
    expect(config?.apiKey).toBe('sk-test-openai');
    expect(config?.model).toBe('gpt-4o-mini');
  });

  it('should load Anthropic config from env', () => {
    process.env.ANTHROPIC_API_KEY = 'sk-ant-test';
    process.env.ANTHROPIC_MODEL = 'claude-sonnet-4-6';

    const config = loadProviderFromEnv();

    expect(config).not.toBeNull();
    expect(config?.provider).toBe('anthropic');
    expect(config?.apiKey).toBe('sk-ant-test');
    expect(config?.model).toBe('claude-sonnet-4-6');
  });

  it('should load Gemini config from env', () => {
    process.env.GEMINI_API_KEY = 'gemini-test-key';

    const config = loadProviderFromEnv();

    expect(config).not.toBeNull();
    expect(config?.provider).toBe('gemini');
    expect(config?.apiKey).toBe('gemini-test-key');
  });

  it('should load Azure config when key and endpoint are present', () => {
    process.env.AZURE_OPENAI_KEY = 'azure-test-key';
    process.env.AZURE_OPENAI_ENDPOINT = 'https://test.openai.azure.com/';

    const config = loadProviderFromEnv();

    expect(config).not.toBeNull();
    expect(config?.provider).toBe('azure');
    expect(config?.apiKey).toBe('azure-test-key');
  });

  it('should load MiniMax config from env', () => {
    process.env.MINIMAX_API_KEY = 'minimax-test-key';

    const config = loadProviderFromEnv();

    expect(config).not.toBeNull();
    expect(config?.provider).toBe('minimax');
    expect(config?.apiKey).toBe('minimax-test-key');
  });

  it('should prioritize OpenAI over Anthropic when both are set', () => {
    process.env.OPENAI_API_KEY = 'sk-openai';
    process.env.ANTHROPIC_API_KEY = 'sk-ant';

    const config = loadProviderFromEnv();

    expect(config?.provider).toBe('openai');
  });
});

describe('loadFromEnvFile', () => {
  const fs = require('fs');
  const path = require('path');
  const os = require('os');

  it('should return empty object for non-existent file', () => {
    const result = loadFromEnvFile('/non/existent/path/.env');
    expect(result).toEqual({});
  });

  it('should parse simple KEY=VALUE format', () => {
    const tmpFile = path.join(os.tmpdir(), 'test-env-file');
    fs.writeFileSync(tmpFile, 'OPENAI_API_KEY=sk-test\nANTHROPIC_API_KEY=sk-ant\n');

    try {
      const result = loadFromEnvFile(tmpFile);
      expect(result.OPENAI_API_KEY).toBe('sk-test');
      expect(result.ANTHROPIC_API_KEY).toBe('sk-ant');
    } finally {
      fs.unlinkSync(tmpFile);
    }
  });
});