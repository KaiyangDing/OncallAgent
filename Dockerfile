# 基于官方 Python 3.13 slim 镜像(slim = 精简版,体积小)
FROM python:3.13-slim

# 装 uv(用官方提供的方式,从 uv 镜像里复制二进制)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 设置工作目录
WORKDIR /app

# 先只复制依赖声明文件,利用 Docker 层缓存
# (依赖没变时,这层缓存复用,不用每次重装依赖)
COPY pyproject.toml uv.lock README.md ./

# 安装依赖(--frozen 用 lock 文件精确版本,--no-dev 不装开发依赖)
RUN uv sync --frozen --no-dev --no-install-project

# 复制项目代码
COPY src/ ./src/
COPY mcp_servers/ ./mcp_servers/
COPY static/ ./static/

# 安装项目本身
RUN uv sync --frozen --no-dev

# 默认启动命令(主应用;MCP 在 compose 里覆盖 command)
CMD ["uv", "run", "uvicorn", "oncall_agent.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]