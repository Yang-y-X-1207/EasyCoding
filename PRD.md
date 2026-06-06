# Coding-CLI 产品 PRD

## 1. 产品概述

### 1.1 产品定位

**Coding-CLI** 是一个 AI 编程助手 CLI 工具，通过聊天平台（Slack/Telegram/Discord）接收开发者指令，调度本地 Agent 执行编码任务，返回结果到聊天平台。

**Agent 专长**：这个 Agent 专精于 DDD（领域驱动设计）辅助编码，能够帮助开发者：
- 理解和实现 DDD 架构模式（Entity、Value Object、Aggregate、Repository、Domain Service 等）
- 按照 DDD 分层架构（api/app/domain/infrastructure/trigger）组织代码
- 辅助构建 DDD 项目结构（多模块、上下文边界、限界上下文）

### 1.2 目标用户

| 用户画像 | 使用场景 |
|----------|----------|
| 开发者 | 希望通过聊天界面操控代码助手，边写代码边对话 |
| 团队 | 多人协作，消息汇总到统一平台，共享 Agent 能力 |
| 自动化场景 | 定时任务触发、CI/CD 集成、Webhook 回调 |

### 1.3 核心价值

- **统一入口**：多聊天平台通过单一 Gateway 接入
- **隔离 Agent**：每个 channel/account 分配独立 Agent 上下文
- **本地优先**：优先本地执行，减少云端依赖
- **持久记忆**：Claude Code 风格的 Memory 存储

---

## 2. 功能规格

### 2.1 核心功能清单

#### 2.1.1 Gateway（网关层）

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 统一入口 | 单一控制平面，管理所有 inbound/outbound 流量 | P0 |
| Session 管理 | 会话生命周期（创建/更新/销毁） | P0 |
| Event 分发 | 消息事件、工具执行事件的分发 | P1 |
| 请求-响应关联 | UUID + CompletableFuture 模式匹配响应 | P0 |

#### 2.1.2 Multi-Channel（多渠道接入）

| 渠道 | 协议 | 优先级 |
|------|------|--------|
| Slack | Socket Mode / Webhook | P1 |
| Telegram | Long Polling Bot API | P1 |
| Discord | Bot Gateway | P2 |
| HTTP Webhook | HTTP Server | P0 |

#### 2.1.3 Multi-Agent（多 Agent 路由）

| 功能 | 描述 | 优先级 |
|------|------|--------|
| Agent 注册 | 配置驱动的 Agent 装配 | P0 |
| 路由策略 | 根据 channel/account 路由到对应 Agent | P0 |
| Workspace 隔离 | 每个 Agent 独立的上下文 | P1 |
| 配置管理 | YAML 配置多个 Agent 和 Workflow | P1 |

#### 2.1.4 Coding Agent（编码 Agent）

| 能力 | 描述 | 优先级 |
|------|------|--------|
| 代码生成 | 根据 prompt 生成代码片段/文件 | P0 |
| 代码修改 | 理解 diff/patch 应用修改 | P1 |
| 项目分析 | 分析项目结构、依赖、关键文件 | P1 |
| 任务执行 | 调用工具（文件操作、git、shell） | P0 |
| 状态反馈 | 进度、结果返回给用户 | P0 |

#### 2.1.5 Memory 系统

| 功能 | 描述 | 优先级 |
|------|------|--------|
| Session 记忆 | 当前会话上下文存储 | P0 |
| 长期记忆 | CLAUDE.md 持久化项目知识 | P1 |
| 项目上下文 | 按项目隔离的记忆空间 | P2 |

#### 2.1.6 CLI 命令

| 命令 | 描述 | 优先级 |
|------|------|--------|
| `coding-cli chat` | 启动交互式聊天 | P0 |
| `coding-cli init` | 初始化项目配置 | P0 |
| `coding-cli config` | 管理 Agent 配置 | P1 |
| `coding-cli status` | 查看连接状态 | P1 |

---

### 2.2 用户交互流程

#### 2.2.1 消息流转路径

