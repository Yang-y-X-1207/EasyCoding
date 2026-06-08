# EasyCoding 用户手册

EasyCoding 是一个 AI 编程助手 CLI 工具，支持直接本地对话和通过聊天平台（Slack/Telegram/Discord）远程控制。

---

## 快速开始

### 1. 安装 CLI

```bash
cd EasyCoding/cli
npm install
npm run build
```

### 2. 配置 API Key

EasyCoding 支持多种 LLM 提供商，选择一种配置：

```bash
# MiniMax (推荐国内用户)
export MINIMAX_API_KEY=sk-cp-xxxxxxxx

# OpenAI
export OPENAI_API_KEY=sk-xxxxx

# Anthropic (Claude)
export ANTHROPIC_API_KEY=sk-ant-xxxxx

# Google Gemini
export GEMINI_API_KEY=xxxxx

# Azure OpenAI
export AZURE_OPENAI_KEY=xxxxx
export AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
```

### 3. 运行

```bash
# 直接模式（无需后端）
cd cli
node dist/index.js direct -p .

# 后端模式（多渠道支持）
cd backend
pip install fastapi uvicorn pydantic python-dotenv aiohttp slack-sdk httpx
PYTHONPATH=./ uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## 新架构 (v0.9+)

### 核心组件

```
backend/
├── agent/                    # Agent 系统
│   ├── providers/            # LLM Provider 工厂
│   │   ├── base.py          # Provider 基类 + LLMResponse
│   │   ├── registry.py      # ProviderSpec 元数据表
│   │   ├── factory.py       # make_provider() 工厂函数
│   │   └── *.py            # Anthropic/OpenAI/Gemini/Azure 实现
│   ├── tools/               # 工具系统
│   │   ├── base.py         # Tool 基类 + ToolContext
│   │   ├── loader.py       # pkgutil 自动发现
│   │   ├── registry.py     # ToolRegistry 工具注册表
│   │   └── *.py            # file_read/file_write/bash/git/glob/grep
│   └── loop.py             # AgentLoop 状态机 + AgentRunner
│
└── bus/                      # MessageBus 消息队列
    └── queue.py             # asyncio.Queue 解耦
```

### Provider 架构

Provider 通过 `ProviderSpec` 元数据表 + 工厂函数实现多供应商支持：

```python
from agent import create_provider_from_env

# 自动检测环境变量创建 Provider
provider = create_provider_from_env()
# 支持: anthropic, openai, minimax, groq, openrouter, azure, gemini, dashscope
```

### Tool 自动发现

工具通过 pkgutil 自动发现 + 注册：

```python
from agent import ToolLoader, ToolRegistry, ToolContext

registry = ToolRegistry()
loader = ToolLoader("agent.tools")
ctx = ToolContext(workspace_id="ws1", project_path="/project")
loader.load(ctx, registry)

# 内置工具: file_read, file_write, bash, git, glob, grep
schemas = registry.get_definitions()  # 获取 LLM 工具 schema
```

### Agent Loop 状态机

```
TurnState: RESTORE -> COMPACT -> COMMAND -> BUILD -> RUN -> SAVE -> RESPOND -> DONE
```

---

## 工作模式

### 模式一：直接 CLI（无需后端）

```bash
node dist/index.js direct -p .
```

特点：
- 无需启动后端服务
- 即装即用
- 支持文件读写、命令执行、代码搜索

### 模式二：后端服务（多渠道）

启动 Python 后端，支持 Slack/Telegram/Discord 接入：

```bash
cd backend
PYTHONPATH=./ uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## CLI 命令

### 交互命令

| 命令 | 说明 |
|------|------|
| `exit` | 退出程序 |
| `clear` | 清屏 |
| `history` | 显示对话历史 |
| `help` | 显示帮助 |

### 文件操作

| 命令 | 示例 | 说明 |
|------|------|------|
| `read <path>` | `read cli/src/index.ts` | 读取文件 |
| `看 <文件>` | `看 cli/src/index.ts` | 读取文件（中文） |
| `write <path> <content>` | `write test.js console.log(1)` | 写入文件 |
| `ls [path]` | `ls` 或 `ls src` | 列目录 |
| `!cmd` | `!ls -la` | 执行 Shell 命令 |
| `grep <pattern>` | `grep function` | 搜索代码 |

---

## 支持的 LLM 提供商

| 提供商 | 环境变量 | 默认模型 |
|--------|----------|-----------|
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-7 |
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| MiniMax | `MINIMAX_API_KEY` | abab5.5-chat |
| Groq | `GROQ_API_KEY` | mixtral-8x7b-32768 |
| OpenRouter | `OPENROUTER_API_KEY` | anthropic/claude-3-haiku |
| Azure | `AZURE_OPENAI_KEY` | gpt-4 |
| Gemini | `GEMINI_API_KEY` | gemini-1.5-flash |
| DashScope | `DASHSCOPE_API_KEY` | qwen-plus |

---

## 配置文件

### .env 例子

```bash
# LLM 配置
ANTHROPIC_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-sonnet-4-7

# 可选: OpenAI 兼容服务
OPENAI_BASE_URL=https://api.openai.com/v1

# Slack 配置
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_APP_TOKEN=xapp-xxxxx

# Telegram 配置
TELEGRAM_BOT_TOKEN=xxxxx

# Discord 配置
DISCORD_BOT_TOKEN=xxxxx
```

---

## 项目结构

```
EasyCoding/
├── cli/                        # TypeScript CLI
│   ├── src/
│   │   ├── agent/              # LLM provider + Agent
│   │   ├── commands/           # CLI 命令
│   │   └── index.ts            # 入口
│   └── dist/                   # 编译输出
│
├── backend/                    # Python 后端
│   ├── agent/                  # Agent 系统 (v0.9+)
│   │   ├── providers/          # LLM Provider 工厂
│   │   ├── tools/              # 工具系统
│   │   └── loop.py             # AgentLoop 状态机
│   ├── bus/                    # MessageBus 消息队列
│   ├── api/routes/             # HTTP 接口
│   ├── services/              # 业务逻辑
│   ├── domain/models/         # 领域模型
│   └── infrastructure/        # 存储和适配器
│
├── memory/                     # Session 记忆存储
└── workspace/                  # 工作区项目目录
```

---

## 后端 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/chat` | 发送消息 |
| POST | `/api/v1/chat/stream` | SSE 流式响应 |
| POST | `/api/v1/sessions` | 创建会话 |
| GET | `/api/v1/sessions/{id}` | 获取会话 |
| POST | `/api/v1/tasks/enqueue` | 添加任务 |
| GET | `/api/v1/tasks/{id}/status` | 任务状态 |
| POST | `/api/v1/workspaces/{id}/git/commit` | Git 提交 |
| POST | `/api/v1/workspaces/{id}/git/pr` | 创建 PR |
| GET | `/api/v1/workspaces/{id}/memory/claude-md` | 获取 CLAUDE.md |

---

## 常见问题

### Q: 直接模式报 "未找到 LLM API 配置"

A: 确保已设置环境变量：

```bash
export MINIMAX_API_KEY=sk-cp-你的密钥
```

### Q: 中文命令"看"不生效

A: 确保第一个字符是中文且后面有空格分隔路径，如 `看 cli/src/index.ts`

### Q: 如何查看 CLI 版本

```bash
node dist/index.js --version
```

---

## License

MIT