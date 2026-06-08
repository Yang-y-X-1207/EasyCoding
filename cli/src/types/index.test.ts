import { describe, it, expect } from 'vitest';

// ============ Types Tests ============

describe('ChatRequest', () => {
  it('should have correct structure', () => {
    const request = {
      action: 'chat',
      channel: 'cli',
      account_id: 'user-1',
      session_id: 'sess-1',
      params: { message: 'Hello' },
      metadata: { client: 'coding-cli' },
    };

    expect(request.action).toBe('chat');
    expect(request.channel).toBe('cli');
    expect(request.account_id).toBe('user-1');
    expect(request.params.message).toBe('Hello');
  });

  it('should allow optional session_id', () => {
    const request: {
      action: string;
      channel: string;
      account_id: string;
      session_id?: string;
      params: { message: string };
      metadata: Record<string, string>;
    } = {
      action: 'chat',
      channel: 'cli',
      account_id: 'user-1',
      params: { message: 'Hello' },
      metadata: {},
    };

    expect('session_id' in request).toBe(false);
  });
});

describe('ChatResponse', () => {
  it('should have correct structure', () => {
    const response = {
      id: 'req-1',
      status: 'success',
      message: 'OK',
      data: {
        reply: 'Hello, how can I help?',
        session_id: 'sess-1',
      },
      timestamp: '2026-01-01T00:00:00Z',
    };

    expect(response.id).toBe('req-1');
    expect(response.status).toBe('success');
    expect(response.data.reply).toBeDefined();
    expect(response.data.session_id).toBe('sess-1');
  });

  it('should allow session_id in params for request', () => {
    const request = {
      action: 'chat',
      channel: 'cli',
      account_id: 'user-1',
      session_id: 'sess-1',
      params: { message: 'Hello' },
      metadata: {},
    };

    expect(request.session_id).toBe('sess-1');
  });
});

describe('Config', () => {
  it('should have correct structure', () => {
    const config = {
      backendUrl: 'http://localhost:8080',
      accountId: 'user-1',
    };

    expect(config.backendUrl).toBe('http://localhost:8080');
    expect(config.accountId).toBe('user-1');
  });
});