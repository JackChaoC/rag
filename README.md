# Local RAG service — llama-index

Python 3.13 + FastAPI/MCP. HTTP uploads store raw files; RabbitMQ workers read,
split and embed them using LlamaIndex. PostgreSQL stores document management
data only. Qdrant stores complete Nodes, metadata and vectors.

## Run locally

```bash
uv sync
docker compose up -d
# Create this branch's NEW database once (skip if already created):
docker compose exec postgres createdb -U rag rag_llama_index
uv run alembic upgrade head
uv run rag
# Separate terminal, same working directory / storage path:
uv run rag-worker
```

Compose is unchanged from main; create the additional database explicitly.
Do not recreate an existing container to rename its database. The initial LlamaIndex migration requires an empty database; the later file/document migration preserves existing LlamaIndex documents and file paths.
The historical initial migration remains intact; the new revision removes the
empty chunks table and replaces document content with a file path.

Ollama must be running at `http://127.0.0.1:11434` with `qwen3-embedding:8b`.
Copy `.env.example` to `.env.llama-index` if configuration is needed.
Only `RAG_LI_*` environment variables and `.env.llama-index` are loaded:
main's `.env` is intentionally ignored.

Defaults isolate the branch:

- Database: `rag_llama_index`.
- Collection: `rag_llama_index_nodes`, lazily created using the actual embedding dimension.
- RabbitMQ namespace: `rag.llama-index.indexing`.
- Files: `statics/<file UUID>/1.<extension>` (legacy paths are retained); not publicly mounted.
  API and worker must share this directory.

Console: http://127.0.0.1:8123/ui/ · Swagger: http://127.0.0.1:8123/docs ·
MCP: http://127.0.0.1:8123/mcp

Use `uv run rag expose=true` to listen on `0.0.0.0:8123` for LAN access.
The default (`uv run rag` or `uv run rag expose=false`) listens only on localhost.
This exposes HTTP APIs, MCP and the UI together; configure authentication and network access controls before sharing sensitive data.

## Architecture

Business classes use explicit constructor injection and suffixes such as
`FileService`, `FileRepository`, `UploadFileUseCase`; providers and injected
instances use `fileService`, `fileRepository`, `uploadFileUseCase`.

`containers/` assembles resources → repositories → services → use cases;
worker handlers delegate to use cases. There is no LlamaIndex container or
integration layer. HTTP alone uses FastAPI Depends. MCP resolves the same
use-case providers explicitly.

- `UploadFileUseCase`: store raw bytes and a file record; return a file URL.
- `IngestDocumentUseCase`: resolve that URL, create the document, confirm publication.
- `IndexDocumentUseCase`: ReaderService → SplitterService → EmbeddingService →
  VectorService. Worker owns this processing.
- `ReaderService`: Markdown/TXT retain heading markers; PDF uses LlamaIndex PDFReader.
- `MarkdownNodeParser`: implements LlamaIndex NodeParser using main's H2/1200-character
  chunking algorithm unchanged. H1/H2 become metadata; global chunk_index starts at 0.
- `EmbeddingRepository`: official OllamaEmbedding through IngestionPipeline.
- `VectorRepository`: official QdrantVectorStore serialization and Retriever.
- `ChunkLookupService`: list chunks by document; get full detail by chunk ID.
- `VectorQueryService`: text query + optional top_k (default 5, range 1..10).
  No PostgreSQL hydration/validation or candidate over-fetch.

Node IDs are UUID5(document ID, version:chunk_index). Qdrant stores full text,
source association, document_id, version, chunk_index, file_url, title, team, project, description, operator,
heading_h1/heading_h2 and line ranges. Only title and headings participate in
default metadata-plus-text embedding; technical/user metadata remains available
but is excluded from embedding. Line ranges refer to the normalized reader text,
not PDF page coordinates.

## API compatibility and update behavior

Existing HTTP routes, MCP tools and frontend remain available. Two HTTP reads are added:

- `GET /v1/documents/{document_id}/chunks`: ordered chunk list.
- `GET /v1/chunks/{chunk_id}`: full chunk detail.

The existing `GET /v1/documents/{document_id}/chunks/{chunk_id}` and MCP
`get_document_chunk(document_id, chunk_id)` still check Node ownership without PG.

Upload supports Markdown, TXT and PDF. First call `POST /v1/files` with multipart
`file`; use its relative `url` as `file_url` in JSON `POST /v1/documents`.
`title` is required and nonblank. Optional fields: `team` (wallet, member, devops,
data, event), `project`, `description`, `operator`, and object `metadata`.
Source URI is removed. Only registered upload URLs are accepted; no remote fetching.

Open the file URL to view Markdown/TXT as plain text or PDF in the browser.
Append `?download=true` for an attachment download with the original filename.
The console uploads on selection and submits indexing after upload succeeds.

Repeating ingest with the same file URL and fields reuses the document.
Reindex takes optional JSON `file_url`, advances the version, deletes old Nodes,
and queues the new version. Uploaded files are retained on replacement/document deletion.
Search does not check PG status, so partial Nodes may be visible during writes.
Legacy titles are filled from filenames when absent; existing Nodes retain their vectors
and receive file links at read time without a re-embedding run.


Per-document PostgreSQL advisory locks serialize API/worker operations across
processes. Lock connections use a separate unpooled engine so waiting locks do
not exhaust the CRUD connection pool. Stale jobs do nothing; retries reuse Node
IDs. Terminal indexing failure cleans Nodes and records failed. Terminal delete
failure retains deleting + last_error to prevent old ingest jobs resurrecting it.

The DB/file/broker/Qdrant changes are not one transaction. Raw files are retained
for failed indexing retries; process crashes between file storage and DB writes
can leave orphan files. No outbox, automatic orphan sweeper, atomic version switch,
metadata-filter API, or additional file formats are introduced in this branch.

## Verification

```bash
uv run pytest -q
RUN_RAG_INTEGRATION=1 uv run pytest tests/integration -q -s
uv run alembic check
```

Integration tests require the new migrated database plus RabbitMQ/Qdrant/Ollama.
They create uniquely named test collections/queues and delete only those test
artifacts and test rows. Run against a dedicated test database: the rebuild test
queues documents from that database.

Detailed current contracts are in `regulations/`. Learning progress in
`target.md` is not advanced by this architecture refactor.

### Document query

`GET /v1/documents?q=account&team=member&status=ready` queries document summaries in PostgreSQL. `q` matches title, project, operator, team and document ID as a case-insensitive literal substring. Optional `team`, `status`, `project`, and `operator` filters match exactly and combine with AND. Blank text filters are ignored; no matches return `[]`. Omitting filters lists all documents. The console and MCP `list_documents` support the same filters; full-text semantic retrieval remains `/v1/search`.
