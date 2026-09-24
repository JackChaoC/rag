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

## Dependency injection

`src/rag/containers/application.py` assembles the shared dependency graph using
`dependency-injector`. Each HTTP/MCP process and worker owns a separate container.
Configuration comes from the existing Pydantic `Settings`; connections use
`Resource` providers. Stateless repositories, retrieval services, use cases and
worker handlers use container-local `Singleton` providers. The parser and its
Ingest/Reindex owners remain `Factory` providers to avoid sharing MarkItDown
across parsing threads. The health HTTP client is also a `Factory`, since each
probe closes its client.

The container package follows the dependency layers:

```text
containers/
├── application.py    # composition root
├── resources.py      # external clients and lifecycle
├── repositories.py   # depends on resources
├── core.py           # depends on repositories and resources
├── use_cases.py      # HTTP/MCP application operations
└── worker.py         # parallel top layer: handlers and dispatcher
```

Subcontainers declare lower-layer dependencies explicitly. Use cases and worker
handlers share the same resource/repository providers and do not depend on each
other.

HTTP routes use `@inject` with
`Depends(Provide[ApplicationContainer.use_cases.…])`. MCP receives
the three use-case providers explicitly and resolves them when a tool is called.
The worker resolves its dispatcher and failure handler from the same container.
Business classes retain ordinary constructor arguments and do not import the
container or injection framework.

`src/rag/containers/resources.py` manages startup and reverse-order cleanup, including
partial startup failures. The broker stops consumption and drains in-flight
callbacks before the remaining clients are closed. Repository methods continue
to own their individual database sessions.

Tests replace dependencies using
`with container.repositories.documents.override(fake):` or
`with container.use_cases.search_knowledge.override(fake):`.
Override dependencies before resolving singleton consumers; if already resolved,
use `container.reset_singletons()` before resolving them again. Lifecycle exit
also resets singleton caches so restarting resources cannot retain old clients.
Async provider resolution uses `await resolve(container.worker.dispatcher)`, which
also supports synchronous test overrides. HTTP wiring is module-scoped: use one
active wired app per process and unwire its container after tests/lifespan exit.

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
