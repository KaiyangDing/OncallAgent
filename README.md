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
uv run pytest         # 运行测试
uv run ruff check .   # 代码检查
uv run ruff format .  # 代码格式化
```

PyCharm 用户:将解释器指向 `.venv\Scripts\python.exe`。

## 里程碑进度

- [x] M0 仓库初始化(uv + ruff + pytest 工具链)
- [ ] M1 配置与最小可运行服务
- [ ] M2 向量层(知识库管线)
- [ ] M3 RAG 对话 Agent
- [ ] M4 Mock MCP 服务器与工具接入
- [ ] M5 诊断图(Plan-Execute-Replan)
- [ ] M6 前端适配与收尾
