# EasyCoding 与 nanobot 相似模块实现对比

本文档对比 EasyCoding 与 nanobot 在功能相似模块上的具体实现差异，为 EasyCoding 的架构升级提供参考。

---

## 1. LLM Provider 多供应商支持

### nanobot 实现 (`providers/`)

**两层架构设计：**

```python
# Layer 1: ProviderSpec 元数据注册表 (registry.py)
@dataclass(frozen=True)
class ProviderSpec:
    name: str              # 配置字段名，如 "dashscope"
    keywords: tuple        # 模型名关键字匹配
    env_key: str           # API Key 环境变量
    display_name: str
    backend: str           # "openai_compat" | "anthropic" | "azure_openai" | ...
    is_gateway: bool
    detect_by_key_prefix: str  # 如 "sk-or-" 识别 OpenRouter
    supports_prompt_caching: bool
    # ...

PROVIDERS: tuple[ProviderSpec, ...]  # ~30 种 provider spec
```

**Layer 2: 工厂函数 (`factory.py`)**

```python
def make_provider(config, preset_name=None, preset=None, model=None):
    # 1. 解析 ModelPresetConfig
    # 2. 通过 find_by_name(provider_name) 查找 ProviderSpec
    # 3. 根据 backend 类型分支构造
    if backend == "openai_codex": provider = OpenAICodexProvider(...)
    elif backend == "anthropic": provider = AnthropicProvider(...)
    elif backend == "azure_openai": provider = AzureOpenAIProvider(...)
    else: provider = OpenAICompatProvider(...)  # 默认走 OpenAI 兼容
    # 4. 可选包装 FallbackProvider 实现主备切换
```

**FallbackProvider 装饰器 (`fallback_provider.py`)**

```python
class FallbackProvider:
    """主备切换，3次失败后进入60秒冷却期"""
    def __init__(self, primary, fallback_presets, provider_factory):
        self._failure_count = 0
        self._cooldown_until = 0

    async def chat(self, messages, ...):
        response = await self.primary.chat(...)
        if response.finish_reason == "error" and self._should_fallback(response):
            # 尝试 fallback presets
            for fb in self.fallback_presets:
                fb_provider = self.provider_factory(fb)
                # ...
```

**特点：**
- ProviderSpec 枚举表驱动，新加 provider 只需添加 2 行配置
- `provider_signature(...)` 哈希检测配置变化，触发 provider 重建
- 懒加载：`__getattr__` + `_LAZY_IMPORTS` 避免导入所有 SDK
- 统一错误结构：`finish_reason="error"` + status_code/kind/type/retry_after

### EasyCoding 实现 (`cli/src/agent/llm_provider.ts`)

**简单 Switch 分支：**

```typescript
export class LLMProviderClient {
  async chat(messages, system?: string): Promise<LLMResponse> {
    switch (this.config.provider) {
      case "openai":   return this.openaiChat(messages, system);
      case "anthropic": return this.anthropicChat(messages, system);
      case "gemini":   return this.geminiChat(messages, system);
      case "azure":    return this.azureChat(messages, system);
      case "minimax":  return this.minimaxChat(messages, system);
    }
  }
}
```

**特点：**
- 每个 case 直接内联 HTTP 调用，无抽象层
- 环境变量检测在 `loadProviderFromEnv()` 顺序检查
- 无 provider 元数据表，扩展需要改 switch 语句
- 后端 (`backend/services/llm_service.py`) 只有 Anthropic 单实现

**改进建议：**
```python
# 1. 添加 ProviderSpec 元数据表
PROVIDER_SPECS = {
    "anthropic": ProviderSpec(
        name="anthropic",
        keywords=("claude", "claude-sonnet", "claude-opus"),
        env_key="ANTHROPIC_API_KEY",
        backend="anthropic",
        default_model="claude-sonnet-4-7",
    ),
    # ... 其他 provider
}

# 2. 工厂函数替代 switch
def make_provider(config: ProviderConfig) -> LLMProvider:
    spec = find_spec_by_name(config.provider)
    if spec.backend == "anthropic":
        return AnthropicProvider(config.apiKey, config.model)
    elif spec.backend == "openai_compat":
        return OpenAICompatProvider(config.apiKey, config.baseUrl, config.model)
    # ...
```

---

