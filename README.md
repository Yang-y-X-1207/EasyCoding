# Coding-CLI 用户手册

Coding-CLI 是一个 AI 编程助手 CLI 工具，支持直接本地对话和通过聊天平台（Slack/Telegram/Discord）远程控制。

---

## 快速开始

### 1. 安装 CLI

```bash
cd cli
npm install
npm run build
```

### 2. 配置 API Key

Coding-CLI 支持多种 LLM 提供商，选择一种配置：

```bash
# MiniMax (推荐国内用户)
export MINIMAX_API_KEY=sk-cp-xxxxxxxx

# OpenAI
export OPENAI_API_KEY=sk-xxxxx

# Anthropic (Claude)
export ANTHROPIC_API_KEY=sk-ant-xxxxx

# Google Gemini
export GEMINI_API_KEY=xxxxx
```

或创建 `.env` 文件：

```bash
# 在项目根目录创建 .env
MINIMAX_API_KEY=sk-cp-xxxxxxxx
```

### 3. 运行

```bash
# 直接对话模式 (Claude Code 风格)
node dist/index.js direct -p /你的项目路径

# 示例
node dist/index.js direct -p ~/my-project
```

---

## 工作模式

### 模式一：直接 CLI（无需后端）

直接与 AI 对话，操作本地文件：

```bash
node dist/index.js direct -p .
```

特点：
- 无需启动后端服务
- 即装即用
- 支持文件读写、命令执行、代码搜索

### 模式二：后端服务（多渠道）

需要启动 Python 后端，支持 Slack/Telegram/Discord 接入：

```bash
cd backend
pip install fastapi uvicorn python-dotenv aiohttp slack-sdk httpx
PYTHONPATH=./ uvicorn main:app --host 0.0.0.0 --port 8080
```

然后配置渠道 Token 后，AI 在群聊中响应。

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

### 示例对话

```
You: 看 cli/src/index.ts
📄 cli/src/index.ts (56 行)
...
```

```
You: !ls -la
🔧 执行: ls -la
...
```

```
You: 帮我创建一个 hello.py
🤖 AI 正在分析您的需求...
```

---

## 支持的 LLM 提供商

| 提供商 | 环境变量 | 默认模型 |
|--------|----------|-----------|
| MiniMax | `MINIMAX_API_KEY` | abab5.5-chat |
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-7 |
| Google Gemini | `GEMINI_API_KEY` | gemini-1.5-flash |
| Azure | `AZURE_OPENAI_KEY` + `AZURE_OPENAI_ENDPOINT` | gpt-4 |

---

## 配置文件

### .env 例子

```bash
# Backend 配置
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8080

# LLM 配置
ANTHROPIC_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-sonnet-4-7

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
├── cli/                    # TypeScript CLI
│   ├── src/
│   │   ├── agent/          # LLM provider + Agent
│   │   ├── commands/        # CLI 命令
│   │   └── index.ts         # 入口
│   └── dist/                # 编译输出
│
├── backend/                # Python 后端
│   ├── api/routes/          # HTTP 接口
│   ├── services/            # 业务逻辑
│   ├── domain/models/       # 领域模型
│   └── infrastructure/      # 存储和适配器
│
├── memory/                 # Session 记忆存储
│   └── sessions/           # 会话历史
│
└── workspace/              # 工作区项目目录
```

---

## 常见问题

### Q: 直接模式报 "未找到 LLM API 配置"

A: 确保已设置环境变量或 `.env` 文件中有有效的 API Key：

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

## 后端 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/chat` | 发送消息 |
| GET | `/api/v1/sessions/{id}` | 获取会话 |
| POST | `/api/v1/tasks/enqueue` | 添加任务 |
| GET | `/api/v1/tasks/{id}/status` | 任务状态 |

---

## License

MIT