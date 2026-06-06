/**
 * Gateway Client
 * Phase 2: Session-aware HTTP client to call Backend API
 */

import axios, { AxiosInstance } from "axios";
import { ChatRequest, ChatResponse } from "../types";

export interface SessionInfo {
  session_id: string;
  account_id: string;
  channel: string;
  agent_id: string;
  status: string;
  created_at: string;
}

export interface SessionListItem {
  session_id: string;
  account_id: string;
  channel: string;
  agent_id: string;
  message_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export class GatewayClient {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  async sendChat(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>("/api/v1/chat", request);
    return response.data;
  }

  async createSession(accountId: string, channel: string = "cli"): Promise<SessionInfo> {
    const response = await this.client.post<SessionInfo>("/api/v1/sessions", {
      account_id: accountId,
      channel,
    });
    return response.data;
  }

  async getSession(sessionId: string): Promise<any> {
    const response = await this.client.get(`/api/v1/sessions/${sessionId}`);
    return response.data;
  }

  async listSessions(accountId?: string): Promise<SessionListItem[]> {
    const params = accountId ? { account_id: accountId } : {};
    const response = await this.client.get("/api/v1/sessions", { params });
    return response.data.sessions;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/api/v1/sessions/${sessionId}`);
  }

  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }
}