```
[Slack/Telegram/Discord/HTTP]
         ↓
    Channel Adapter
         ↓
    Gateway (Session 管理 + Event 分发)
         ↓
    Agent Router (根据 channel/account 路由)
         ↓
    Coding Agent (执行推理)
         ↓
    Tool Executor (文件/git/shell)
         ↓
    Response (通过原渠道返回)
```

#### 2.2.2 Session 生命周期

```
1. 用户首次发消息 → 创建 Session → 分配 Agent
2. 后续消息 → 查找 Session → 追加历史 → 执行推理 → 更新 Session
3. 超时/手动结束 → 持久化 Memory → 销毁 Session
```

---

### 2.3 数据模型

#### 2.3.1 CodingCommand（命令）

| 字段 | 类型 | 描述 |
|------|------|------|
| id | string (UUID) | 唯一标识 |
| action | string | chat / analyze / code / generate |
| channel | string | slack / telegram / discord / http |
| account_id | string | 账户标识 |
| session_id | string | 会话 ID（可空） |
| params | dict | 参数集合 |
| metadata | dict | 元数据（threadId, channelId 等） |
| timestamp | datetime | 时间戳 |

#### 2.3.2 CodingResponse（响应）

| 字段 | 类型 | 描述 |
|------|------|------|
| id | string | 关联的请求 ID |
| status | string | success / error / processing |
| message | string | 状态描述 |
| data | any | 响应数据（代码片段/文件路径等） |
| timestamp | datetime | 时间戳 |

#### 2.3.3 CodingSession（会话）

| 字段 | 类型 | 描述 |
|------|------|------|
| session_id | string | 会话 ID |
| account_id | string | 账户 ID |
| channel | string | 渠道类型 |
| agent_id | string | 分配的 Agent ID |
| messages | list | 消息历史 |
| context | dict | 上下文（当前项目、最后任务等） |
| status | string | active / completed / timeout |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

#### 2.3.4 Memory 文件结构

```
memory/
├── sessions/
│   ├── {session-id}.json     # Session 完整数据
│   └── {session-id}.md       # 对话摘要（可读）
├── projects/
│   └── {project-hash}/
│       └── context.md        # 项目级上下文
└── agents/
    └── {agent-id}/
        └── config.yaml       # Agent 配置
```

---

### 2.4 接口规格

#### 2.4.1 HTTP API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/chat` | 发送消息，获取响应 |
| POST | `/api/v1/chat/stream` | 流式响应（SSE） |
| GET | `/api/v1/session/{session_id}` | 获取 Session 信息 |
| DELETE | `/api/v1/session/{session_id}` | 销毁 Session |
| GET | `/api/v1/agent/configs` | 获取所有 Agent 配置 |
| POST | `/api/v1/agent/configs` | 注册新 Agent |
| GET | `/health` | 健康检查 |

#### 2.4.2 请求/响应示例

**POST /api/v1/chat**

Request:
```json
{
  "action": "chat",
  "channel": "http",
  "account_id": "user_123",
  "session_id": "sess_abc123",
  "params": {
    "message": "帮我生成一个 FastAPI 的 hello world 示例"
  },
  "metadata": {
    "client": "cli"
  }
}
```

Response:
```json
{
  "id": "req_xyz789",
  "status": "success",
  "message": "已完成",
  "data": {
    "reply": "这是一个 FastAPI hello world 示例...",
    "files": ["/tmp/hello.py"]
  },
  "timestamp": "2026-06-05T10:00:00Z"
}
```

---

### 2.5 配置规格

#### 2.5.1 Agent 配置 (YAML)

