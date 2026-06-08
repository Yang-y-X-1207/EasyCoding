"use strict";
/**
 * Gateway Client
 * Phase 4: Task queue support
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.GatewayClient = void 0;
const axios_1 = __importDefault(require("axios"));
const events_1 = require("events");
class GatewayClient extends events_1.EventEmitter {
    constructor(baseURL) {
        super();
        this.client = axios_1.default.create({
            baseURL,
            timeout: 60000,
            headers: {
                "Content-Type": "application/json",
            },
        });
    }
    // ============ Chat Methods ============
    async sendChat(request) {
        const response = await this.client.post("/api/v1/chat", request);
        return response.data;
    }
    async sendChatStream(request, onEvent) {
        const response = await this.client.post("/api/v1/chat/stream", request, {
            responseType: "stream",
        });
        let buffer = "";
        response.data.on("data", (chunk) => {
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
                            const streamEvent = { event: eventName, data };
                            onEvent(streamEvent);
                            this.emit(eventName, data);
                        }
                        catch (e) {
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
    async createSession(accountId, channel = "cli") {
        const response = await this.client.post("/api/v1/sessions", {
            account_id: accountId,
            channel,
        });
        return response.data;
    }
    async getSession(sessionId) {
        const response = await this.client.get(`/api/v1/sessions/${sessionId}`);
        return response.data;
    }
    async listSessions(accountId) {
        const params = accountId ? { account_id: accountId } : {};
        const response = await this.client.get("/api/v1/sessions", { params });
        return response.data.sessions;
    }
    async deleteSession(sessionId) {
        await this.client.delete(`/api/v1/sessions/${sessionId}`);
    }
    // ============ Task Queue Methods ============
    async enqueueTask(params) {
        const response = await this.client.post("/api/v1/tasks/enqueue", params);
        return response.data;
    }
    async getTaskStatus(taskId) {
        const response = await this.client.get(`/api/v1/tasks/${taskId}/status`);
        return response.data;
    }
    async getTaskQueueStatus() {
        const response = await this.client.get("/api/v1/tasks/queue/status");
        return response.data;
    }
    async cancelTask(taskId, accountId) {
        await this.client.post("/api/v1/tasks/cancel", {
            task_id: taskId,
            account_id: accountId,
        });
    }
    // ============ Health Check ============
    async healthCheck() {
        const response = await this.client.get("/health");
        return response.data;
    }
}
exports.GatewayClient = GatewayClient;
//# sourceMappingURL=client.js.map