/**
 * Gateway Client
 * Phase 4: Task queue support
 */
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
export declare class GatewayClient extends EventEmitter {
    private client;
    constructor(baseURL: string);
    sendChat(request: ChatRequest): Promise<ChatResponse>;
    sendChatStream(request: ChatRequest, onEvent: (event: ChatStreamEvent) => void): Promise<void>;
    createSession(accountId: string, channel?: string): Promise<SessionInfo>;
    getSession(sessionId: string): Promise<any>;
    listSessions(accountId?: string): Promise<SessionListItem[]>;
    deleteSession(sessionId: string): Promise<void>;
    enqueueTask(params: {
        session_id: string;
        account_id: string;
        channel?: string;
        agent_id?: string;
        message: string;
        action?: string;
        priority?: number;
    }): Promise<EnqueueResult>;
    getTaskStatus(taskId: string): Promise<TaskStatus>;
    getTaskQueueStatus(): Promise<QueueStatus>;
    cancelTask(taskId: string, accountId: string): Promise<void>;
    healthCheck(): Promise<{
        status: string;
    }>;
}
//# sourceMappingURL=client.d.ts.map