```yaml
agents:
  - id: "default"
    name: "默认助手"
    type: "general"  # general / coder / reviewer / analyzer
    model:
      provider: "anthropic"
      model: "claude-sonnet-4-5"
      api_key: "${ANTHROPIC_API_KEY}"
    tools:
      - "file_read"
      - "file_write"
      - "bash"
      - "git"
    allowed_channels:
      - "slack"
      - "telegram"
      - "http"
    memory:
      max_tokens: 128000
      preserve_recent: 10

  - id: "coder"
    name: "代码助手"
    type: "coder"
    model:
      provider: "openai"
      model: "gpt-4o"
    tools:
      - "file_read"
      - "file_write"
      - "bash"
      - "git"
      - "grep"
      - "glob"
    allowed_channels:
      - "slack"
```

#### 2.5.2 Channel 配置 (YAML)

```yaml
channels:
  slack:
    enabled: true
    socket_mode:
      app_token: "${SLACK_APP_TOKEN}"
      bot_token: "${SLACK_BOT_TOKEN}"
    webhook:
      url: "${SLACK_WEBHOOK_URL}"

  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    long_polling:
      timeout: 60

  discord:
    enabled: false
    bot_token: "${DISCORD_BOT_TOKEN}"
    gateway:
      intents: 513  # MESSAGE_CONTENT + GUILD_MESSAGES

  http:
    enabled: true
    port: 8080
    cors: true
```

---

## 3. 技术架构

### 3.1 技术栈

| 层级 | 技术 | 职责 |
|------|------|------|
| CLI | TypeScript + Node.js | 命令行入口、渠道适配、Memory 管理 |
| Backend | Python + FastAPI | 业务逻辑、Agent 调度、LLM 集成 |
| Storage | JSON Files (memory/) | Session 记忆存储 |
| Long-term | CLAUDE.md | 项目上下文、知识沉淀 |

### 3.2 项目结构

```
coding-cli/
├── cli/                          # TypeScript CLI
│   ├── src/
│   │   ├── commands/             # CLI 命令实现
│   │   ├── adapters/            # 渠道适配器
│   │   │   ├── slack.ts
│   │   │   ├── telegram.ts
│   │   │   ├── discord.ts
│   │   │   └── http.ts
│   │   ├── gateway/              # 网关客户端
│   │   ├── memory/               # Memory 文件管理
│   │   ├── types/                # TypeScript 类型
│   │   └── index.ts              # CLI 入口
│   └── package.json
│
├── backend/                      # Python Backend
│   ├── api/                      # HTTP 入口、DTO
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   ├── session.py
│   │   │   └── agent.py
│   │   └── dto/
│   ├── domain/                   # 领域模型、端口接口
│   │   ├── models/               # 实体、值对象
│   │   ├── ports/                # 端口接口
│   │   └── services/             # 领域服务
│   ├── infrastructure/           # 端口实现
│   │   ├── adapters/             # 适配器实现
│   │   └── storage/              # 存储实现
│   ├── trigger/                  # 触发器
│   └── services/                 # Agent 服务
│
├── memory/                       # Memory 存储
│   ├── sessions/
│   ├── projects/
│   └── agents/
│
├── CLAUDE.md                     # 长期记忆
└── config.yaml                   # 全局配置
```

### 3.3 核心设计模式

#### 六边形架构（端口与适配器）

```
Domain Layer (核心业务)
    ↑↓  (端口接口)
Infrastructure Layer (技术实现)
    ↑↓  (适配器)
Trigger Layer (外部触发)
```

#### 请求-响应关联

```
Request → pendingRequests[id] = Future
                    ↓
Response → id 匹配 → future.complete()
```

---

## 4. 验收标准

### 4.1 功能验收

| 功能 | 验收条件 |
|------|----------|
| HTTP API | POST /api/v1/chat 返回有效响应 |
| Session 管理 | 同一 session_id 消息上下文保持 |
| Agent 路由 | 不同 channel/account 路由到不同 Agent |
| Memory 存储 | 重启后 session 历史可恢复 |
| 多渠道 | Slack/Telegram 消息收发正常 |

### 4.2 非功能验收

| 指标 | 目标 |
|------|------|
| 响应时间 | < 5s（不含 LLM 推理时间） |
| 启动时间 | < 3s |
| 内存占用 | < 200MB |
| 并发支持 | 100+ 并发连接 |

