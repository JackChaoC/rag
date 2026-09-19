# PostgreSQL 数据模型

本分类是保留的 table 架构目录，只定义 PostgreSQL 目标表结构。`prisma/schema.prisma` 是产品实现中的可执行表结构来源，必须与这里的目标约束保持一致。

## 表定义

| 文件 | 拥有的表 |
|---|---|
| [`documents.sql`](documents.sql) | `documents` |
| [`chunks.sql`](chunks.sql) | `chunks` |

本分类不定义 ORM 使用方式、事务流程、migration、回填、连接池、消息发布或部署命令。

