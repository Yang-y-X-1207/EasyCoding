# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**Phase 9+10 COMPLETED** - P1 and P2 improvements implemented:
- P1: Provider factory, Tool auto-discovery, Agent state machine, MessageBus
- P2: SessionManager with cache/async-writeback, SubagentManager, CommandRouter, Pydantic Config, Structured errors

## Project Overview

**EasyCoding** is an AI coding assistant CLI tool with two operating modes:

1. **Direct CLI Mode** - Claude Code style local chat with MiniMax/OpenAI/Anthropic API
2. **Backend Mode** - Receives instructions via chat platforms, dispatches Agent to execute tasks

## Architecture (v0.9+)

### New Architecture Components

```
backend/
├── agent/                        # Agent 系统
│   ├── providers/                # LLM Provider 工厂
│   │   ├── base.py              # LLMProvider 基类 + LLMResponse (structed errors)
│   │   ├── registry.py          # ProviderSpec 元数据表 (~9 providers)
│   │   ├── factory.py           # make_provider() 工厂函数
│   │   ├── anthropic_provider.py
│   │   ├── openai_compat_provider.py  # OpenAI/MiniMax/Groq/DashScope
│   │   ├── azure_provider.py
│   │   ├── gemini_provider.py
│   │   └── fallback_provider.py   # 主备切换
│   ├── tools/                   # 工具系统
│   │   ├── base.py             # Tool 基类 + ToolContext
│   │   ├── loader.py           # pkgutil 自动发现
│   │   ├── registry.py         # ToolRegistry
│   │   ├── file_read.py
│   │   ├── file_write.py
│   │   ├── bash.py
│   │   ├── git.py
│   │   ├── glob.py
│   │   └── grep.py
│   ├── loop.py                 # AgentLoop + AgentRunner + TurnState
│   └── subagent.py             # SubagentManager (P2)
├── bus/                         # MessageBus (asyncio.Queue)
│   └── queue.py
├── command/                      # Command 系统 (P2)
│   └── router.py               # CommandRouter (/stop, /new, /model, etc.)
└── infrastructure/storage/
    └── session_manager.py     # SessionManager with cache/async-writeback (P2)
```

### Two Operating Modes

```
# Mode 1: Direct CLI (No backend needed)
User -> CLI (direct API call) -> Local file operations

# Mode 2: Backend (Multi-channel)
Slack/Telegram/Discord -> Backend (FastAPI) -> Agent -> File/Git operations
```

### Provider Architecture

Provider 通过两层架构实现：
1. **ProviderSpec 元数据表** (`registry.py`) - 定义 ~9 种 provider 的配置
2. **工厂函数** (`factory.py`) - `make_provider()` 根据配置创建实例

```python
# 自动检测环境变量创建 Provider
from agent import create_provider_from_env
provider = create_provider_from_env()

# 手动指定
from agent import make_provider, ProviderConfig
config = ProviderConfig(provider="anthropic", api_key="...", model="claude-sonnet-4-7")
provider = make_provider(config)
```

### Tool Auto-Discovery

工具通过 pkgutil 自动发现 + entry_points 插件支持：

```python
from agent import ToolLoader, ToolRegistry, ToolContext

registry = ToolRegistry()
loader = ToolLoader("agent.tools")
ctx = ToolContext(workspace_id="ws1", project_path="/project")
loader.load(ctx, registry)

schemas = registry.get_definitions()  # 获取 LLM 工具 schema
```

内置工具: `file_read`, `file_write`, `bash`, `git`, `glob`, `grep`

### Agent Loop State Machine

TurnState: `RESTORE -> COMPACT -> COMMAND -> BUILD -> RUN -> SAVE -> RESPOND -> DONE`

```python
from agent import AgentLoop, AgentRunner

runner = AgentRunner(provider)
loop = AgentLoop(bus, runner, session_manager)
await loop.run()
```

## Project Structure

```
EasyCoding/
├── cli/                        # TypeScript CLI (Node.js)
│   ├── src/
│   │   ├── agent/              # LLM provider + Claude agent
│   │   │   ├── llm_provider.ts
│   │   │   └── claude_agent.ts
│   │   ├── commands/           # CLI commands (chat, task)
│   │   └── index.ts            # 入口
│   └── dist/                   # Compiled JavaScript
│
├── backend/                     # Python Backend (FastAPI)
│   ├── agent/                  # Agent 系统 (v0.9+ new)
│   │   ├── providers/           # LLM Provider 工厂
│   │   ├── tools/              # 工具系统
│   │   ├── loop.py             # AgentLoop 状态机
│   │   └── subagent.py         # SubagentManager
│   ├── bus/                    # MessageBus
│   ├── command/                # CommandRouter (P2)
│   ├── api/routes/             # HTTP endpoints
│   ├── services/               # Business logic
│   ├── domain/models/          # Domain entities
│   └── infrastructure/         # Storage + Channel adapters
│
├── memory/sessions/             # Session memory files
└── workspace/                  # Workspace project directories
```

