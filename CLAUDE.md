# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**Phase 1 completed** - Minimal viable system (CLI <-> Backend communication) is working.
**Next**: Phase 2 - Basic Memory storage

## Project Overview

**Coding-CLI** is an AI coding assistant CLI tool that receives developer instructions via chat platforms (Slack/Telegram/Discord), dispatches local Agent to execute coding tasks, and returns results to chat platforms.

**Agent Specialization**: The Agent specializes in DDD (Domain-Driven Design) assisted coding, helping developers understand and implement DDD patterns.

### DDD Patterns Supported

| Pattern | Description |
|---------|-------------|
| Entity | Objects with identity that persists over time |
| Value Object | Immutable objects defined by their attributes |
| Aggregate | Cluster of related entities with a root |
| Repository | Abstraction for data access |
| Domain Service | Operations that don't belong to entities |
| Domain Event | Records of significant domain occurrences |

### DDD Layer Conventions

```
api/          # HTTP entry points, DTOs, request/response models
app/          # Application services, use cases, orchestration
domain/       # Entities, value objects, domain services, port interfaces
infrastructure/# Port implementations, external adapters, persistence
trigger/      # Event handlers, webhooks, async triggers
types/        # Shared types, enums, constants
```

## Architecture

### Project Structure

```
coding-cli/
├── cli/                      # TypeScript CLI (Node.js)
│   ├── src/
│   │   ├── commands/         # CLI commands (chat, init, config, status)
│   │   ├── adapters/         # Channel adapters (Slack, Telegram, Discord, HTTP)
│   │   ├── gateway/          # Gateway client
│   │   ├── memory/           # Memory file management
│   │   └── types/            # TypeScript types
│   └── package.json
│
├── backend/                  # Python Backend (FastAPI)
│   ├── api/                  # HTTP entry points, DTOs
│   │   └── routes/           # chat, session, agent endpoints
│   ├── domain/               # Domain models, port interfaces
│   │   ├── models/           # Entities, value objects
│   │   └── ports/            # Port interfaces
│   ├── infrastructure/       # Port implementations
│   │   ├── adapters/         # Adapter implementations
│   │   └── storage/          # Storage implementations
│   ├── trigger/              # Triggers (HTTP adapters)
│   └── services/             # Agent services
│
├── memory/                   # Memory file storage
│   └── sessions/             # Session memory files
│
└── PRD.md                    # Product requirements document
```

### Agent System Architecture

```
Multi-Agent System per Workspace:
├── Queue Agent (1)           # Task queue maintenance, deduplication
├── Writer Agent (1)         # Exclusive code modification (file lock)
├── Reader Agents (N)         # Read project, chat with users, concurrent
├── Evaluator Agent (2)      # Requirement completeness evaluation, clarification
├── Analyzer Agents (N)       # Project analysis, code review
└── Git Agent (1)             # Git operations, changelog, PR creation
```

### Agent Role Responsibilities

| Agent | Count | Responsibility |
|-------|-------|----------------|
| Queue Agent | 1 | Task queue, deduplication, dispatch |
| Writer Agent | 1 | Code modification (file lock protected) |
| Reader Agent | N | Read project, user chat, concurrent read |
| Evaluator Agent | 2 | Requirement evaluation, clarification questions |
| Git Agent | 1 | Git commit, changelog, PR creation |

### Key Flows

**Task Queue Flow**:
```
User Message -> Reader Agent -> Evaluator Agent (check completeness)
    -> If incomplete: Clarification questions -> User Response -> Re-evaluate
    -> If complete: Queue Agent -> Deduplication Check -> Writer Agent (execute)
    -> Git Agent (commit) -> Notify User
```

**Workspace Isolation**:
- Each chat group (channel) maps to an independent Workspace
- Each Workspace has its own Agent system and project directory
- Directory structure: `/workspace/{workspace_id}/project/` + `/workspace/{workspace_id}/changelog.md`

## Build Commands

### Backend (Python)
```bash
# Install dependencies
cd backend && pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --port 8080

# Run tests
pytest
```

### CLI (TypeScript)
```bash
# Install dependencies
cd cli && npm install

# Build
npm run build

# Link for development
npm link

# Run
coding-cli chat
```

## Implementation Phases

See PRD.md Section 5 for detailed implementation plan:

| Phase | Content | Duration | Status |
|-------|---------|----------|--------|
| Phase 1 | Minimal viable system (CLI <-> Backend) | 1 week | TODO |
| Phase 2 | Basic Memory storage | 1 week | TODO |
| Phase 3 | Single Agent + Evaluator | 1-2 weeks | TODO |
| Phase 4 | Task queue + deduplication | 1-2 weeks | TODO |
| Phase 5 | Multi-Channel | 2 weeks | TODO |
| Phase 6 | Workspace isolation | 1 week | TODO |
| Phase 7 | Git Agent | 1 week | TODO |
| Phase 8 | Long-term memory + review | 1 week | TODO |

## Memory File Structure

```
memory/
├── sessions/{session-id}.json   # Session data (messages, context)
├── sessions/{session-id}.md     # Human-readable summary
├── projects/{project-hash}/context.md  # Project-level context
└── agents/{agent-id}/config.yaml # Agent configuration
```

## Important Conventions

### Commit Messages
```
feat(module): add user registration endpoint

- Add POST /api/v1/users endpoint
- Integrate with UserRepository
- Add input validation

Closes: #123
```

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
  "timestamp": "2026-06-06T00:00:00Z"
}
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| CLI | TypeScript + Node.js | Command entry, channel adapters, memory |
| Backend | Python + FastAPI | Business logic, Agent dispatch, LLM integration |
| Storage | JSON Files (memory/) | Session memory |
| Long-term | CLAUDE.md | Project knowledge persistence |

## Configuration

- Backend config: `backend/config.yaml`
- Agent config: `agents/*.yaml` (per workspace)
- Channel config: `channels/*.yaml`

## Git Workflow

- Main branch: `main` (protected)
- Task branches: `task/{task-name}-{date}`
- All changes committed with clear messages
- PR required for merging to main