## 2. Tool 工具系统

### nanobot 实现 (`agent/tools/`)

**Auto-Discovery 机制 (`loader.py`)：**

```python
class ToolLoader:
    def discover(self) -> list[type[Tool]]:
        for _importer, module_name, _ispkg in pkgutil.iter_modules(self._package.__path__):
            if module_name.startswith("_") or module_name in _SKIP_MODULES:
                continue
            module = importlib.import_module(f".{module_name}", self._package.__name__)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, Tool)
                    and attr is not Tool
                    and not attr_name.startswith("_")
                    and not getattr(attr, "__abstractmethods__", None)
                    and getattr(attr, "_plugin_discoverable", True)  # 插件可放弃发现
                    and id(attr) not in seen):
                    results.append(attr)

    def load(self, ctx, registry, scope="core"):
        # 1. discover() 扫描内置工具
        # 2. _discover_plugins() 扫描 entry_points
        # 3. 每个工具调用 tool_cls.enabled(ctx) 检核，tool_cls.create(ctx) 实例化
```

**插件发现 (`_discover_plugins`)：**

```python
def _discover_plugins(self):
    eps = importlib.metadata.entry_points(group="nanobot.tools")
    for ep in eps:
        tool_cls = ep.load()
        # 注册到 registry
```

**pyproject.toml 插件注册点：**
```toml
[project.entry-points."nanobot.tools"]
my_plugin = "my_package.plugins:MyTool"
```

**Tool 基类 (`base.py`)：**

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema

    @classmethod
    def config_cls(cls) -> type[BaseModel] | None: ...
    @classmethod
    def enabled(cls, ctx: ToolContext) -> bool: ...  # 配置门控
    @classmethod
    def create(cls, ctx: ToolContext) -> Tool: ...   # 工厂方法

    async def execute(self, **kwargs) -> Any: ...

# 参数类型构建器
class Schema(ABC):
    @staticmethod
    def validate_json_schema_value(value, schema) -> tuple[bool, str | None]: ...

# 装饰器
def tool_parameters(schema_dict):
    """简化 JSON Schema 定义"""
    ...
```

**ToolRegistry (`registry.py`)：**

```python
class ToolRegistry:
    def register(self, tool: Tool): ...
    def get_definitions(self) -> list[dict]:
        """返回 OpenAI 格式 tool schemas，缓存结果"""
    def prepare_call(self, name, params) -> tuple[Tool, dict, str | None]:
        """类型转换 + JSON Schema 校验"""
    def execute(self, name, params) -> str:
        """热路径，返回错误字符串（带标准 hint）"""
```

### EasyCoding 实现 (`cli/src/agent/claude_agent.ts`)

**手动 ToolHandler 类：**

```typescript
class ToolHandler {
  constructor(private projectPath: string) {}

