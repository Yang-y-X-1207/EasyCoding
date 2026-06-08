import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { PromptOptimizer } from './prompt_optimizer';

// Mock LLMProviderClient
vi.mock('./llm_provider', () => ({
  LLMProviderClient: vi.fn().mockImplementation(() => ({
    chat: vi.fn().mockResolvedValue({ content: 'NOT_A_COMMAND' }),
  })),
  loadProviderFromEnv: vi.fn().mockReturnValue(null),
}));

describe('PromptOptimizer', () => {
  let optimizer: PromptOptimizer;

  beforeEach(() => {
    optimizer = new PromptOptimizer({
      provider: 'anthropic',
      apiKey: 'sk-test',
      model: 'claude-sonnet-4-7',
    });
  });

  describe('tryRuleBasedExtraction', () => {
    it('should normalize "读一下 <path>"', async () => {
      const result = await optimizer.optimize('读一下 src/index.ts');
      expect(result.command).toBe('read src/index.ts');
      expect(result.isToolCommand).toBe(true);
    });

    it('should normalize "看一下 <path>"', async () => {
      const result = await optimizer.optimize('看一下 package.json');
      expect(result.command).toBe('read package.json');
      expect(result.isToolCommand).toBe(true);
    });

    it('should normalize "帮我看 <path>"', async () => {
      const result = await optimizer.optimize('帮我看 cli/src/index.ts');
      expect(result.command).toBe('read cli/src/index.ts');
      expect(result.isToolCommand).toBe(true);
    });

    it('should normalize "请打开 <path>"', async () => {
      const result = await optimizer.optimize('请打开 backend/main.py');
      expect(result.command).toBe('read backend/main.py');
      expect(result.isToolCommand).toBe(true);
    });

    it('should normalize "打开 <path>"', async () => {
      const result = await optimizer.optimize('打开 src/agent/claude_agent.ts');
      expect(result.command).toBe('read src/agent/claude_agent.ts');
      expect(result.isToolCommand).toBe(true);
    });

    it('should normalize "查看目录" to "ls"', async () => {
      const result = await optimizer.optimize('查看目录');
      expect(result.command).toBe('ls');
      expect(result.isToolCommand).toBe(true);
    });

    it('should normalize "运行 <command>" to "!<command>"', async () => {
      const result = await optimizer.optimize('运行 ls -la');
      expect(result.command).toBe('!ls -la');
      expect(result.isToolCommand).toBe(true);
    });

    it('should normalize "执行 <command>" to "!<command>"', async () => {
      const result = await optimizer.optimize('执行 pwd');
      expect(result.command).toBe('!pwd');
      expect(result.isToolCommand).toBe(true);
    });

    it('should pass through direct tool commands', async () => {
      const result = await optimizer.optimize('read src/index.ts');
      expect(result.command).toBe('read src/index.ts');
      expect(result.isToolCommand).toBe(true);
    });

    it('should pass through shell commands', async () => {
      const result = await optimizer.optimize('!ls -la');
      expect(result.command).toBe('!ls -la');
      expect(result.isToolCommand).toBe(true);
    });

    it('should handle path-only inputs as read commands', async () => {
      const result = await optimizer.optimize('src/index.ts');
      expect(result.isToolCommand).toBe(true);
      expect(result.command).toBe('src/index.ts');
    });

    it('should keep natural language as-is when not recognized', async () => {
      const result = await optimizer.optimize('帮我写一个排序算法');
      expect(result.isToolCommand).toBe(false);
      expect(result.command).toBe('帮我写一个排序算法');
    });
  });

  describe('isDirectToolCommand', () => {
    it('should recognize direct commands', async () => {
      const result1 = await optimizer.optimize('ls');
      expect(result1.isToolCommand).toBe(true);

      const result2 = await optimizer.optimize('help');
      expect(result2.isToolCommand).toBe(true);

      const result3 = await optimizer.optimize('history');
      expect(result3.isToolCommand).toBe(true);
    });
  });

   describe('intent tracking', () => {
    it('should include intent when normalized', async () => {
      const result = await optimizer.optimize('读一下 src/index.ts');
      expect(result.intent).toBeDefined();
      expect(result.intent).toContain('Chinese command normalized');
    });
  });
});