# 运行时与 Migration

## 运行环境与隔离

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- Python 3.13、uv、FastAPI、dependency-injector、SQLAlchemy Async ORM + psycopg、aio-pika。
- 使用锁定版本 LlamaIndex core/readers-file/embeddings-ollama/vector-stores-qdrant；移除 MarkItDown 与手写 Ollama HTTP 实现。
- Ollama 默认 qwen3-embedding:8b；向量维度来自真实 Embedding 响应，不硬编码。
- 只加载 .env.llama-index 与 RAG_LI_* 环境变量，不读取 main 的 .env。
- 新数据库 rag_llama_index、新 Collection rag_llama_index_nodes、新消息命名空间 rag.llama-index.indexing；不迁移旧数据、不清空旧服务。
- API 与 Worker 使用相同 storage_path；默认 statics/，Git 忽略且不公开挂载。

## Migration

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- SQLAlchemy Model 是运行时结构，Alembic 是唯一迁移工具，应用启动不自动 migration。
- 已共享初始 migration 保持原样；新 revision 20260930000000 只接受没有 documents 的数据库，删除空 chunks 表并将 content 替换为 file_path。
- 非空旧库明确拒绝，不自动回填、stamp 或 destructive reset。默认使用新库。
- forward-only；初始化用 uv run alembic upgrade head，结构核对用 uv run alembic check。
