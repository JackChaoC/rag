# Local RAG service

Python 3.13 service for parsing documents, storing facts in PostgreSQL, indexing
chunks asynchronously through RabbitMQ and Ollama, and searching vectors in
Qdrant. The service exposes the same read operations through FastAPI and MCP.

## Local setup

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
```

The default embedding model is `qwen3-embedding:8b`. Install it in Ollama and
keep Ollama available at `http://127.0.0.1:11434`.

Start the HTTP/MCP process and the indexing worker in separate terminals:

```bash
uv run rag
uv run rag-worker
```

The browser console is available at `http://127.0.0.1:8000/ui/`, Swagger at
`http://127.0.0.1:8000/docs`, and the Streamable HTTP MCP endpoint at
`http://127.0.0.1:8000/mcp`.

## Verification

Fast tests use controlled substitutes and do not require local services:

```bash
uv run pytest -q
```

The integration suite requires PostgreSQL, RabbitMQ, Qdrant, and Ollama. It
includes a real PDF-to-vector flow and records the detected embedding dimension:

```bash
RUN_RAG_INTEGRATION=1 uv run pytest -q -s
```
