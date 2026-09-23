# Qdrant 索引模型与检索回填

## Collection 与 Point 契约

> 变更批次：`26-09-24_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- 使用单个 Collection `rag_chunks`。
- Point 只包含 `id` 与一个 Dense Vector；`id` 必须等于 PostgreSQL `chunks.id`，Vector 类型为 `FLOAT32[embedding_dimension]`。
- Point 不保存 Payload，不复制正文、`document_id`、版本、`active` 或 Metadata。
- `embedding_dimension` 由配置的 Embedding 模型决定；模型没有特殊要求时距离度量使用 `Cosine`。
- 默认模型为本地 Ollama `qwen3-embedding:8b`；Collection 创建时以一次真实 Embed 响应的长度确定 `embedding_dimension`。
- Ollama Embed 请求不得固定 `num_gpu` 或其他设备选择参数，由 Ollama 自动调度运行设备；`keep_alive` 固定为 `5m`。当前不人为拆分 Chunk Embedding 批次，出现实际资源或超时问题后再单独定义批处理策略。
- 服务启动和 Worker 写入前必须校验现有 Collection 的向量维度和距离度量。配置不兼容时必须快速失败并要求显式重建，不得向不兼容 Collection 写入。

Qdrant 是派生索引。删除 Collection 或 Point 后，系统必须能仅根据 PostgreSQL 中的有效 Chunk 重新生成全部向量；不得从 Qdrant 反向恢复业务事实。

## Document Embedding 输入

> 变更批次：`26-09-21_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

Worker 为 Chunk 生成 Document Embedding 时，按 Markdown 结构依次拼接非空的 Document `title`、Chunk `metadata.heading` 和 Chunk `content`。若正文开头已包含相同二级标题，拼接时不得重复该标题。Document title 或 Section heading 不存在时必须自然退化为剩余内容；两者都不存在时 Embedding 输入等于清理首尾空白后的 `chunk.content`。

Query Embedding 只处理用户查询文本，不拼接 Document title、Section heading 或其他 Document Metadata。第一版不为 title 与 body 建立独立向量。

## 搜索与 PostgreSQL 回填

> 变更批次：`26-09-19_0`
> 变更来源：`improve-regulations`
> 落地状态：`已实现`
> 实现优先级：`P0`

1. 查询文本通过同一兼容 Embedding 模型生成 Query Vector。
2. Qdrant 只返回候选 `chunk_id` 和相似度 `score`。
3. Retrieval Service 按 ID 批量查询 PostgreSQL，只接受 `active = true`、所属 Document 为 `ready` 且 Chunk 版本等于 `documents.current_version` 的记录。
4. 回填结果必须恢复为 Qdrant 给出的顺序，并保留原始相似度分数；数据库返回顺序不得改变排名。
5. 找不到、已停用或版本过期的 Point 属于脏索引，必须从响应中排除并记录为可观测事件。

由于 Qdrant 没有 Payload 过滤，检索必须支持有界 over-fetch：过滤后不足请求的 Top-K 时继续取得候选，直到数量满足或达到配置的最大候选数。不得返回无效 Chunk 填满结果。

第一版只规范 Dense 检索。Sparse/BM25、RRF 和 Reranker 在后续学习阶段另行定义，当前实现不得提前把这些能力伪装成已支持。

验收条件：搜索响应中的每个 Chunk 都能在 PostgreSQL 中找到且满足有效版本规则；批量回填后排名和分数保持不变；注入孤儿或停用 Point 时不会泄漏到响应；Collection 配置不兼容时启动或写入明确失败。