---

## 5. 实现计划

按依赖关系排序，从核心功能到扩展功能：

### Phase 1: 最小可用系统（1周）
目标：CLI 能对话，Backend 返回响应

- [ ] 创建项目骨架（Python FastAPI + TypeScript CLI）
- [ ] 实现简单 HTTP API（`/api/v1/chat` 返回固定响应）
- [ ] 实现 CLI 基础命令（`chat` 交互式对话）
- [ ] CLI Gateway 客户端调用 Backend
- [ ] 端到端：CLI 发送消息 → Backend 响应 → CLI 显示

### Phase 2: 基础 Memory 存储（1周）
目标：对话历史记忆

- [ ] Session 模型（session_id, messages, account_id）
- [ ] JSON 文件存储（`memory/sessions/{id}.json`）
- [ ] HTTP API 读取/写入 Session
- [ ] CLI 展示对话历史
- [ ] 测试：重启后对话上下文保持

### Phase 3: 单 Agent 聊天 + Evaluator（1-2周）
目标：真正的 AI 对话 + 需求评估

- [ ] 集成 LiteLLM（单模型支持）
- [ ] ChatService 对话逻辑
- [ ] Evaluator Agent（需求完整性评估）
- [ ] 澄清对话机制（用户输入不明确时提问）
- [ ] CLI 流式响应显示（SSE）
- [ ] 测试：AI 对话正常 + 需求澄清有效

### Phase 4: 任务队列 + 去重（1-2周）
目标：多人请求不冲突，相同任务去重

- [ ] 实现 TaskQueue 数据结构
- [ ] 实现任务签名去重（hash 去重）
- [ ] Queue Agent 单例
- [ ] Writer Agent 文件锁
- [ ] Reader Agent 池（多实例并发读）
- [ ] 任务状态通知（ACCEPTED/DUPLICATED/PROCESSING）
- [ ] 测试：重复任务被正确拒绝

### Phase 5: Multi-Channel（2周）
目标：接入 Slack/Telegram/Discord

- [ ] Channel Adapter 接口定义
- [ ] ChannelDispatcher 统一分发
- [ ] SlackAdapter（Socket Mode）
- [ ] TelegramAdapter（Long Polling）
- [ ] DiscordAdapter（Gateway）
- [ ] 测试：各渠道消息收发

### Phase 6: Workspace 隔离（1周）
目标：多群聊多项目隔离

- [ ] Workspace 数据结构
- [ ] 按 channel_id 创建/路由 Workspace
- [ ] 每个 Workspace 独立 Agent 系统
- [ ] 项目目录隔离（`/workspace/{id}/`）
- [ ] 测试：不同群聊独立运作

### Phase 7: Git Agent（1周）
目标：代码修改自动提交

- [ ] Git 操作封装（git add/commit/push）
- [ ] changelog.md 维护
- [ ] 分支创建（task/{name}-{date}）
- [ ] Commit Message 规范生成
- [ ] 测试：代码修改自动提交

### Phase 8: 长期记忆 + 审核（1周）
目标：持久化知识 + 代码审核

- [ ] CLAUDE.md 读写
- [ ] 项目上下文注入
- [ ] PR/MR 创建（GitHub/GitLab API）
- [ ] 审核通知（Slack/Email）
- [ ] 测试：代码审核流程完整

---

## 总工期：9-10 周（约 2.5 个月）

| Phase | 内容 | 周期 | 依赖 | 难度 |
|-------|------|------|------|------|
| Phase 1 | 最小可用系统 | 1周 | 无 | ★ |
| Phase 2 | 基础 Memory | 1周 | Phase 1 | ★ |
| Phase 3 | 单 Agent + Evaluator | 1-2周 | Phase 2 | ★★ |
| Phase 4 | 任务队列 + 去重 | 1-2周 | Phase 3 | ★★★ |
| Phase 5 | Multi-Channel | 2周 | Phase 1 | ★★★ |
| Phase 6 | Workspace 隔离 | 1周 | Phase 4 | ★★ |
| Phase 7 | Git Agent | 1周 | Phase 4 | ★★ |
| Phase 8 | 长期记忆 + 审核 | 1周 | Phase 6+7 | ★★ |

