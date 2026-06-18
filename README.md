# OnCall Agent

智能 OnCall 运维助手:**RAG 知识库问答** + **AIOps 自动故障诊断**(Plan-Execute-Replan)。

基于 LangGraph 原生 StateGraph 手搭的对话 Agent 与诊断 Agent,接入 Milvus 向量库与
MCP 工具协议。本文档只描述**已实现**的内容。

## 技术栈

- Python 3.13 + [uv](https://docs.astral.sh/uv/)
- FastAPI + LangGraph(原生 StateGraph)+ 通义千问(DashScope)
- Milvus 向量数据库 + MCP(Model Context Protocol)工具协议
- 测试 pytest,代码质量 ruff(lint + format)

## 功能

- **RAG 对话**:手搭 ReAct 循环图(model ↔ tools),知识库语义检索、多轮记忆、消息修剪、流式输出
- **AIOps 诊断**:Plan-Execute-Replan 诊断图,自动巡检告警 → 查指标/日志 → 检索知识库 → 生成诊断报告
- **知识库**:Markdown 文档分块、嵌入、写入 Milvus,支持上传更新
- **工具接入**:本地工具(知识检索)+ MCP 工具(告警/指标/日志),失败降级可恢复

## 快速开始

需先准备 DashScope API Key:从 [.env.example](.env.example) 复制一份 `.env` 填入 `DASHSCOPE_API_KEY`
(容器方式则将其设为宿主机环境变量)。

### 方式一:容器化一键启动(推荐)

需安装 Docker。一条命令构建并启动全栈(向量库 + 2 个 MCP 服务 + 主应用):

```bash
docker compose up --build      # 首次构建较慢;之后 docker compose up -d 即可
```

`compose` 会按依赖顺序启动 6 个容器(etcd / minio / milvus / monitor / logs / app),
app 等 milvus 健康后再启动。访问 http://127.0.0.1:8000/ 即可使用。停止:`docker compose down`。

### 方式二:本地开发启动

适合改代码调试。先装依赖,再用 [honcho](https://github.com/nickstenning/honcho) 一键起前台进程:

```bash
uv sync                  # 创建虚拟环境并安装全部依赖(含 dev)
docker compose up -d milvus etcd minio   # 仅起向量库
uv run honcho start      # 一条命令同启 2 个 MCP 服务 + 主应用,Ctrl+C 一并停止
```

PyCharm 用户:将解释器指向 `.venv\Scripts\python.exe`。

- **Web 界面**:http://127.0.0.1:8000/(对话 / 一键诊断 / 上传文档)
- 健康检查:http://127.0.0.1:8000/health
- API 文档:http://127.0.0.1:8000/docs

> 也可单独启动某进程,如 `uv run uvicorn oncall_agent.main:create_app --factory`,`uv run python -m mcp_servers.logs_server`,`uv run python -m mcp_servers.monitor_server`。
> MCP 未启动时主应用仍可运行,Agent 自动降级为仅用本地知识库工具。

### 建立知识库索引

```bash
# 上传单篇
curl.exe -X POST "http://127.0.0.1:8000/api/documents" -F "file=@knowledge_docs/cpu_high_usage.md"

# 批量上传 knowledge_docs/ 下全部文档(PowerShell)
Get-ChildItem knowledge_docs\*.md | ForEach-Object {
    curl.exe -X POST "http://127.0.0.1:8000/api/documents" -F "file=@knowledge_docs/$($_.Name)"
}
```

## API

### 对话

```bash
# 非流式
curl.exe -X POST "http://127.0.0.1:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "question": "CPU使用率过高怎么排查?"}'

# 流式(SSE)
curl.exe -N -X POST "http://127.0.0.1:8000/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "question": "服务不可用如何处理?"}'
```

同一 `session_id` 的多轮对话共享上下文;历史超出上限时自动修剪最旧消息。

### AIOps 自动诊断

```bash
curl.exe -N -X POST "http://127.0.0.1:8000/api/diagnosis"
```

SSE 推送计划、每步执行结果与最终报告。诊断图四个节点:

- **Planner**:基于真实工具清单与知识库经验制定诊断计划
- **Executor**:逐步执行,携带已执行步骤上下文,对未知工具调用容错
- **Replanner**:三态决策(continue / replan / respond)+ 步数护栏防失控
- **Reporter**:综合全部数据生成 Markdown 诊断报告

## 项目结构

```
src/oncall_agent/
├── main.py          应用工厂 create_app() + lifespan(资源装配,所有有状态资源在此构造注入)
├── settings.py      pydantic-settings 配置(SecretStr 护 key,field_validator 校验,环境变量可覆盖)
├── logging.py       loguru,setup_logging(settings) 显式初始化无副作用,patcher 注入 request-id
├── dependencies.py  AppResources 容器 + get_resources(FastAPI 依赖注入)
├── context.py       contextvar:request_id_var + token_usage_var/TokenUsage + track_token_usage()
├── middleware.py    request_middleware:每请求设 request-id 写响应头
├── callbacks.py     TokenUsageCallback:on_llm_end 累加 token 到 contextvar
├── rate_limit.py    slowapi Limiter(按 IP)
├── api/             health/documents/chat/diagnosis 路由 + schemas.py(统一 ApiResponse[T] 信封 PEP695泛型)
├── domain/
│   ├── knowledge/   splitter(三阶段分割,同h1才合并)/ indexer(切块→嵌入→先删后插)/ retriever(检索+阈值过滤)/ models
│   ├── chat/        graph(手搭 ReAct: trim→model⇄tools)/ service(编译图+注入checkpointer+thread_id多轮记忆)/ tools(闭包工厂)/ prompts
│   └── diagnosis/   state(operator.add累积past_steps)/ planner(检索经验+真实工具清单,None兜底)/ executor(手写ReAct循环+past_steps上下文+未知工具容错)/ replanner(三态决策Literal+MAX_STEPS护栏)/ reporter(直出Markdown不用结构化输出)/ graph(条件边按plan空否路由)/ service / prompts
│   └── infra/       llm(create_chat_model工厂)/ milvus(MilvusClient封装,insert/delete后flush)/ embeddings / mcp(MCPToolProvider加载+缓存+失败降级可恢复)
mcp_servers/         独立运行的 mock MCP:monitor(query_active_alerts+query_cpu_metrics)/ logs(search_logs)/ _fixtures(故事线剧本:HighCPUUsage@data-sync-service,CPU爬升曲线,同步堆积日志——三者讲同一故事)
knowledge_docs/      5篇运维知识文档(cpu/disk/memory/service_unavailable/slow_response)
tests/unit + tests/integration(@integration标记,CI跳过)
Dockerfile + .dockerignore + docker-compose.yml(全栈容器化) + Procfile(honcho) + .github/workflows/ci.yml
```

## 开发

```bash
uv run pytest                      # 运行全部测试
uv run pytest -m "not integration" # 只运行单元测试
uv run pytest -m integration       # 只运行集成测试
uv run ruff format .               # 代码格式化
uv run ruff check .                # 代码检查
uv run ruff check --fix .          # 检查同时修复
```

## 里程碑进度

- [x] M0 仓库初始化(uv + ruff + pytest 工具链)
- [x] M1 配置与最小可运行服务(settings / 日志 / 应用工厂 / 健康检查 / 统一响应)
- [x] M2 向量层(嵌入 / Milvus 封装 / 文档分割 / 索引服务 / 上传接口)
- [x] M3 RAG 对话 Agent(ReAct 循环图 / 知识检索工具 / 多轮记忆 / 消息修剪 / 流式 SSE)
- [x] M4 Mock MCP 服务器(告警 / 指标 / 日志,故事线对齐 / 失败降级可恢复)
- [x] M5 AIOps 诊断图(Plan-Execute-Replan / 结构化决策 / 步数护栏 / 工具容错)
- [x] M6 前端与收尾(精简单页 Web:流式对话 / 一键诊断 / 文档上传)
