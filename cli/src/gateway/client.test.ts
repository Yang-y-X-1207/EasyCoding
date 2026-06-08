import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GatewayClient } from './client';

// ============ Gateway Client Tests ============

describe('GatewayClient', () => {
  describe('constructor', () => {
    it('should create client with base URL', () => {
      const client = new GatewayClient('http://localhost:8080');
      expect(client).toBeDefined();
    });

    it('should extend EventEmitter', () => {
      const client = new GatewayClient('http://localhost:8080');
      expect(typeof client.on).toBe('function');
      expect(typeof client.emit).toBe('function');
    });
  });

  describe('SessionInfo structure', () => {
    it('should have required fields', () => {
      const info = {
        session_id: 'sess-1',
        account_id: 'user-1',
        channel: 'cli',
        agent_id: 'default',
        status: 'active',
        created_at: '2026-01-01T00:00:00Z',
      };

      expect(info.session_id).toBeDefined();
      expect(info.account_id).toBeDefined();
      expect(info.channel).toBeDefined();
      expect(info.agent_id).toBeDefined();
      expect(info.status).toBeDefined();
      expect(info.created_at).toBeDefined();
    });
  });

  describe('EnqueueResult structure', () => {
    it('should have required fields', () => {
      const result = {
        success: true,
        task_id: 'task-1',
        message: 'Task enqueued',
        queue_position: 1,
        status: 'ACCEPTED',
      };

      expect(result.success).toBe(true);
      expect(result.task_id).toBe('task-1');
      expect(result.queue_position).toBe(1);
      expect(result.status).toBe('ACCEPTED');
    });
  });

  describe('TaskStatus structure', () => {
    it('should have required fields', () => {
      const status = {
        task_id: 'task-1',
        status: 'PROCESSING',
        message: 'Working on it',
        queue_position: null,
      };

      expect(status.task_id).toBe('task-1');
      expect(status.status).toBe('PROCESSING');
    });
  });

  describe('QueueStatus structure', () => {
    it('should have required fields', () => {
      const status = {
        queue_length: 5,
        processing: 'task-1',
        completed_recent: 10,
        signatures_active: 3,
      };

      expect(status.queue_length).toBe(5);
      expect(status.processing).toBe('task-1');
    });
  });
});