  async handleCommand(input: string): Promise<string | null> {
    // 字符串匹配指令
    if (trimmed.startsWith("read ")) return this.readFile(filePath);
    if (trimmed.startsWith("write ")) return this.writeFile(filePath, content);
    if (trimmed.startsWith("!")) return this.runBash(cmd);
    // ... 中文字符检测
  }
}
```

**特点：**
- 无 Tool 基类抽象
- 字符串模式匹配指令（`startsWith`）
- 手工分支处理所有工具逻辑
- 后端 Python 无独立 Tool 层，文件操作散落在各 Service

**改进建议：**
```python
# backend/agent/tools/base.py
class Tool(ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema

    @classmethod
    def enabled(cls, ctx: ToolContext) -> bool: ...
    @classmethod
    def create(cls, ctx: ToolContext) -> Tool: ...

    async def execute(self, **kwargs) -> Any: ...

# backend/agent/tools/loader.py
class ToolLoader:
    def discover(self) -> list[type[Tool]]:
        # pkgutil.iter_modules 扫描
        # entry_points 扫描插件
        ...

    def load(self, ctx, registry: ToolRegistry, scope="core"):
        for tool_cls in self.discover():
            if tool_cls.enabled(ctx):
                registry.register(tool_cls.create(ctx))
```

---

## 3. Agent 执行循环

### nanobot 实现 (`agent/loop.py`, `agent/runner.py`)

**双层分离架构：**

```
AgentRunner (transport-agnostic)          AgentLoop (product layer)
├── provider: LLMProvider                 ├── MessageBus (in/out queues)
├── run(AgentRunSpec) → 核心循环          ├── ToolRegistry
├── _execute_tools()                      ├── AgentRunner
└── 错误处理/重试/上下文治理               ├── SubagentManager
                                           ├── ContextBuilder
                                           ├── SessionManager
                                           └── 状态机 TurnState
```

**AgentRunner (`runner.py`) — 纯 LLM ↔ Tool 循环：**

```python
class AgentRunner:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def run(self, spec: AgentRunSpec):
        while iteration < max_iterations:
            # 1. 构建请求 (messages + tools)
            # 2. 调用 provider.chat_stream_with_retry()
            # 3. 如果有 tool_calls：
            #    - hook.before_execute_tools(context)
            #    - _execute_tools() 并发或串行执行
            #    - hook.after_execute_tools()
            #    - 追加 tool 结果消息
            # 4. 如果无 tool_calls：返回结果
```

**AgentLoop (`loop.py`) — 状态机驱动：**

```python
class TurnState(Enum):
    RESTORE = auto()
    COMPACT = auto()
    COMMAND = auto()
    BUILD = auto()
    RUN = auto()
    SAVE = auto()
    RESPOND = auto()
    DONE = auto()

_TRANSITIONS: dict[tuple[TurnState, str], TurnState] = {
    (RESTORE, "ok"): COMPACT,
    (COMPACT, "ok"): COMMAND,
    (COMMAND, "dispatch"): BUILD,
    (BUILD, "ok"): RUN,
    (RUN, "ok"): SAVE,
    # ...
}

async def _process_message(self, msg: InboundMessage):
    state = TurnState.RESTORE
    while state != TurnState.DONE:
        handler = getattr(self, f"_state_{state.name.lower()}")
        event = await handler(msg)
        state = _TRANSITIONS[(state, event)]
```

**MessageBus 解耦 (`bus/queue.py`)：**

```python
class MessageBus:
    def __init__(self):
        self._inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    def publish_inbound(self, msg: InboundMessage): ...
    async def consume_inbound(self) -> InboundMessage: ...  # 1s timeout 唤醒检查

# AgentLoop.run() 主循环
async def run(self):
    while True:
        msg = await bus.consume_inbound()  # 1s timeout
        # 检查 auto_compact 是否过期
        # _dispatch(msg) 分发到 session
```

### EasyCoding 实现

**CLI 模式 (`cli/src/agent/claude_agent.ts`) — 简单循环：**

```typescript
while (true) {
    input = await question("You: ");
    // 检查工具命令
    const toolResult = await tools.handleCommand(input);
    if (toolResult) { /* 直接输出 */ continue; }
    // 发送到 LLM
    const response = await client.chat(messages, systemPrompt);
    // 输出结果
}
```

**Backend 模式 (`backend/services/chat_service.py`) — 简单 Service：**

```python
class ChatService:
    async def chat(self, session: Session, message: str):
        # 1. 添加消息到 session
        # 2. 简单评估是否需要澄清
        # 3. 调用 LLM
        # 4. 返回响应
```

**特点：**
- 无 AgentRunner / AgentLoop 分离
- 无状态机
- CLI 模式直接调用 tool，无真正的 Agent Loop
- Backend 无 MessageBus，通过 FastAPI HTTP 直接调用

**改进建议：**
```python
# backend/agent/loop.py
class AgentLoop:
    """产品层：管理 MessageBus、Session、状态机"""

    async def run(self):
        while True:
            msg = await self.bus.consume_inbound()
            await self._dispatch(msg)

# backend/agent/runner.py
class AgentRunner:
    """传输无关：纯 LLM ↔ Tool 循环"""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def run(self, spec: AgentRunSpec):
        while iteration < spec.max_iterations:
            response = await self.provider.chat_stream(...)
            if response.should_execute_tools:
                results = await self._execute_tools(response.tool_calls)
                # 追加 tool 结果，继续循环
            else:
                return response
```

---

## 4. Session 会话管理

### nanobot 实现 (`session/`)

```python
class SessionManager:
    def __init__(self, store: SessionStore, config: Config):
        self.sessions: dict[str, Session] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    async def get_or_create(self, session_key: str) -> Session:
        if session_key not in self.sessions:
            self.sessions[session_key] = await self.store.load(session_key)
        return self.sessions[session_key]

    def save(self, session: Session):
        asyncio.create_task(self.store.save(session))
```

### EasyCoding 实现 (`backend/infrastructure/storage/`)

```python
# session_file_store.py
class SessionFileStore:
    def save(self, session: Session):
        path = self._session_path(session.session_id)
        with open(path, "w") as f:
            json.dump(session.to_dict(), f)

    def load(self, session_id: str) -> Session | None:
        path = self._session_path(session_id)
        if path.exists():
            data = json.loads(path.read_text())
            return Session.from_dict(data)
```

**特点：**
- nanobot 有内存缓存 + 异步写回
- EasyCoding 直接同步写文件
- nanobot 有 per-session 锁保证串行

---

## 5. Subagent 子代理

### nanobot 实现 (`agent/subagent.py`)

```python
class SubagentManager:
    def __init__(self, config, tool_loader: ToolLoader, ...):
        self.runner = AgentRunner(...)  # 复用同一 runner

    async def run_subagent(self, spec: SubagentSpec) -> Any:
        # 用不同 ToolRegistry 创建 subagent runner
        sub_tools = self.tool_loader.load(ctx, registry, scope="subagent")
        sub_runner = AgentRunner(provider, tools=sub_tools)
        result = await sub_runner.run(spec)
        # 通过 MessageBus  announcing result
        self._announce_result(result)

    def _announce_result(self, result):
        # 发回 MessageBus 作为 InboundMessage
        self.bus.publish_inbound(InboundMessage(
            channel="system", sender_id="subagent", ...
        ))
```

### EasyCoding 实现

**无独立 Subagent 机制。** Evaluator Agent 是独立 Service 调用，非子代理模式。

---

## 6. Command 指令路由

### nanobot 实现 (`command/`)

```python
class CommandRouter:
    def __init__(self):
        self.commands: dict[str, CommandHandler] = {}

    def register(self, name: str, handler: CommandHandler):
        self.commands[name] = handler

    async def dispatch(self, text: str, ctx: RequestContext) -> CommandResult:
        if text.startswith("/"):
            parts = text.split()
            name = parts[0][1:]
            if name in self.commands:
                return await self.commands[name].execute(parts[1:], ctx)

# 内置命令：/stop, /model, /goal, /dream, /new, ...
```

### EasyCoding 实现

**CLI 模式手工分支 (`claude_agent.ts`)：**

```typescript
const lower = input.toLowerCase();
if (lower === "exit") { ... }
if (lower === "clear") { ... }
if (lower === "history") { ... }
if (lower === "help") { ... }
```

**无统一 CommandRouter。**

---

## 7. 配置与依赖注入

### nanobot 实现 (`config/`)

**Pydantic Config Schema：**

```python
class Config(BaseSettings):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    channels: ChannelsConfig
    agents: AgentsConfig
    providers: ProvidersConfig
    tools: ToolsConfig

    def get_provider_name(self, model, preset=None) -> str:
        # 通过 ProviderSpec.keywords 匹配 provider

    def resolve_config_env_vars(self, config):
        # 替换 ${VAR} 为环境变量
```

**依赖注入：**
- 无 IoC 容器
- `ToolContext` 是 per-tool DI bag
- `RequestContext` 通过 `contextvars` per-request 注入
- `WorkspaceScopeResolver` 通过 `contextvars` 绑定 workspace scope

### EasyCoding 实现

**无正式配置 schema。** 使用 `.env` 文件 + `os.getenv()` 散落调用。

---

## 8. 关键差距总结

| 维度 | nanobot | EasyCoding | 改进优先级 | 状态 |
|------|---------|------------|-----------|------|
| **Provider 架构** | ProviderSpec 元数据表 + 工厂 + FallbackProvider | ✅ 已实现 (providers/) | P1 | ✅ |
| **Tool 发现** | pkgutil + entry_points 自动发现 | ✅ 已实现 (tools/loader.py) | P1 | ✅ |
| **Agent 循环** | AgentRunner/AgentLoop 双层分离 + 状态机 | ✅ 已实现 (loop.py) | P1 | ✅ |
| **MessageBus** | asyncio.Queue 解耦 channels/agent | ✅ 已实现 (bus/queue.py) | P1 | ✅ |
| **Session 管理** | 内存缓存 + 异步写回 + per-session 锁 | ✅ 已实现 (session_manager.py) | P2 | ✅ |
| **Subagent** | 复用 AgentRunner + MessageBus 回调 | ✅ 已实现 (subagent.py) | P2 | ✅ |
| **Command 路由** | CommandRouter 统一分发 | ✅ 已实现 (command/router.py) | P2 | ✅ |
| **配置 Schema** | Pydantic BaseSettings | ✅ 已实现 (config.py) | P2 | ✅ |
| **错误结构化** | finish_reason + error_kind/type/code/retry_after | ✅ 已实现 (providers/base.py) | P2 | ✅ |
| **上下文注入** | contextvars RequestContext | 参数传递 | P3 | ⏳ |

**图例**: ✅ 已实现 | ⏳ 待实现

---

## 9. 推荐优先升级点

### P1 - 核心架构 (✅ 已完成)

**1. LLM Provider 重构** ✅
```python
# 新增 backend/agent/providers/registry.py
@dataclass(frozen=True)
class ProviderSpec:
    name: str
    keywords: tuple
    env_key: str
    backend: str
    default_model: str
    # ...

PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec("anthropic", ("claude",), "ANTHROPIC_API_KEY", "anthropic", "claude-sonnet-4-7"),
    ProviderSpec("openai", ("gpt",), "OPENAI_API_KEY", "openai_compat", "gpt-4o"),
    # ...
)

