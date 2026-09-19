# RAG 项目规范索引

本目录定义后续实现必须满足的工程契约。[`target.md`](../target.md) 仍是学习阶段、推进顺序和验收目标的唯一来源；本目录只把当前阶段涉及的架构与行为整理为可实施、可验证的规则。

| 分类 | 路径 | 负责内容 | 明确不包含 |
|---|---|---|---|
| 架构与接口边界 | [`architecture/`](architecture/index.md) | 服务职责、依赖方向、跨组件数据所有权、运行时技术、HTTP/MCP 契约 | 表字段、消息拓扑细节、测试用例 |
| PostgreSQL 数据模型 | [`database/`](database/index.md) | PostgreSQL 表、列、约束、外键和索引的目标结构 | ORM、事务流程、migration 和运行时查询策略 |
| 文档解析与切块 | [`document-processing/`](document-processing/index.md) | MarkItDown、清洗、切块、引用位置和解析失败行为 | 消息投递、Embedding 与向量检索 |
| RabbitMQ 任务可靠性 | [`messaging/`](messaging/index.md) | Exchange、Queue、路由、确认、重试和死信 | Worker 业务状态转换和 PostgreSQL 表结构 |
| Worker 幂等与状态转换 | [`worker/`](worker/index.md) | Worker 操作顺序、版本防护、幂等和失败收敛 | Broker 拓扑和检索排序 |
| Qdrant 索引与检索 | [`vector-search/`](vector-search/index.md) | Collection、Point、向量配置、搜索与 PostgreSQL 回填 | 文档解析和答案生成 |
| 测试与验收 | [`quality/`](quality/index.md) | 自动化验证范围、失败场景和客观验收条件 | 生产实现与部署步骤 |

## 跨分类所有权

- PostgreSQL 表结构只由 [`database/`](database/index.md) 定义；其他分类只引用实体和字段语义。
- RabbitMQ 拓扑只由 [`messaging/`](messaging/index.md) 定义；Worker 分类只定义消费后的业务行为。
- Qdrant Point 与检索回填只由 [`vector-search/`](vector-search/index.md) 定义。
- 跨组件完整处理顺序由 [`architecture/system-boundaries.md`](architecture/system-boundaries.md) 定义，各组件内部细节归对应分类所有。
- HTTP 与 MCP 的公开契约由 [`architecture/service-contracts.md`](architecture/service-contracts.md) 定义。
- 数据库运行时和 migration 策略由 [`architecture/runtime-and-migrations.md`](architecture/runtime-and-migrations.md) 定义，table 目标结构仍只由 `database/` 拥有。
- 所有规则的验证要求汇总到 [`quality/acceptance.md`](quality/acceptance.md)，但被测行为仍由原分类拥有定义。
