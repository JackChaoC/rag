# 解析、清洗与切块 Pipeline

## 统一处理流程

> 变更批次：`26-09-21_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

适用于所有进入索引流程的原始文件，包括原生 Markdown 和普通文本。

1. `parser` 使用 Microsoft MarkItDown 将受支持输入统一转换为 Markdown，并尽量保留标题、列表、表格和链接结构。
2. `cleaner` 对 Markdown 进行确定性的清洗与规范化；相同输入和配置必须得到相同输出。
3. `chunker` 按 Markdown 结构生成有序 Chunk；同一文档版本的 `chunk_index` 必须从 `0` 连续递增。
4. 完整清洗后 Markdown 写入 `documents.content`，Chunk 文本与引用信息写入 `chunks`；文档正文和 Chunk 内容不得放入 RabbitMQ 消息。
5. 只有解析、清洗、切块和 PostgreSQL 保存全部成功后，才允许发布索引任务。

Markdown 只以合法二级标题 `## ` 作为 Section 边界；一级标题、三级及更深标题保留在所属 Section 中。首个二级标题之前的非空内容形成 preamble Section。每个 Section 默认按不超过 `1200` 字符生成 Chunk；超长内容优先按空行分隔的语义块与完整代码围栏拆分，再依次按行、句子和字符硬切兜底。第一版不生成 overlap。所有子 Chunk 的 `metadata.heading` 保存所属二级标题，`chunk_index` 在整个文档版本内连续递增。

`start_line` 和 `end_line` 使用从 `1` 开始、包含边界的 `documents.content` 行号；不能稳定定位时两者允许为空，不得伪造近似行号。`content_hash` 根据最终写入的完整 Markdown 计算，相同 Hash 的重复导入不得无故增加版本或重新生成向量。

MarkItDown 不得承担清洗、切块、Embedding 或检索职责。第一版启用 Markdown、普通文本和 PDF；PDF 是端到端验收使用的首个非 Markdown 格式。Word、Excel、PowerPoint 和 HTML 在补齐对应依赖与测试前必须明确拒绝；声明了枚举值不等于该格式已经启用。

任何解析或清洗失败必须终止当前操作，不发布 RabbitMQ 消息、不写入 Qdrant，并在 Document 的 `status` 与 `last_error` 中留下可诊断结果。不得留下当前版本的部分 Chunk 集合。

验收条件：至少一种非 Markdown 文件能完整进入 Pipeline；只有二级标题产生 Section 边界；超长 Section 的每个 Chunk 不超过 `1200` 字符并保留标题 Metadata 与准确行号；标题、列表或表格结构可在保存的 Chunk 中核查；重复输入产生稳定结果；解析失败不会产生消息或向量残留。

权威数据结构：[`documents.sql`](../database/documents.sql) 与 [`chunks.sql`](../database/chunks.sql)。