---
## 6. 竞品对比

| 维度 | OpenClaw | Coding-CLI |
|------|----------|-------------|
| 目标平台 | 通用 Agent + 设备控制 | 编程助手 |
| 交互形态 | 语音 + 文字 + 画布 | 纯文字（聊天平台） |
| 工具集 | 通用 | 代码专用（文件/git/shell） |
| 架构 | Java DDD | Python FastAPI + TypeScript CLI |
| 记忆系统 | 无 | Claude Code 风格 Memory |
| 多渠道 | 20+ 消息平台 | Slack/Telegram/Discord/HTTP |

---

## 7. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| LLM API 不稳定 | 响应延迟/失败 | 添加超时重试、降级策略 |
| 多渠道消息并发 | 性能瓶颈 | 异步处理、消息队列 |
| Memory 文件膨胀 | 存储不足 | 定期压缩、归档策略 |
| 安全风险 | API Key 泄露 | 环境变量、密钥轮换 |
---



#### 2.1.10 Evaluator Agent（需求评估 Agent，新增）

### 背景
用户提出的需求往往不够明确或完整，直接执行可能导致错误结果。Evaluator Agent 负责在任务进入队列前评估需求质量，识别模糊点，并通过提问获取完整信息。

### Evaluator Agent 职责

| 职责 | 描述 |
|------|------|
| **需求完整性评估** | 检查任务描述是否包含：目标、范围、约束条件、验收标准 |
| **模糊点识别** | 识别未定义的技术栈、文件路径、依赖关系、预期行为 |
| **澄清提问** | 向用户提问获取缺失信息（不能臆造，只能基于已知提问） |
| **任务签名预生成** | 在澄清完成后生成准确的任务签名，提高去重准确率 |

### 评估维度

需求完整性检查清单：
- 目标明确：用户想实现什么功能/修复什么问题？
- 范围清晰：涉及哪些文件/模块？
- 技术栈确定：使用什么语言/框架/版本？
- 验收标准：如何判断任务完成？
- 约束条件：有性能要求、安全要求、兼容性要求？
- 优先级：用户期望的完成时间/紧急程度？

### 澄清对话示例

**用户输入**（模糊）：帮我改一下那个接口

**Evaluator Agent 响应**：
- 需求评估：信息不足，需要澄清以下问题：
  1. 目标接口：您说的是哪个接口？是 src/api/users.py 的用户查询接口吗？
  2. 修改内容：具体需要修改什么？增加字段/修改逻辑/修复bug？
  3. 关联影响：修改是否需要同步更新 Model/Schema/测试/文档？

请回复上述问题的答案，我将为您完善任务描述。

### 工作流程

用户消息 -> Reader Agent 接收 -> Evaluator Agent 评估
  -> 信息完整？否 -> 澄清提问 -> 用户回复 -> 重新评估
  -> 是 -> Queue Agent 接收任务 -> 去重检查 -> 进入队列

### 配置项

```yaml
evaluator:
  pool_size: 2
  max_clarification_rounds: 3
  clarification_timeout_minutes: 5
```

### 与其他 Agent 的交互

用户 <- Reader Agent（收集原始需求）
        |
        v
  Evaluator Agent（评估 + 澄清）
        |
        v
  Queue Agent（接收完整任务）
        |
        v
  Writer Agent（执行任务）
        |
        v
  Evaluator Agent（验证结果）
        |
        v
  通知用户

### 任务状态新增

PENDING_EVALUATION（信息不足，等待澄清）
        |
        v
EVALUATION_COMPLETED（澄清完成，进入队列）
        |
        v
PENDING -> PROCESSING -> COMPLETED

## 2.1.7 任务队列与多 Agent 协作（新增）

