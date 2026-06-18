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

> 也可单独启动某进程,如 `uv run uvicorn oncall_agent.main:create_app --factory,uv run python -m mcp_servers.logs_server,uv run python -m mcp_servers.monitor_server。
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
├── api/            接口层:health / documents / chat / diagnosis 路由,统一响应契约
├── domain/         业务层
│   ├── knowledge/  文档分割、索引、检索
│   ├── chat/       ReAct 对话图、工具、会话服务
│   └── diagnosis/  Plan-Execute-Replan 诊断图各节点
├── infra/          基础设施:llm / milvus / embeddings / mcp
├── main.py         应用工厂 + lifespan(资源装配)
├── settings.py     配置(pydantic-settings)
└── dependencies.py 依赖注入容器
mcp_servers/        独立运行的 Mock MCP 服务器(告警/指标/日志)
knowledge_docs/     运维知识库种子文档
tests/              单元测试
```

## 开发

```bash
uv run pytest         # 运行测试
uv run ruff check .   # 代码检查
uv run ruff format .  # 代码格式化
```

## 里程碑进度

- [x] M0 仓库初始化(uv + ruff + pytest 工具链)
- [x] M1 配置与最小可运行服务(settings / 日志 / 应用工厂 / 健康检查 / 统一响应)
- [x] M2 向量层(嵌入 / Milvus 封装 / 文档分割 / 索引服务 / 上传接口)
- [x] M3 RAG 对话 Agent(ReAct 循环图 / 知识检索工具 / 多轮记忆 / 消息修剪 / 流式 SSE)
- [x] M4 Mock MCP 服务器(告警 / 指标 / 日志,故事线对齐 / 失败降级可恢复)
- [x] M5 AIOps 诊断图(Plan-Execute-Replan / 结构化决策 / 步数护栏 / 工具容错)
- [x] M6 前端与收尾(精简单页 Web:流式对话 / 一键诊断 / 文档上传)
