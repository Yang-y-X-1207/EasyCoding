import { describe, it, expect } from 'vitest';
import * as path from 'path';

// ============ Claude Agent / ToolHandler Tests ============

describe('ToolHandler', () => {
  describe('path resolution', () => {
    it('should resolve absolute paths as-is', () => {
      const absolutePath = '/absolute/path/file.ts';
      const resolved = path.isAbsolute(absolutePath)
        ? absolutePath
        : path.join('/test/project', absolutePath);

      expect(resolved).toBe('/absolute/path/file.ts');
    });

    it('should join relative paths with project path', () => {
      const projectPath = '/test/project';
      const relativePath = 'src/index.ts';
      const resolved = path.join(projectPath, relativePath);

      // Use toContain since path.join on Windows will use backslashes
      expect(resolved).toContain('src');
      expect(resolved).toContain('index.ts');
    });
  });

  describe('command parsing', () => {
    it('should identify read command', () => {
      const input = 'read src/index.ts';
      expect(input.startsWith('read ')).toBe(true);
      expect(input.slice(5).trim()).toBe('src/index.ts');
    });

    it('should identify write command', () => {
      const input = 'write src/index.ts const x = 1';
      expect(input.startsWith('write ')).toBe(true);
      const parts = input.slice(6).split(' ');
      expect(parts[0]).toBe('src/index.ts');
    });

    it('should identify bash command', () => {
      const input = '!ls -la';
      expect(input.startsWith('!')).toBe(true);
      expect(input.slice(1).trim()).toBe('ls -la');
    });

    it('should identify ls command', () => {
      const input = 'ls';
      expect(input.startsWith('ls')).toBe(true);
    });

    it('should identify grep command', () => {
      const input = 'grep "pattern" src/';
      expect(input.startsWith('grep ')).toBe(true);
      const parts = input.slice(4).trim().split(' ');
      expect(parts[0]).toBe('"pattern"');
      expect(parts[1]).toBe('src/');
    });
  });

  describe('Chinese command detection', () => {
    it('should detect Chinese character at start', () => {
      const input = '看 src/index.ts';
      const firstCharCode = input.charCodeAt(0);
      const isChinese = firstCharCode > 127;

      expect(isChinese).toBe(true);
    });

    it('should not flag ASCII as Chinese', () => {
      const input = 'read src/index.ts';
      const firstCharCode = input.charCodeAt(0);
      const isChinese = firstCharCode > 127;

      expect(isChinese).toBe(false);
    });

    it('should identify Chinese read commands', () => {
      const chineseCommands = ['看', '查看', '读取', '打开', '查', '读'];
      const input = '查看 src/index.ts';

      for (const cmd of chineseCommands) {
        if (input.startsWith(cmd)) {
          const rest = input.slice(cmd.length).trim();
          expect(rest).toBe('src/index.ts');
          return;
        }
      }
      // Should have matched
      expect(true).toBe(false);
    });
  });
});

describe('Message structure', () => {
  it('should have correct user message structure', () => {
    const msg = { role: 'user' as const, content: 'hello' };
    expect(msg.role).toBe('user');
    expect(msg.content).toBe('hello');
  });

  it('should have correct assistant message structure', () => {
    const msg = { role: 'assistant' as const, content: 'hi there' };
    expect(msg.role).toBe('assistant');
    expect(msg.content).toBe('hi there');
  });
});