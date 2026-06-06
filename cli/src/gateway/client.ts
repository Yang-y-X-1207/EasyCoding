/**
 * Gateway Client
 * Phase 1: Simple HTTP client to call Backend API
 */

import axios, { AxiosInstance } from "axios";
import { ChatRequest, ChatResponse } from "../types";

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

  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }
}