### 背景
一个聊天群（如 Slack Channel）中多个用户同时发起请求，如果每个请求都启动独立 Agent 写代码，会导致：
1. 代码冲突（多人同时修改同一文件）
2. 任务重复（同一需求被多次执行）
3. 系统堵塞（写操作串行但无协调）

### 解决方案：单一写 Agent + 任务队列

#### Agent 角色分工

| Agent 角色 | 数量 | 职责 | 并发模型 |
|------------|------|------|----------|
| **Queue Agent** | 1 | 维护任务队列、识别重复任务、任务分发 | 单例，全局唯一 |
| **Writer Agent** | 1 | 独占修改代码文件（文件锁保护） | 单例写，串行执行 |
| **Reader Agent** | N | 读取项目、与用户对话、查询状态 | 多实例，并发读 |
| **Evaluator Agent** | 2 | 需求完整性评估、模糊点识别、澄清提问 | 单池，与 Reader 协作 |
| **Analyzer Agent** | N | 项目分析、代码审查、依赖分析 | 多实例，并发 |

#### 任务队列设计

```
用户消息群聊
    [用户A: 帮我改个bug]  [用户B: 生成接口]  [用户C: 帮我改同一个bug]
                                ↓
                    Channel Adapter (路由)
                                ↓
                    Reader Agent 池 (与用户交互，收集任务)
                                ↓
                    任务描述 + 任务签名 (hash)
                                ↓
                    Queue Agent (单例，维护队列)
                    - 写入任务队列
                    - 识别重复任务
                    - 任务去重 (签名匹配)
                                ↓
                    Writer Agent (单例，文件锁)
                    - 从队列取任务
                    - 串行执行写操作
                    - 执行完通知用户
```

#### 去重机制

Queue Agent 维护**任务签名池**：

```python
# 任务签名 = hash(项目路径 + 文件路径 + 操作类型 + 关键参数)
# 例：hash("/project/src/api.py" + "modify" + "add_user_endpoint")

class TaskSignature:
    signature: str      # hash 值
    user_id: str       # 提交者
    submitted_at: datetime
    status: str         # pending / processing / completed / cancelled
```

**去重规则**：
- 相同签名在 `dedup_window` (默认 5 分钟) 内重复提交 → 拒绝，通知用户
- 任务执行完成后，签名保留 `completed_ttl` (默认 30 分钟) 后自动清除
- 用户可手动取消自己提交的任务

#### 文件锁机制

Writer Agent 使用**悲观锁**保护写操作：

```python
# 写操作前申请锁
with FileLock(file_path, timeout=30):
    # 读取文件 -> 修改 -> 写回文件
# 锁自动释放
```

**锁粒度**：按文件路径加锁，不同文件可并发修改。

#### 任务队列结构

```python
class TaskQueue:
    queue: list[Task]          # 等待执行的任务
    processing: Task | None     # 当前执行的任务
    completed: list[Task]      # 已完成任务 (保留最近N条)

    def enqueue(self, task: Task) -> EnqueueResult:
        # 1. 生成任务签名
        # 2. 检查重复（查 completed_ttl 内的签名）
        # 3. 如重复，返回 DUPLICATED
        # 4. 如不重复，加入 queue，返回 ACCEPTED

    def dequeue(self) -> Task | None:
        # 取下一个任务（FIFO）

    def mark_completed(self, task_id: str):
        # 标记完成，添加到 completed
        # 清理过期 completed 条目
```

#### 任务状态流转

```
PENDING -> PROCESSING -> COMPLETED
    ↓           ↓
 CANCELLED   FAILED
    ↓           ↓
 (用户取消)   (重试或放弃)
```

#### 通知机制

任务状态变更时，通过原渠道通知用户：

| 状态 | 通知内容 |
|------|----------|
| ACCEPTED | "✅ 任务已加入队列，你是第 X 位" |
| DUPLICATED | "⚠️ 检测到重复任务，已在队列中" |
| PROCESSING | "🔧 开始执行任务..." |
| COMPLETED | "✅ 任务完成，修改了 X 个文件" |
| FAILED | "❌ 任务失败: {reason}，是否重试？" |
| CANCELLED | "🚫 任务已取消" |

