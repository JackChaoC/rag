## 后续实施说明

2026-09-24：项目已采用 dependency-injector 统一装配 HTTP、MCP 与 Worker。
本文保留当时的调研结论；其中手写 Container、getter 和
`app.dependency_overrides` 的实施建议已由声明式 providers 与 provider override 取代。
当前实现以 `src/rag/containers/` 中的分层子容器及架构规范为准。

## FastAPI 工程化与依赖注入调研

调研日期：2026-09-23

问题：本项目是否应该使用 `Depends`，以及应该参考哪一种成熟 FastAPI 工程结构。

结论先行：**应该使用 `Depends`，但只把它当作 HTTP 边界的依赖解析器，而不是让它侵入整个业务系统。** 本项目适合采用“显式 Composition Root + FastAPI Provider”的混合方式：Lifespan 创建和释放进程级资源，Provider 从应用资源中暴露具体 Use Case，Router 只依赖自己使用的 Use Case；`core`、`use_cases` 和 `infrastructure` 不导入 FastAPI。现阶段不需要引入第三方 DI Container。

## 调研范围与可信度

只使用一手来源：FastAPI 官方文档和项目官方 GitHub 仓库源码。

| 项目 | 定位 | 研究价值 | 时效性说明 |
|---|---|---|---|
| [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | FastAPI 官方组织维护的全栈模板 | 小到中型项目的基线 | 活跃；结构简洁，但不是 Clean Architecture 范例 |
| [Netflix/dispatch](https://github.com/Netflix/dispatch) | Netflix 的大型事件管理应用 | 按业务功能拆分、Router/Service 分离的历史案例 | **已于 2025-09-03 归档**，只能参考结构，不能照搬生命周期和测试方案 |
| [langflow-ai/langflow](https://github.com/langflow-ai/langflow) | 大型、活跃的 FastAPI AI 应用 | Lifespan、服务管理器、依赖覆盖和复杂资源边界 | 活跃，但复杂度远高于本项目，不应整体复制 |

FastAPI 官方确认：依赖可以形成任意深度的依赖图，同一请求内默认缓存重复的子依赖；官方也把 `APIRouter`、Router 级 dependencies 和 `app.dependency_overrides` 作为标准组织与测试机制。参见 [Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)、[Sub-dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/)、[Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) 和 [Testing Dependencies with Overrides](https://fastapi.tiangolo.com/advanced/testing-dependencies/)。

## 证据：FastAPI 官方建议的职责边界

- `Depends` 的原生用途包括共享逻辑、数据库连接、认证和授权；依赖函数也可以有子依赖。[官方依赖文档](https://fastapi.tiangolo.com/tutorial/dependencies/)
- 同一个子依赖在一次请求中被多处需要时，默认只解析一次并复用结果；只有显式设置 `use_cache=False` 才重复执行。[官方子依赖文档](https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/)
- `APIRouter` 用于把同一 FastAPI 应用拆成多个模块；认证等“执行即可、不需要返回值”的依赖可放在 Router 或 `include_router()` 层级。[官方大型应用文档](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- 需要跨请求共享且必须清理的资源，例如连接池或模型，应由 `FastAPI(lifespan=...)` 在启动时创建、关闭时释放。[官方 Lifespan 文档](https://fastapi.tiangolo.com/advanced/events/)
- 测试可以使用 `app.dependency_overrides[原依赖] = 替代依赖`，并且原依赖的子依赖不会执行。[官方测试覆盖文档](https://fastapi.tiangolo.com/advanced/testing-dependencies/)

以上是框架能力，不是强制架构。FastAPI 没有 NestJS `Module/Provider` 或 Spring Bean 那样的统一应用容器，因此项目必须自行规定边界。

## 证据：full-stack-fastapi-template

该模板采用“Router + `deps.py` + 薄量 CRUD”结构：

- [`api/deps.py`](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/api/deps.py) 用 `Annotated[..., Depends(...)]` 定义 `SessionDep`、`TokenDep`、`CurrentUser`。它把请求级数据库 Session、认证和授权放在 HTTP 依赖图里。
- [`api/main.py`](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/api/main.py) 只负责聚合各功能 Router；[`main.py`](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/main.py) 创建应用、配置 Middleware、挂载 Router。
- [`routes/items.py`](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/api/routes/items.py) 直接使用 `SessionDep` 执行简单查询；复杂的用户逻辑则抽到 [`crud.py`](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/crud.py)。它没有 Repository 接口，也没有第三方 DI Container。
- [`tests/conftest.py`](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/tests/conftest.py) 使用真实测试数据库和全局 App，没有展示 `dependency_overrides`；这是一种集成测试取向，而不是本项目必须复制的做法。

判断：值得借鉴其 `Annotated` 依赖别名、Router 聚合和小型 `main.py`；不应照搬“Route 直接写数据库查询”，因为本项目已经有明确 Use Case 和 Repository 边界。

## 证据：Netflix Dispatch

Dispatch 是成熟的大型历史案例，但仓库已经归档。其结构更接近按功能组织：每个业务目录含 `views.py`、`service.py`、`models.py`。

- [`tag/views.py`](https://github.com/Netflix/dispatch/blob/main/src/dispatch/tag/views.py) 负责 HTTP、错误映射和调用 Service；[`tag/service.py`](https://github.com/Netflix/dispatch/blob/main/src/dispatch/tag/service.py) 负责数据库业务操作。这说明大型 FastAPI 项目通常不会把所有路由堆进 `app.py`。
- [`database/core.py`](https://github.com/Netflix/dispatch/blob/main/src/dispatch/database/core.py) 定义 `DbSession = Annotated[Session, Depends(get_db)]`，但 `get_db()` 从 `request.state.db` 取 Session。
- [`main.py`](https://github.com/Netflix/dispatch/blob/main/src/dispatch/main.py) 的 Middleware 为每个请求创建、提交/回滚并关闭数据库 Session，再放入 `request.state`。它还在模块导入时创建并挂载多个 FastAPI App，没有现代 App Factory + Lifespan 结构。
- [`api.py`](https://github.com/Netflix/dispatch/blob/main/src/dispatch/api.py) 在 Router 聚合层统一添加组织上下文、当前用户和权限依赖，体现了“横切规则放 Router 层”的用法。
- [`tests/conftest.py`](https://github.com/Netflix/dispatch/blob/main/tests/conftest.py) 主要通过真实测试数据库、事务回滚和插件替身测试，没有依赖覆盖体系。

判断：值得借鉴“按功能放置 Router/Service/Model”和 Router 级认证；不要借鉴其数据库 Session Middleware、模块导入副作用和测试数据库管理方式。它更像 FastAPI 早期的大型实践，不是 2026 年的新项目模板。

## 证据：Langflow

Langflow 展示了复杂系统的混合方案：FastAPI `Depends` 负责请求级依赖，同时自有 Service Manager 管理共享服务。

- [`main.py`](https://github.com/langflow-ai/langflow/blob/main/src/backend/base/langflow/main.py) 提供 `create_app()`，并通过 `get_lifespan()` 初始化和拆除服务、后台任务及临时资源；这是 App Factory + Lifespan 的明确案例。
- [`api/utils/core.py`](https://github.com/langflow-ai/langflow/blob/main/src/backend/base/langflow/api/utils/core.py) 用 `CurrentActiveUser`、`DbSession`、`DbSessionReadOnly` 等 `Annotated` 别名表达 HTTP 依赖。它还刻意区分写 Session 的 function scope 与只读 Session 的 request scope，说明 Session 的提交与关闭时机属于请求边界设计。
- [`services/deps.py`](https://github.com/langflow-ai/langflow/blob/main/src/backend/base/langflow/services/deps.py) 通过 Provider 函数从自有 Service Manager 获取 Storage、Cache、Task、Telemetry 等长生命周期服务；[`api/v2/files.py`](https://github.com/langflow-ai/langflow/blob/main/src/backend/base/langflow/api/v2/files.py) 再用 `Depends(get_storage_service)` 注入具体服务。
- [`test_log_router.py`](https://github.com/langflow-ai/langflow/blob/main/src/backend/tests/unit/api/test_log_router.py) 创建最小 FastAPI App，只挂载被测 Router，并用 `dependency_overrides` 替换认证依赖；[`test_model_provider_policy.py`](https://github.com/langflow-ai/langflow/blob/main/src/backend/tests/unit/api/v1/test_model_provider_policy.py) 同时替换认证和数据库 Session Provider。

判断：值得借鉴 App Factory、Lifespan、具体 Service Provider、最小 Router 测试和依赖覆盖。不要复制其全局 Service Manager：那是大型插件化系统为多类服务、工厂和运行模式付出的复杂度；对当前 RAG 服务会形成新的 Service Locator。

## 横向比较

| 关注点 | full-stack template | Dispatch | Langflow | 本项目应选 |
|---|---|---|---|---|
| `Depends` 边界 | Session、认证、授权 | Session 访问、认证、权限 | Session、认证、具体共享 Service | HTTP 边界中的 Session/认证/Use Case Provider |
| Router 与业务分离 | 部分；简单 CRUD 仍在 Route | `views.py` 调 `service.py` | Router + 多层 Service | Router 只做协议转换并调用 Use Case |
| Repository | 无独立接口层 | Service 直接操作 ORM | 按子系统而异 | 保留现有 Repository |
| App Factory | 无，模块级 App | 无，模块级多个 App | 有 `create_app()` | 保留并简化 `create_app()` |
| 资源生命周期 | 模块级 Engine | Middleware 管请求 Session | Lifespan 管共享服务 | Lifespan 管 DB pool、Broker、Qdrant、HTTP client |
| 测试替换 | 真实测试 DB 为主 | 真实测试 DB/事务为主 | `dependency_overrides` 很明确 | Unit/契约测试使用 overrides；另留少量真实集成测试 |
| 第三方/自有 DI Container | 无 | 无 | 自有 Service Manager | 暂不需要 |

## 对当前 RAG 仓库的证据判断

调研时的 `container.py` 集中创建 Database、RabbitMQ、Qdrant、Embedder、Repository 和 Use Case，作为 Composition Root 的方向是合理的；问题是其 `start()` 动态添加 `ingest`、`search` 等属性，对象在启动前并不完整，存在调用顺序耦合。该历史实现已被分层子容器取代。

当前 [`interfaces/http/app.py`](../src/rag/interfaces/http/app.py) 同时负责 App 生命周期、异常处理、全部 HTTP 路由、DTO 转换、Health Check、静态文件和 MCP 挂载；而 [`routes/documents.py`](../src/rag/interfaces/http/routes/documents.py) 与 [`routes/search.py`](../src/rag/interfaces/http/routes/search.py) 为空。路由又通过闭包直接访问完整 `container`，所以任何 Route 都能取得所有基础设施和 Use Case。这是当前“依赖传递很乱”的主要原因，不是 `Depends` 本身造成的。

当前 [`tests/interfaces/test_contracts.py`](../tests/interfaces/test_contracts.py) 通过构造 `FakeContainer` 替换整个对象图，测试可运行，但替身必须模仿整个 Container 的形状。随着功能增加，它会越来越脆弱；替换路由实际需要的单个 Use Case 会更精确。

## 推荐架构

建议采用下列依赖方向：

```text
FastAPI lifespan
  └── AppResources（DB pool、Broker、Qdrant、Embedder）

HTTP Router
  └── Depends(get_ingest_document)
        └── IngestDocument
              ├── DocumentRepository
              └── Broker publisher

Use Case / Core / Repository
  └── 不导入 FastAPI，不读取 Request，不调用 Depends
```

具体约束：

1. `Depends` 只出现在 `interfaces/http/`：注入请求级 Session、身份/权限、Use Case，或者执行 Router 级 guard。
2. Router 参数依赖具体能力，例如 `IngestDocumentDep`、`SearchKnowledgeDep`，禁止注入整个 `Container` 或让 Route 直接读取 `app.state.container`。
3. Lifespan 只拥有需要启动/关闭的进程级资源；Repository 和 Use Case 可以在资源就绪后一次组装，也可以由无副作用 Provider 按请求轻量构造。
4. `Container` 若保留，应成为内部 Composition Root，而不是 Service Locator。将动态属性改为显式、可类型检查的字段或独立 `build_services(resources)` 返回值。
5. `app.py` 只保留 App Factory、Middleware、异常处理、Router/MCP 挂载；Documents、Search、Health 各自放入 Router 模块。
6. 业务异常继续由全局 exception handlers 转换为 HTTP；Use Case 不抛 `HTTPException`。
7. Router 单元/契约测试创建 App 后使用 `dependency_overrides[get_search_knowledge] = fake_provider`；真实 PostgreSQL、RabbitMQ、Qdrant 测试继续留在 integration test。

## 推荐的最小 Provider 形态

```python
from typing import Annotated

from fastapi import Depends, Request


def get_services(request: Request) -> ApplicationServices:
    return request.app.state.services


ServicesDep = Annotated[ApplicationServices, Depends(get_services)]


def get_search_knowledge(services: ServicesDep) -> SearchKnowledge:
    return services.search_knowledge


SearchKnowledgeDep = Annotated[
    SearchKnowledge,
    Depends(get_search_knowledge),
]
```

Router 只声明自己需要的 Use Case：

```python
@router.post("/search", response_model=list[SearchItem])
async def search(
    body: SearchRequest,
    use_case: SearchKnowledgeDep,
) -> list[SearchItem]:
    result = await use_case.execute(body.query, body.top_k)
    return [SearchItem.model_validate(item) for item in result]
```

测试只覆盖这一条依赖：

```python
app.dependency_overrides[get_search_knowledge] = lambda: FakeSearchKnowledge()
```

这里的 `ApplicationServices` 不传给 Route；它只藏在 Provider 层作为 Composition Root 的结果。这样既利用 FastAPI 的测试覆盖和请求依赖图，也不会把 FastAPI 变成业务层的全局容器。

## 最终建议

本项目应该使用 `Depends`，实施优先级如下：

1. 先把现有路由从 `app.py` 移入 `documents.py`、`search.py`、`health.py`。
2. 为每个公开 Use Case 增加具体 Provider 和 `Annotated` 别名。
3. Lifespan 管资源，Provider 暴露能力，Route 不再闭包捕获整个 Container。
4. 把 HTTP 契约测试改为 `dependency_overrides`，保留现有集成测试覆盖真实资源。
5. 暂不引入 Dishka、Dependency Injector 等第三方容器；只有出现多个 Scope、插件式 Provider 注册或大量条件绑定后再重新评估。

最接近本项目目标的不是完整复制某一个仓库，而是组合三者的优点：采用 full-stack template 的简洁 `Annotated` Provider 和 Router 聚合，采用 Dispatch 的按功能 Router/Service 分离，采用 Langflow 的 App Factory、Lifespan 和依赖覆盖测试；同时保留本项目已经存在的 Use Case/Repository 分层。
