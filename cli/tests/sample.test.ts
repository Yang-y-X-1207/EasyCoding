import { describe, it, expect } from 'vitest';

describe('Sample Tests', () => {
  it('should add numbers correctly', () => {
    expect(1 + 1).toBe(2);
  });

  it('should handle string operations', () => {
    const str = 'hello world';
    expect(str.toUpperCase()).toBe('HELLO WORLD');
    expect(str.includes('hello')).toBe(true);
  });
});

describe('LLM Provider', () => {
  it('should have correct config structure', () => {
    const config = {
      provider: 'anthropic',
      apiKey: 'test-key',
      model: 'claude-sonnet-4-7',
    };
    expect(config.provider).toBe('anthropic');
    expect(config.model).toBe('claude-sonnet-4-7');
  });
});