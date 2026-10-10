# 系统边界与数据所有权

## LlamaIndex 分层与依赖注入

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- 保持 `api → use_cases → services → repositories → resources`；Use Case 之间不互相调用。
- LlamaIndex 作为各层实现工具，不设独立 LlamaIndex Container 或 integrations 目录。
- 类按职责加 Service、Repository、UseCase、Handler 后缀；provider 和注入实例使用完整 camelCase 名，如 fileService、fileRepository、uploadFileUseCase。
- containers/application.py 组装 Resources、Repositories、Services、UseCases、Worker 子容器。Resource 按实际外部服务命名为 `postgresql`、`qdrant`、`ollama`、`rabbitmq`；无请求状态 Repository/Service/Handler 用 Singleton；UseCase 和自定义 Parser 用 Factory。健康检查不建立独立 Repository，由 Health Service 组合各服务 Repository 提供的 `healthcheck()`。
- 业务类只使用普通构造注入，不导入 Depends、Provide 或 Container。HTTP 用 Depends(Provide)；MCP 显式解析同一组 UseCase provider；Worker Handler 只分派到 UseCase。
- 生命周期依次启动数据库、Qdrant、Ollama、Broker，逆序关闭；先停止消费并等待回调结束，再关闭底层资源。退出重置单例；测试可 override provider。
- 每个数据库操作持有自己的 session；跨进程文档锁用独立 NullPool engine，避免锁等待占满 CRUD 池。

## 数据流与所有权

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- API 上传只存原始文件和 File 管理记录；创建文档接口引用已上传文件、保存 Document 并发布任务，不解析、不切块、不生成 Embedding。
- 文件位于 statics/，不对外静态挂载；API/Worker 必须共享同一存储根路径。
- Worker 调用 ReaderService、SplitterService、EmbeddingService、VectorService 完成索引。
- PG 管理 File 的文件名、路径、类型、大小、哈希，以及 Document 的文件关联、标题、团队、项目、描述、操作人、版本、状态，不保存全文或 Chunk 表。
- Qdrant 用官方 Node 格式保存完整 Chunk、Metadata 和向量。搜索及 Chunk GET 不回 PG 验证或回填。
- 更新允许旧结果暂时不可搜索；不实现原子双版本切换，索引过程中可能看见部分新 Nodes。
- FileService 封装 FileRepository（文件存储）和 FileRecordRepository（数据库文件记录）；EmbeddingService 封装使用 OllamaEmbedding 的 EmbeddingRepository；VectorService/ChunkLookupService/VectorQueryService 使用 VectorRepository。
- RAG 不生成答案；保持 HTTP、MCP 和现有前端入口。不开通 URL 抓取、认证、多租户、Metadata Filter 或新文件类型。
- 数据库、文件、Broker 与 Qdrant 不是分布式事务；本分支不增加 Outbox 或崩溃后孤儿文件自动清扫。

## 进程入口

> 变更批次：`26-09-30_0`
> 变更来源：`implement-regulations`
> 落地状态：`已实现`

- `uv run rag`：FastAPI/Uvicorn，/v1、/health、/docs、/mcp、/ui。
- `uv run rag-worker`：rag.worker.worker:main，主文件仍叫 worker.py。
- 每个进程有独立容器，共享外部服务与文件目录。

- 原文件属于 files，删除文档或替换文件不删除独立上传记录或原始 bytes，避免破坏其他引用。旧文档迁移建立 files 关联，保留文件位置；历史缺失标题回填原文件名。