#### 配置项

```yaml
queue:
  dedup_window_minutes: 5      # 去重时间窗口
  completed_ttl_minutes: 30     # 完成记录保留时间
  max_queue_size: 100           # 最大队列长度
  max_retries: 3               # 失败重试次数

writer:
  file_lock_timeout_seconds: 30
  lock_dir: ".coding-cli/locks"  # 锁文件目录

reader:
  pool_size: 5                 # Reader Agent 池大小
  timeout_seconds: 60          # 对话超时时间
```

---

## 2.1.8 多群聊-多项目隔离（新增）

### 背景
多个聊天群（如不同项目的 Slack Channel）同时使用系统，每个群聊应拥有独立的项目上下文和 Agent 系统，避免不同项目之间相互干扰。

### 解决方案：Workspace 隔离

```
群聊A (项目Alpha)          群聊B (项目Beta)           群聊C (项目Gamma)
      ↓                        ↓                        ↓
独立的多Agent系统            独立的多Agent系统          独立的多Agent系统
(Queue+Writer+Readers)     (Queue+Writer+Readers)     (Queue+Writer+Readers)
      ↓                        ↓                        ↓
  /workspace/alpha/           /workspace/beta/          /workspace/gamma/
```

### Workspace 创建流程

```
1. 群聊首次发消息（项目无关的对话除外）
2. Gateway 识别 channel_id
3. 检查 workspace 是否已存在
   - 已存在 → 路由到已有 workspace
   - 不存在 → 创建新 workspace：
     a. 分配 workspace_id
     b. 初始化 Agent 系统（Queue/Writer/Readers/Git Agent）
     c. 创建 workspace 目录结构
     d. 初始化 git 仓库（如果是非 git 项目）
4. 后续消息路由到对应 workspace
```

### Workspace 数据结构

```python
class Workspace:
    workspace_id: str          # 唯一标识 (channel_id 或自定义)
    channel_id: str            # 关联的聊天渠道 ID
    channel_type: str           # slack / telegram / discord
    project_path: str           # 项目根目录
    project_name: str           # 项目名称
    agent_system: AgentSystem  # 该 workspace 的 Agent 系统
    created_at: datetime
    updated_at: datetime
    status: str                 # active / paused / archived

class AgentSystem:
    queue_agent: QueueAgent     # 单例
    writer_agent: WriterAgent   # 单例
    reader_agents: list[ReaderAgent]  # 多实例
    analyzer_agents: list[AnalyzerAgent]  # 多实例
    git_agent: GitAgent         # 单例（新增）
```

### Workspace 目录结构

```
/workspace/
└── {workspace_id}/
    ├── .coding-cli/           # CLI 配置
    │   ├── config.yaml        # workspace 配置
    │   ├── memory/            # Memory 文件
    │   │   ├── sessions/
    │   │   └── context.md     # 上下文
    │   └── locks/             # 文件锁目录
    ├── project/               # 项目代码
    │   ├── src/
    │   ├── tests/
    │   └── ...
    └── changelog.md           # 变更记录（Git Agent 维护）
```

### Agent 系统生命周期

```
创建 → 启动 → 运行 → 暂停/恢复 → 归档
         ↓
    首次消息时创建
         ↓
    群聊静默超时（默认7天）→ 暂停 Agent 系统
         ↓
    归档前保留 Memory 和 changelog
```

---

## 2.1.9 Git 维护 Agent（新增）

### 背景
Writer Agent 执行代码修改后，需要：
1. 详细记录每次修改的内容
2. 自动提交 git（格式化的 commit message）
3. 通知修改人员进行代码审核

### Git Agent 职责

| 职责 | 描述 |
|------|------|
| 变更记录 | 将每次修改详细记录到 changelog.md |
| 自动提交 | 生成规范 commit message 并提交 |
| 分支管理 | 为每个任务创建独立分支，审核后合并 |
| 审核通知 | 通知相关人员审核 PR/MR |
| 冲突处理 | 检测并解决合并冲突 |

