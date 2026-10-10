# Qdrant Nodes 与检索

## Node 与 Embedding

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- 默认独立 Collection rag_llama_index_nodes；官方 QdrantVectorStore 管理命名 Dense Vector、Cosine 与完整 Node payload（含 _node_content），不维护自定义序列化。
- Node 存完整文本、document_id、version、chunk_index、source_uri、title、heading_h1、heading_h2、start_line/end_line 及自定义 metadata；无 PG Chunk ID 依赖。
- EmbeddingRepository 注入 OllamaEmbedding Resource，使用 IngestionPipeline 转换 Nodes；默认 Metadata + 文本格式保留 title/H1/H2，其他 metadata 从 Embedding 输入排除。
- Query 使用同一 OllamaEmbedding；只传查询文本，无文档 Metadata。
- Collection 按首批向量真实维度建立，错误不静默降级。Collection 被删除后可用保存的原文件重新解析、切块、生成向量，不依赖 PG chunks。
- 写入用 Node ID 幂等覆盖；按文档删除用官方适配器 SOURCE/ref_doc_id 关联。并发首次创建在 Repository 内串行化。

## Chunk GET 与向量 Query

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- ChunkLookupService.listChunks(documentId)：Qdrant scroll 分页读取全部文档 Nodes，再按 chunk_index 排序。
- ChunkLookupService.getChunkDetail(chunkId)：按 Node ID 读取全量内容，不存在报 NotFound。
- 两种 GET 分别由 ListDocumentChunksUseCase 和 GetChunkDetailUseCase 提供，不计算 Embedding。
- VectorQueryService.query(text, top_k=5)：由官方 VectorStoreIndex Retriever 生成查询向量并取 Top-K。允许范围 1..10，保持 Qdrant 分数/排名，不做 PG 验证、回填、max_candidates 或 over-fetch。
- 不提供 Metadata Filter、Sparse、Hybrid、Reranker 或答案生成。

- Ollama 请求不传 num_gpu，由 Ollama 自动选择设备；keep_alive 为 5m。
