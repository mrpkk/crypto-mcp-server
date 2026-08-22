FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY tools/ ./tools/
COPY ai/ ./ai/
COPY chain/ ./chain/
COPY mcp_server.py api_server.py config.py main.py ./
RUN pip install --no-cache-dir .
EXPOSE 8080
# MCP-сервер по умолчанию (stdio); для HTTP API: docker run ... api_server
CMD ["python", "-m", "mcp_server"]
