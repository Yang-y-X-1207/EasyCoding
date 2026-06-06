/**
 * Gateway Client
 * Phase 4: Task queue support
 */

import axios, { AxiosInstance, AxiosResponse } from "axios";
import { EventEmitter } from "events";
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

export interface ChatStreamEvent {
  event: string;
  data: any;
}

export interface EnqueueResult {
  success: boolean;
  task_id: string | null;
  message: string;
  queue_position: number | null;
  status: string;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  message: string;
  queue_position: number | null;
}

export interface QueueStatus {
  queue_length: number;
  processing: string | null;
  completed_recent: number;
  signatures_active: number;
}

export class GatewayClient extends EventEmitter {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    super();
    this.client = axios.create({
      baseURL,
      timeout: 60000,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  // ============ Chat Methods ============

  async sendChat(request: ChatRequest): Promise<ChatResponse> {
    const response: AxiosResponse<ChatResponse> = await this.client.post<ChatResponse>(
      "/api/v1/chat",
      request
    );
    return response.data;
  }

  async sendChatStream(
    request: ChatRequest,
    onEvent: (event: ChatStreamEvent) => void
  ): Promise<void> {
    const response = await this.client.post("/api/v1/chat/stream", request, {
      responseType: "stream",
    });

    let buffer = "";

    response.data.on("data", (chunk: Buffer) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("event:") && line.includes(":")) {
          const [eventPart, dataPart] = line.split(":", 2);
          const eventName = eventPart.replace("event:", "").trim();
          const dataStr = dataPart.trim();

          if (dataStr.startsWith("data:")) {
            const jsonStr = dataStr.replace("data:", "").trim();
            try {
              const data = JSON.parse(jsonStr);
              const streamEvent: ChatStreamEvent = { event: eventName, data };
              onEvent(streamEvent);
              this.emit(eventName, data);
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    });

    return new Promise((resolve, reject) => {
      response.data.on("end", resolve);
      response.data.on("error", reject);
    });
  }

  // ============ Session Methods ============

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

  // ============ Task Queue Methods ============

  async enqueueTask(params: {
    session_id: string;
    account_id: string;
    channel?: string;
    agent_id?: string;
    message: string;
    action?: string;
    priority?: number;
  }): Promise<EnqueueResult> {
    const response = await this.client.post<EnqueueResult>(
      "/api/v1/tasks/enqueue",
      params
    );
    return response.data;
  }

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await this.client.get<TaskStatus>(
      `/api/v1/tasks/${taskId}/status`
    );
    return response.data;
  }

  async getTaskQueueStatus(): Promise<QueueStatus> {
    const response = await this.client.get<QueueStatus>("/api/v1/tasks/queue/status");
    return response.data;
  }

  async cancelTask(taskId: string, accountId: string): Promise<void> {
    await this.client.post("/api/v1/tasks/cancel", {
      task_id: taskId,
      account_id: accountId,
    });
  }

  // ============ Health Check ============

  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }
}