### 变更记录格式 (changelog.md)

```markdown
# 项目 Alpha 变更记录

## 2026-06-05 10:30:45
### 任务: 添加用户注册接口
### 提交者: Writer Agent
### 关联任务ID: task_abc123

#### 修改文件
| 文件 | 操作 | 行号 | 描述 |
|------|------|------|------|
| src/api/users.py | MODIFY | 45-67 | 新增 create_user 函数 |
| src/models/user.py | MODIFY | 12-15 | 新增 UserProfile 模型字段 |
| tests/test_users.py | ADD | 100-150 | 新增 create_user 测试用例 |

#### 变更详情
diff
# src/api/users.py
-def create_user(name, email):
+def create_user(name, email, password=None):
+    """创建用户接口"""
+    if not email:
+        raise ValueError("Email is required")

#### Commit
- Branch: task/user-registry-20260605
- Message: feat(users): add create_user endpoint with validation
- Status: PENDING_REVIEW

---

## 2026-06-05 09:15:00
### 任务: 修复登录bug
...
```

### Git 工作流

```
Writer Agent 执行修改
        ↓
Git Agent 捕获变更
        ↓
记录到 changelog.md（详细 diff + 变更描述）
        ↓
创建任务分支 (task/{任务名}-{日期})
        ↓
git add + git commit（规范 message）
        ↓
git push origin task/xxx
        ↓
创建 PR/MR（关联 changelog 条目）
        ↓
通知审核人员（@mention 或邮件）
        ↓
等待审核结果
        ↓
通过 → 合并到主分支
失败 → 打回 Writer Agent 重新修改
```

### Commit Message 规范

```
<type>(<scope>): <subject>

<body>

<footer>

# Type: feat | fix | docs | style | refactor | test | chore
# Scope: affected module (e.g., users, auth, api)
# Subject: 简短描述（不超过50字）
# Body: 详细说明
# Footer: 关联的任务ID、审核人
```

### 分支策略

```
main (保护分支)
├── develop (开发分支)
│   ├── task/user-registry-20260605
│   ├── task/fix-login-bug-20260604
│   └── ...
```

### 审核通知

```yaml
notification:
  slack:
    channel: "#code-review"
    mention_users: true
  email:
    enabled: true
    smtp_server: "${SMTP_SERVER}"
    from: "coding-cli@example.com"
    to_patterns:
      - "*.example.com"
  pr_template: |
    ## 代码审核
    ### 任务描述
    {task_description}
    ### 变更文件
    {changed_files}
    ### changelog
    {changelog_entry}
    ### Diff
    {git_diff}
```

### Git Agent 与其他 Agent 的交互

```
Reader Agent ←→ 用户对话，收集需求
     ↓
Queue Agent ←→ 任务去重，分发任务
     ↓
Writer Agent ←→ 执行代码修改
     ↓
Git Agent ←──────────────────────────────────┐
     ↓                                      ↓
1. 记录 changelog.md              2. 提交 git
     ↓                                      ↓
3. 创建 PR                        4. 通知审核
     ↓                                      ↓
5. 等待审核结果 ←────────────────────────────┘
     ↓
6. 合并/打回
```

### 配置项

```yaml
git:
  workspace:
    base_path: "/workspace"
    auto_init: true
    default_branch: "main"
  commit:
    message_template: |
      {type}({scope}): {subject}

      {body}

      Task: {task_id}
    sign_off: true
  branch:
    prefix: "task"
    naming: "{prefix}/{task_name}-{date}"
  notification:
    enabled: true
    channels:
      - slack
      - email
    mention_on_create: true
  pr:
    auto_create: true
    auto_merge: false
    merge_method: "squash"
```

### 审核流程状态

```
PENDING_REVIEW → CHANGES_REQUESTED → APPROVED → MERGED
                    ↓
              REJECTED → 返回 Writer Agent 重新修改
```