## Documentation

- `README.md` - User manual with quick start guide
- `PRD.md` - Detailed product requirements and implementation phases
- `impl.md` - Architecture comparison with nanobot (reference for Phase 9 upgrades)

## Build Commands

### CLI (TypeScript)
```bash
cd cli
npm install              # Install dependencies
npm run build            # Compile TypeScript
node dist/index.js direct -p <project-path>   # Run direct mode
```

### Backend (Python)
```bash
cd backend
pip install fastapi uvicorn pydantic python-dotenv aiohttp slack-sdk httpx
PYTHONPATH=./ uvicorn main:app --host 0.0.0.0 --port 8080
```

## Running the CLI

### Direct Mode (Claude Code Style)
```bash
cd cli
export ANTHROPIC_API_KEY=sk-ant-xxxxx
node dist/index.js direct -p /path/to/project
```

### Supported LLM Providers

| Provider | Environment Variable | Default Model |
|----------|---------------------|---------------|
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-7 |
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| MiniMax | `MINIMAX_API_KEY` | abab5.5-chat |
| Groq | `GROQ_API_KEY` | mixtral-8x7b-32768 |
| OpenRouter | `OPENROUTER_API_KEY` | anthropic/claude-3-haiku |
| Azure | `AZURE_OPENAI_KEY` + `AZURE_OPENAI_ENDPOINT` | gpt-4 |
| Gemini | `GEMINI_API_KEY` | gemini-1.5-flash |
| DashScope | `DASHSCOPE_API_KEY` | qwen-plus |

### Backend Mode (Multi-Channel)

```bash
cd backend
export ANTHROPIC_API_KEY=sk-ant-xxxxx
export SLACK_BOT_TOKEN=xoxb-xxxxx  # Optional: enable Slack
PYTHONPATH=./ uvicorn main:app --host 0.0.0.0 --port 8080
```

Works with Slack, Telegram, Discord adapters when tokens are configured.

### CLI Commands (Direct Mode)

```
You: 看 cli/src/index.ts    # Read file (Chinese command)
You: read <path>           # Read file (English command)
You: !ls -la              # Execute shell command
You: ls                   # List directory
You: grep pattern         # Search code
You: exit                 # Exit
You: clear                # Clear screen
You: history              # Show conversation history
```

## Backend API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/chat` | Send chat message |
| POST | `/api/v1/chat/stream` | SSE streaming chat |
| POST | `/api/v1/sessions` | Create session |
| GET | `/api/v1/sessions/{id}` | Get session |
| POST | `/api/v1/tasks/enqueue` | Enqueue task |
| GET | `/api/v1/tasks/{id}/status` | Get task status |
| POST | `/api/v1/workspaces/{id}/git/commit` | Git commit |
| POST | `/api/v1/workspaces/{id}/git/pr` | Create PR |
| GET | `/api/v1/workspaces/{id}/memory/claude-md` | Get CLAUDE.md |

## Implementation Phases

| Phase | Content | Status |
|-------|---------|--------|
| Phase 1-8 | Core functionality (CLI, Backend, Multi-channel, etc.) | ✅ |
| Phase 9 | Architecture upgrade: Provider factory, Tool auto-discovery, Agent state machine | ✅ |

## Important Conventions

### File Naming
- Python: `snake_case.py`
- TypeScript: `camelCase.ts` or `kebab-case.ts`
- Config: `kebab-case.yaml`

### API Response Format
```json
{
  "id": "request-uuid",
  "status": "success|error|processing",
  "message": "Human-readable message",
  "data": { ... },
  "timestamp": "2026-06-08T00:00:00Z"
}
```

## Configuration Files

- `.env` - API keys and environment variables (not committed)
- `backend/.env.example` - Example environment configuration

## Git Workflow

- Main branch: `main` (protected)
- Feature branches: `feat/{name}` or `fix/{name}`
- All changes committed with clear messages
- PR required for merging to main