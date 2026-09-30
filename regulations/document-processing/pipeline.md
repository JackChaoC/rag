# 文件读取与切块

## Worker Pipeline

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- UploadFileUseCase 只存原始 bytes；content_hash 为原始文件 SHA256。PDF 损坏等解析错误由 Worker 记录并重试，不在 API 做解析。
- ReaderService 输出 LlamaIndex Document：Markdown/TXT 直接读 UTF-8（允许 BOM），保留标题；PDF 使用官方 PDFReader，合并全文；统一换行并清除首尾空白，空文档失败。
- SplitterService 使用自定义 MarkdownNodeParser（继承 LlamaIndex NodeParser），内部迁入 main 的 chunk_markdown 算法。只按 H2 分 Section，默认 1200 字符上限、语义块/行/句子/字符兜底，不加入 overlap。
- 沿用 main 算法的既有边界行为，不借框架替换另行改变切分规则。
- 每个文件切好的 Nodes 按顺序赋予全局 chunk_index，从 0 连续递增；H1 取第一个非代码围栏中的一级标题，H2 取所属 Section 标题，存 heading_h1/heading_h2。
- Node ID 为 UUID5(document_id, version:chunk_index)，SOURCE relationship 指向 document_id。
- 系统字段覆盖同名上传 Metadata，不能让外部 metadata 覆盖 document_id、version、chunk_index、标题或引用位置。
- start_line/end_line 为 Reader 规范化文本的 1-based 闭区间行号，不代表 PDF 原始页码/坐标。
- 支持 Markdown/TXT/PDF；没有新增 Office 等格式。解析失败不写入新 Nodes；任务失败状态与终态清理由 Worker 契约定义。