def find_provider_spec(name: str) -> ProviderSpec | None: ...

# 新增 backend/agent/providers/factory.py
def make_provider(config: ProviderConfig) -> LLMProvider:
    spec = find_provider_spec(config.provider)
    if spec.backend == "anthropic":
        return AnthropicProvider(config.apiKey, config.model)
    # ...
```

**2. Agent Loop 状态机** ✅
```python
# 新增 backend/agent/loop.py
class TurnState(Enum):
    RESTORE = auto(); COMPACT = auto(); COMMAND = auto()
    BUILD = auto(); RUN = auto(); SAVE = auto()
    RESPOND = auto(); DONE = auto()

_TRANSITIONS = {
    (RESTORE, "ok"): COMPACT,
    (COMPACT, "ok"): COMMAND,
    (COMMAND, "dispatch"): BUILD,
    (BUILD, "ok"): RUN,
    (RUN, "ok"): SAVE,
    (SAVE, "ok"): RESPOND,
    (RESPOND, "ok"): DONE,
}

class AgentLoop:
    async def _process_message(self, msg):
        state = TurnState.RESTORE
        while state != TurnState.DONE:
            handler = getattr(self, f"_state_{state.name.lower()}")
            event = await handler(msg)
            state = _TRANSITIONS[(state, event)]
