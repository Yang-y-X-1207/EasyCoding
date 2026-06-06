/**
 * CLI Types
 * Phase 1: Basic types for CLI <-> Backend communication
 */

export interface ChatRequest {
  action: string;
  channel: string;
  account_id: string;
  session_id?: string;
  params: {
    message: string;
  };
  metadata: Record<string, string>;
}

export interface ChatResponse {
  id: string;
  status: string;
  message: string;
  data: {
    reply: string;
    session_id: string;
  };
  timestamp: string;
}

export interface Config {
  backendUrl: string;
  accountId: string;
}
