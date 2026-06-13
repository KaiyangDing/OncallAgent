# OnCall Agent

智能 OnCall 运维助手:RAG 知识库问答 + AIOps 自动故障诊断(Plan-Execute-Replan)。

> 项目按里程碑逐步重写中,本文档只描述**已实现**的内容。

## 技术栈

- Python 3.13 + [uv](https://docs.astral.sh/uv/)
- FastAPI + LangGraph(原生 StateGraph)+ 通义千问(DashScope)
- Milvus 向量数据库 + MCP 工具协议

## 开发环境

```bash
uv sync               # 创建虚拟环境并安装全部依赖(含 dev)
cp .env.example .env  # 填入 DASHSCOPE_API_KEY
uv run pytest         # 运行测试
uv run ruff check .   # 代码检查
uv run ruff format .  # 代码格式化
```

PyCharm 用户:将解释器指向 `.venv\Scripts\python.exe`。

## 依赖服务

向量库 Milvus 通过 Docker 启动:

```bash
docker compose up -d   # 启动 Milvus(数据持久化到 volumes/)
docker compose down    # 停止
```

## 运行服务

```bash
uv run uvicorn oncall_agent.main:app --reload
```

- 健康检查:http://127.0.0.1:8000/health
- API 文档:http://127.0.0.1:8000/docs

## 知识库

`knowledge_docs/` 存放运维知识文档(Markdown)。通过上传接口建立向量索引:

```bash
curl.exe -X POST "http://127.0.0.1:8000/api/documents" -F "file=@knowledge_docs/cpu_high_usage.md"
```

文档经「按标题分割 → 字符递归切分 → 同章节小块合并」切块,嵌入后写入 Milvus。

## 对话

基于手搭的 LangGraph ReAct 循环图(model ↔ tools),支持知识库检索、多轮记忆与流式输出:

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

## 里程碑进度

- [x] M0 仓库初始化(uv + ruff + pytest 工具链)
- [x] M1 配置与最小可运行服务(settings / 日志 / 应用工厂 / 健康检查 / 统一响应)
- [x] M2 向量层(嵌入 / Milvus 封装 / 文档分割 / 索引服务 / 上传接口)
- [x] M3 RAG 对话 Agent(ReAct 循环图 / 知识检索工具 / 多轮记忆 / 消息修剪 / 流式 SSE)
- [ ] M4 Mock MCP 服务器与工具接入
- [ ] M5 诊断图(Plan-Execute-Replan)
- [ ] M6 前端适配与收尾
