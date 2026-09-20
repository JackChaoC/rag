# 运行时与 Migration 策略

## Python 基础设施选型

> 变更批次：`26-09-20_0`
> 变更来源：`improve-regulations`
> 落地状态：`已实现`
> 实现优先级：`P0`

- 项目使用 Python 3.13 和 `uv` 管理 Python 依赖及命令。Python 3.14 不是当前支持的运行时，除非 MarkItDown 及其 Magika/ONNX Runtime 依赖链在 Windows 上经过真实 PDF 解析回归验证。
- HTTP 使用 FastAPI 与 Pydantic；PostgreSQL 运行时访问使用 SQLAlchemy 2.0 Async ORM，Psycopg 3 作为异步 PostgreSQL Driver。Repository 对上层隐藏 `AsyncSession`、SQLAlchemy 查询和事务边界，不得将 ORM Model 泄漏到 Core 或接口层。
- RabbitMQ 客户端使用 `aio-pika`；Qdrant 使用官方 `qdrant-client`；Ollama Embedding 使用 `httpx` 调用本地 HTTP API。
- 文档解析使用 `markitdown[pdf]`，第一版必须启用 `markdown`、`text` 与 `pdf`；其他已声明 `source_type` 在有对应依赖和测试前必须拒绝并返回明确错误。
- 应用配置通过环境变量加载，并至少包含 PostgreSQL DSN、RabbitMQ URL、Qdrant URL、Ollama URL、Embedding 模型、搜索候选上限、RabbitMQ Prefetch 与重试延迟。不得在源码中保存凭据。
- 本地默认 Ollama URL 为 `http://127.0.0.1:11434`，Embedding 模型为 `qwen3-embedding:8b`。实际向量维度必须通过真实 Embed 响应获得并用于校验 Qdrant Collection，不在代码中猜测或硬编码。

依赖不可连接、模型不存在、Embedding 返回空向量或向量维度变化时必须明确失败；不得以随机向量或静默降级代替真实 Embedding。

验收条件：`uv sync` 能在 Python 3.13 创建环境；SQLAlchemy Async Engine 能通过 Psycopg 3 连接 PostgreSQL；MarkItDown 能在 Windows 上导入并真实转换 PDF；配置缺失时错误指出具体变量；替身测试能替换所有外部客户端；真实 Ollama 测试记录模型名与实测维度。

## SQLAlchemy Model 与 Alembic Migration

> 变更批次：`26-09-20_0`
> 变更来源：`improve-regulations`
> 落地状态：`已实现`
> 实现优先级：`P0`

- SQLAlchemy 2.0 Declarative Model 是运行时映射和 Alembic Metadata 的产品来源，必须与 [`database/`](../database/index.md) 的目标 DDL 等价。
- Alembic 是唯一 migration 工具，配置由 Python 项目管理，Migration 保存在 `alembic/versions/`；项目不得要求 Node.js、npm、Prisma Schema 或 Prisma CLI 才能初始化数据库。
- 初始 Alembic Migration 必须能够在空 PostgreSQL 中一次成功建立目标结构，并保留 enum、check、foreign key、unique 和 index 约束。
- Migration 采用 forward-only 策略：已共享的 migration 不原地修改，修复通过新 migration 前进；不得自动对非空数据库执行 destructive reset。
- 本地一次性开发数据库可以由开发者显式重建；实现和测试不得连接或修改未由本项目配置明确指定的数据库。
- 部署和本地初始化使用 `uv run alembic upgrade head`；创建新 migration 使用 `uv run alembic revision --autogenerate -m <message>`。应用进程启动时不得自动执行 migration，生成 migration 文件不代表获得生产执行授权。
- 已由旧 Prisma 初始 migration 建表的数据库，只有在确认实际结构与 Alembic 初始 revision 等价后才允许显式 `stamp`；Alembic 不得自动猜测或接管未知 schema。

验收条件：Alembic 配置与 revision 可加载；`upgrade head` 能在空 PostgreSQL 应用；再次执行时无变化；`alembic current` 指向 head；数据库约束测试与规范 DDL 一致；仓库不再包含 Prisma 或 npm migration 工具链。