```

**3. Tool 自动发现** ✅
```python
# 新增 backend/agent/tools/loader.py
class ToolLoader:
    def discover(self) -> list[type[Tool]]:
        results = []
        for _importer, module_name, _ispkg in pkgutil.iter_modules(self._package.__path__):
            if module_name.startswith("_"): continue
            module = importlib.import_module(f".{module_name}", self._package.__name__)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if self._is_tool_class(attr):
                    results.append(attr)
        return results

    def load(self, ctx, registry: ToolRegistry, scope="core"):
        for tool_cls in self.discover():
            if tool_cls.enabled(ctx):
                registry.register(tool_cls.create(ctx))
```

### P2 - 体验完善 (部分完成)

**4. MessageBus 解耦** ✅
```python
# 新增 backend/bus/queue.py
class MessageBus:
    def __init__(self):
        self._inbound = asyncio.Queue()
        self._outbound = asyncio.Queue()

    def publish_inbound(self, msg: InboundMessage): ...
    async def consume_inbound(self) -> InboundMessage: ...
```

**5. FallbackProvider** ✅
```python
# 新增 backend/agent/providers/fallback_provider.py
class FallbackProvider:
    """主备切换，3次失败后60秒冷却"""
```

### P3 - 长期演进 (⏳ 待实现)

**6. Pydantic Config Schema**
**7. CommandRouter 统一指令分发**
**8. Session 内存缓存 + 异步写回**