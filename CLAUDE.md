# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**Phase 1-8 COMPLETED** - All implementation phases are complete. The system can run as:
1. Local CLI (Claude Code style) - Direct AI chat with file operations
2. Backend server - Multi-channel support (Slack, Telegram, Discord)

## Project Overview

**Coding-CLI** is an AI coding assistant CLI tool with two operating modes:

1. **Direct CLI Mode** - Claude Code style local chat with MiniMax/OpenAI/Anthropic API
2. **Backend Mode** - Receives instructions via chat platforms, dispatches Agent to execute tasks

## Architecture

### Two Operating Modes

```
# Mode 1: Direct CLI (No backend needed)
User -> CLI (direct API call) -> Local file operations

# Mode 2: Backend (Multi-channel)
Slack/Telegram/Discord -> Backend (FastAPI) -> Agent -> File/Git operations
```

### Project Structure

```
EasyCoding/
├── cli/                        # TypeScript CLI (Node.js)
│   ├── src/
│   │   ├── agent/              # LLM provider + Claude agent
│   │   │   ├── llm_provider.ts  # Multi-vendor LLM support
│   │   │   └── claude_agent.ts # CLI agent with tool execution
│   │   ├── commands/            # CLI commands (chat, task)
│   │   └── gateway/             # Backend gateway client
│   └── dist/                    # Compiled JavaScript
│
├── backend/                     # Python Backend (FastAPI)
│   ├── api/routes/             # HTTP endpoints (chat, session, git, memory, etc.)
│   ├── services/                # Business logic (chat, evaluator, git, pr, notification)
│   ├── domain/models/           # Domain entities
│   └── infrastructure/          # Storage + Channel adapters
│
├── memory/sessions/             # Session memory files
└── workspace/                   # Workspace project directories
```

## Build Commands

### CLI (TypeScript)
```bash
cd cli
npm install              # Install dependencies
npm run build           # Compile TypeScript
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

# Set API key (MiniMax as example)
export MINIMAX_API_KEY=sk-cp-xxxxx

# Run with project path
node dist/index.js direct -p /path/to/project
```

### Supported LLM Providers

| Provider | Environment Variable | Default Model |
|----------|---------------------|---------------|
| MiniMax | `MINIMAX_API_KEY` | abab5.5-chat |
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-7 |
| Google | `GEMINI_API_KEY` | gemini-1.5-flash |
| Azure | `AZURE_OPENAI_KEY` + `AZURE_OPENAI_ENDPOINT` | gpt-4 |

### CLI Commands

```
You: 看 cli/src/index.ts    # Read file (Chinese command)
You: read <path>            # Read file (English command)
You: !ls -la               # Execute shell command
You: ls                    # List directory
You: grep pattern          # Search code
You: exit                  # Exit
You: clear                 # Clear screen
You: history               # Show conversation history
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
| POST | `/api/v1/workspaces/{id}/git/pr/notify` | Send review notification |

## Agent System Architecture

```
Multi-Agent System per Workspace:
├── Queue Agent (1)        # Task queue, deduplication, dispatch
├── Writer Agent (1)        # Exclusive code modification (file lock)
├── Reader Agents (N)       # Read project, chat with users, concurrent
├── Evaluator Agent (2)     # Requirement completeness evaluation
├── Git Agent (1)           # Git commit, changelog, PR creation
└── Analyzer Agents (N)    # Project analysis, code review
```

## Implementation Phases (All Complete)

| Phase | Content | Status |
|-------|---------|--------|
| Phase 1 | Minimal viable system (CLI <-> Backend) | ✅ |
| Phase 2 | Session Memory storage | ✅ |
| Phase 3 | Single Agent + Evaluator + SSE | ✅ |
| Phase 4 | Task queue + deduplication | ✅ |
| Phase 5 | Multi-Channel (Slack/Telegram/Discord) | ✅ |
| Phase 6 | Workspace isolation | ✅ |
| Phase 7 | Git Agent + Changelog | ✅ |
| Phase 8 | Long-term memory + PR + Notification | ✅ |

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