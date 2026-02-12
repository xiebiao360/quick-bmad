---
name: api-design-principles
description: Master REST and GraphQL API design principles to build intuitive, scalable, and maintainable APIs that delight developers. Use when designing new APIs, reviewing API specifications, or establishing API design standards.
---

# API Design Principles

Master REST and GraphQL API design principles to build intuitive, scalable, and maintainable APIs that delight developers and stand the test of time.

## When to Use This Skill

- Designing new REST or GraphQL APIs
- Refactoring existing APIs for better usability
- Establishing API design standards for your team
- Reviewing API specifications before implementation
- Migrating between API paradigms (REST to GraphQL, etc.)
- Creating developer-friendly API documentation
- Optimizing APIs for specific use cases (mobile, third-party integrations)

## Core Concepts

### 1. RESTful Design Principles

**Resource-Oriented Architecture**
- Resources are nouns (users, orders, products), not verbs
- Use HTTP methods for actions (GET, POST, PUT, PATCH, DELETE)
- URLs represent resource hierarchies
- Consistent naming conventions

**HTTP Methods Semantics:**
- `GET`: Retrieve resources (idempotent, safe)
- `POST`: Create new resources
- `PUT`: Replace entire resource (idempotent)
- `PATCH`: Partial resource updates
- `DELETE`: Remove resources (idempotent)

### 2. GraphQL Design Principles

**Schema-First Development**
- Types define your domain model
- Queries for reading data
- Mutations for modifying data
- Subscriptions for real-time updates

**Query Structure:**
- Clients request exactly what they need
- Single endpoint, multiple operations
- Strongly typed schema
- Introspection built-in

### 3. API Versioning Strategies

**URL Versioning:**
```
/api/v1/users
/api/v2/users
```

**Header Versioning:**
```
Accept: application/vnd.api+json; version=1
```

**Query Parameter Versioning:**
```
/api/users?version=1
```

### 4. 微服务网关架构下的 URL 设计 (Microservices Gateway URL Design)

**核心原则：服务自治 + 路径简洁**

在微服务架构中，Gateway 应该作为透明代理，剥离服务前缀后将请求转发给微服务，让微服务内部路由保持简洁，无需重复服务名。

#### URL 结构规范

```
管理接口: /api/{service}/admin/{resource}
普通接口: /api/{service}/v1/{resource}
```

**关键设计决策**：
- `admin` 和 `v1` 是**版本/类型标识**，二选一，互斥使用
- Gateway 剥离 `/api/{service}` 前缀，仅转发 `/admin/{resource}` 或 `/v1/{resource}`
- 微服务内部路由简洁：`/admin/members`、`/v1/members`（无需包含服务名）
- 微服务通过路径前缀（`/admin/` vs `/v1/`）区分管理端点和普通端点

#### 完整请求流程示例

```
前端请求：GET /api/member/admin/members
         ↓
Gateway nest("/api/member")
         ↓ 剥离 /api/member
         ↓ 根据路径判断权限（/admin/ → Admin Auth）
         ↓ 转发剩余路径
Member 服务接收：GET /admin/members
         ↓
Member nest("/admin/members") 匹配
         ↓
Member Handler 执行
```

#### Gateway 实现（Axum）

```rust
use axum::{
    extract::{Request, State},
    middleware::{self, Next},
    response::Response,
    routing::any,
    Router,
    http::StatusCode,
};
use std::sync::Arc;

/// 认证类型
#[derive(Debug, Clone, Copy)]
pub enum AuthType {
    None,        // 公开路由（如登录）
    Normal,      // 普通认证（v1 路由）
    Admin,       // 管理员认证（admin 路由）
    PathBased,   // 根据路径判断（同时支持 admin 和 v1）
}

/// Gateway 路由配置（按服务分组）
fn create_gateway_routes() -> Router<Arc<AppConfig>> {
    Router::new()
        // 健康检查
        .route("/health", get(health_check))

        // 按服务分组的路由（每个服务一条）
        .nest("/api/member", create_service_route(handle_member, AuthType::PathBased))
        .nest("/api/merchant", create_service_route(handle_merchant, AuthType::PathBased))
        .nest("/api/trade", create_service_route(handle_trade, AuthType::PathBased))
        // ... 其他服务
}

/// 服务 Handler（使用剥离后的路径）
macro_rules! define_service_handler {
    ($fn_name:ident, $service_name:expr) => {
        async fn $fn_name(
            State(config): State<Arc<AppConfig>>,
            req: Request,
        ) -> Result<Response, ProxyError> {
            // ✅ 使用剥离后的路径（nest() 已剥离 /api/{service}）
            let uri = req.uri().clone();
            proxy_handler(req, uri, $service_name.to_string(), (*config).clone()).await
        }
    };
}

define_service_handler!(handle_member, "member");
define_service_handler!(handle_merchant, "merchant");
define_service_handler!(handle_trade, "trade");

/// 创建服务路由，应用认证中间件
fn create_service_route<H, T>(
    handler: H,
    auth_type: AuthType,
) -> Router<Arc<AppConfig>>
where
    H: axum::handler::Handler<T, Arc<AppConfig>> + Clone,
    T: 'static,
{
    let router = Router::new()
        .route("/", any(handler.clone()))      // 处理服务根路径
        .route("/*path", any(handler));        // 处理所有子路径

    // 应用认证中间件
    match auth_type {
        AuthType::PathBased => router.layer(middleware::from_fn(path_based_auth_middleware)),
        AuthType::Admin => router.layer(middleware::from_fn(admin_auth_middleware)),
        AuthType::Normal => router.layer(middleware::from_fn(normal_auth_middleware)),
        AuthType::None => router,
    }
}

/// 基于路径的认证中间件（同时支持 admin 和 v1）
async fn path_based_auth_middleware(
    req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    let path = req.uri().path();

    // 根据路径前缀判断认证类型
    if path.starts_with("/admin/") {
        admin_auth_middleware(req, next).await
    } else if path.starts_with("/v1/") {
        normal_auth_middleware(req, next).await
    } else {
        // 其他路径（如 /health）可能不需要认证
        Ok(next.run(req).await)
    }
}

/// 管理员认证中间件
async fn admin_auth_middleware(
    mut req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    use liangx_auth::JwtDecoder;

    // 提取 token
    let token = req
        .headers()
        .get("authorization")
        .and_then(|h| h.to_str().ok())
        .and_then(|h| h.strip_prefix("Bearer "))
        .ok_or(StatusCode::UNAUTHORIZED)?;

    // 验证 token
    let secret = std::env::var("JWT_SECRET")
        .unwrap_or_else(|_| "default-secret".to_string());
    let decoder = JwtDecoder::new(&secret);

    match decoder.decode(token) {
        Ok(claims) if claims.is_admin() => {
            // 传递用户上下文到微服务
            if let Ok(header_value) = claims.user_id().parse() {
                req.headers_mut().insert("X-User-Id", header_value);
            }
            req.headers_mut().insert("X-User-Role", "admin".parse().unwrap());

            Ok(next.run(req).await)
        }
        Ok(_) => Err(StatusCode::FORBIDDEN),
        Err(_) => Err(StatusCode::UNAUTHORIZED),
    }
}

/// 普通认证中间件（v1 路由）
async fn normal_auth_middleware(
    mut req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    // 类似的 token 验证逻辑，但不要求 admin 角色
    // ... 实现略
    Ok(next.run(req).await)
}

/// 代理转发处理器
pub async fn proxy_handler(
    req: Request,
    uri: Uri,  // 剥离后的 URI（如 /admin/members）
    service_name: String,
    config: AppConfig,
) -> Result<Response, ProxyError> {
    let service_url = config.get_service_url(&service_name)?;

    // 构建目标 URL（转发剥离后的路径）
    let path = uri.path();
    let query = uri.query().map(|q| format!("?{}", q)).unwrap_or_default();
    let target_url = format!("{}{}{}", service_url, path, query);

    tracing::info!(
        service = %service_name,
        forwarded_path = path,
        target = %target_url,
        "Proxying request"
    );

    // 转发请求到微服务
    // ... 实现略（使用 reqwest 等 HTTP 客户端）

    Ok(Response::new(Body::empty()))
}
```

#### 微服务路由实现（简洁版）

```rust
// services/member/src/api/routes.rs

use axum::{routing::{get, post}, Router};

pub fn create_router(
    member_handler: MemberHandler,
    // ... 其他 handlers
) -> Router {
    let member_routes = create_member_routes(member_handler);
    // ... 其他核心路由

    Router::new()
        // ========== 管理后台路由 ==========
        // Gateway 转发：/admin/members（已剥离 /api/member）
        .nest("/admin/members",
            member_routes.clone()
                .layer(axum::middleware::from_fn(extract_user_context))
        )
        .nest("/admin/enterprises",
            enterprise_routes.clone()
                .layer(axum::middleware::from_fn(extract_user_context))
        )

        // ========== 普通路由（V1）==========
        // Gateway 转发：/v1/members（已剥离 /api/member）
        .nest("/v1/members", member_routes.clone())
        .nest("/v1/enterprises", enterprise_routes.clone())

        // ========== 健康检查 ==========
        .route("/health", get(health_check))
}

/// 会员核心路由（无前缀，可复用）
fn create_member_routes(handler: MemberHandler) -> Router {
    Router::new()
        .route("/", get(MemberHandler::list).post(MemberHandler::register))
        .route("/:id", get(MemberHandler::get_by_id).put(MemberHandler::update))
        .route("/:id/freeze", post(MemberHandler::freeze))
        .with_state(handler)
}
```

#### 前端 API 调用

```typescript
// clients/admin-web/src/api/request.ts
const request = axios.create({
  baseURL: "/api",  // 注意：这里是 /api，不是 /api/admin
  timeout: 30000,
});

// clients/admin-web/src/api/member.ts
export const memberApi = {
  // 管理后台接口
  list: (params?: MemberListParams) =>
    request.get<unknown, MemberListResponse>("/member/admin/members", { params }),

  get: (id: string) =>
    request.get<unknown, Member>(`/member/admin/members/${id}`),

  create: (data: CreateMemberInput) =>
    request.post<unknown, Member>("/member/admin/members", data),
};

// 实际请求 URL：/api/member/admin/members
```

#### 设计优势

✅ **微服务路由简洁**：
- 无需在路由中重复服务名（`/admin/members` vs `/api/admin/member/members`）
- 符合"服务自治"原则

✅ **Gateway 配置简单**：
- 每个服务一条路由配置（N 个服务 → N 条路由）
- 无需为每个资源单独配置

✅ **权限控制清晰**：
- Gateway 统一鉴权（根据路径 `/admin/` vs `/v1/`）
- 微服务可二次校验（防御性编程）

✅ **扩展性强**：
- 服务内新增资源无需修改 Gateway
- 版本升级只需修改路径前缀（如 `/v2/`）

#### 常见错误

❌ **错误 1：微服务路由包含服务名**
```rust
// ❌ 错误
.nest("/api/admin/member/members", member_routes)

// ✅ 正确
.nest("/admin/members", member_routes)
```

❌ **错误 2：Gateway 不剥离前缀**
```rust
// ❌ 错误：转发完整原始路径
let target_url = format!("{}{}", service_url, original_uri.path());
// 结果：member:8002/api/member/admin/members

// ✅ 正确：转发剥离后的路径
let target_url = format!("{}{}", service_url, req.uri().path());
// 结果：member:8002/admin/members
```

❌ **错误 3：admin 和 v1 混用**
```rust
// ❌ 错误：同时包含 admin 和 v1
.nest("/api/member/admin/v1/members", ...)

// ✅ 正确：二选一
.nest("/admin/members", ...)  // 管理端点
.nest("/v1/members", ...)     // 普通端点
```

#### 与传统方案对比

| 维度 | 传统方案 | 本方案（推荐） |
|------|---------|---------------|
| **前端 URL** | `/api/admin/member/members` | `/api/member/admin/members` |
| **Gateway 转发** | `member:8002/api/admin/member/members` | `member:8002/admin/members` |
| **微服务路由** | `.nest("/api/admin/member/members", ...)` | `.nest("/admin/members", ...)` |
| **路由冗余** | ❌ 服务名重复 | ✅ 简洁 |
| **服务自治** | ❌ 依赖 Gateway 前缀 | ✅ 完全自治 |
| **Gateway 配置** | 每资源一条（N×M 条） | 每服务一条（N 条） |

## REST API Design Patterns

### Pattern 1: Resource Collection Design

```rust
// 优秀示例：面向资源的端点设计
use axum::{
    routing::{get, post, put, patch, delete},
    Router,
};

fn user_routes() -> Router {
    Router::new()
        // 用户资源集合路由
        .route("/api/users", get(list_users).post(create_user))
        .route(
            "/api/users/:id",
            get(get_user)
                .put(replace_user)      // PUT：完整替换
                .patch(update_user)     // PATCH：部分更新
                .delete(delete_user)
        )
        // 嵌套资源路由
        .route(
            "/api/users/:id/orders",
            get(get_user_orders).post(create_user_order)
        )
}

// ❌ 错误示例：面向动作的端点（应避免）
// POST   /api/createUser
// POST   /api/getUserById
// POST   /api/deleteUser
```

### Pattern 2: Pagination and Filtering

```rust
use axum::{extract::Query, Json};
use serde::{Deserialize, Serialize};

/// 分页查询参数
#[derive(Debug, Deserialize)]
pub struct ListUsersQuery {
    /// 页码（默认 1）
    #[serde(default = "default_page")]
    pub page: i64,
    /// 每页大小（默认 20，最大 100）
    #[serde(default = "default_page_size")]
    pub page_size: i64,
    /// 状态过滤
    pub status: Option<String>,
    /// 搜索关键词
    pub search: Option<String>,
    /// 创建时间过滤
    pub created_after: Option<String>,
}

fn default_page() -> i64 { 1 }
fn default_page_size() -> i64 { 20 }

/// 分页响应结构
#[derive(Debug, Serialize)]
pub struct PaginatedResponse<T> {
    pub items: Vec<T>,
    pub total: i64,
    pub page: i64,
    pub page_size: i64,
    pub pages: i64,
}

impl<T> PaginatedResponse<T> {
    pub fn new(items: Vec<T>, total: i64, page: i64, page_size: i64) -> Self {
        let pages = (total + page_size - 1) / page_size;
        Self { items, total, page, page_size, pages }
    }

    pub fn has_next(&self) -> bool {
        self.page < self.pages
    }

    pub fn has_prev(&self) -> bool {
        self.page > 1
    }
}

/// Axum 端点示例
async fn list_users(
    Query(query): Query<ListUsersQuery>,
) -> Result<Json<PaginatedResponse<User>>, AppError> {
    // 验证分页参数
    if query.page < 1 || query.page_size < 1 || query.page_size > 100 {
        return Err(AppError::BadRequest("Invalid pagination params".to_string()));
    }

    // 应用过滤条件
    let filters = build_filters(&query.status, &query.search, &query.created_after);

    // 查询总数
    let total = count_users(&filters).await?;

    // 计算偏移量并获取分页数据
    let offset = (query.page - 1) * query.page_size;
    let users = fetch_users(&filters, query.page_size, offset).await?;

    let response = PaginatedResponse::new(users, total, query.page, query.page_size);
    Ok(Json(response))
}
```

### Pattern 3: Error Handling and Status Codes

```rust
use axum::{
    http::StatusCode,
    response::{IntoResponse, Response, Json},
};
use serde::Serialize;

/// 统一错误响应结构
#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<serde_json::Value>,
    pub timestamp: String,
    pub path: String,
}

/// 字段验证错误详情
#[derive(Debug, Serialize)]
pub struct ValidationErrorDetail {
    pub field: String,
    pub message: String,
    pub value: serde_json::Value,
}

/// 应用错误类型
#[derive(Debug)]
pub enum AppError {
    NotFound { resource: String, id: String },
    ValidationError(Vec<ValidationErrorDetail>),
    BadRequest(String),
    Unauthorized,
    Forbidden,
    InternalError(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, error_type, message, details) = match self {
            AppError::NotFound { resource, id } => (
                StatusCode::NOT_FOUND,
                "NotFound",
                format!("{} not found", resource),
                Some(serde_json::json!({ "id": id })),
            ),
            AppError::ValidationError(errors) => (
                StatusCode::UNPROCESSABLE_ENTITY,
                "ValidationError",
                "Request validation failed".to_string(),
                Some(serde_json::json!({ "errors": errors })),
            ),
            AppError::BadRequest(msg) => (
                StatusCode::BAD_REQUEST,
                "BadRequest",
                msg,
                None,
            ),
            AppError::Unauthorized => (
                StatusCode::UNAUTHORIZED,
                "Unauthorized",
                "Authentication required".to_string(),
                None,
            ),
            AppError::Forbidden => (
                StatusCode::FORBIDDEN,
                "Forbidden",
                "Insufficient permissions".to_string(),
                None,
            ),
            AppError::InternalError(msg) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                "InternalError",
                msg,
                None,
            ),
        };

        let body = Json(ErrorResponse {
            error: error_type.to_string(),
            message,
            details,
            timestamp: chrono::Utc::now().to_rfc3339(),
            path: "/api/users/123".to_string(), // 实际应用中从请求中获取
        });

        (status, body).into_response()
    }
}

/// 端点使用示例
async fn get_user(
    Path(user_id): Path<String>,
) -> Result<Json<User>, AppError> {
    let user = fetch_user(&user_id).await?;

    user.ok_or_else(|| AppError::NotFound {
        resource: "User".to_string(),
        id: user_id,
    })
    .map(Json)
}
```

### Pattern 4: HATEOAS (Hypermedia as the Engine of Application State)

```rust
use serde::Serialize;
use std::collections::HashMap;

/// 超链接对象
#[derive(Debug, Serialize)]
pub struct Link {
    pub href: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub method: Option<String>,
}

/// 包含 HATEOAS 链接的用户响应
#[derive(Debug, Serialize)]
pub struct UserResponse {
    pub id: String,
    pub name: String,
    pub email: String,
    #[serde(rename = "_links")]
    pub links: HashMap<String, Link>,
}

impl UserResponse {
    pub fn from_user(user: User, base_url: &str) -> Self {
        let mut links = HashMap::new();

        // self 链接
        links.insert(
            "self".to_string(),
            Link {
                href: format!("{}/api/users/{}", base_url, user.id),
                method: None,
            },
        );

        // 相关资源链接
        links.insert(
            "orders".to_string(),
            Link {
                href: format!("{}/api/users/{}/orders", base_url, user.id),
                method: None,
            },
        );

        // 操作链接
        links.insert(
            "update".to_string(),
            Link {
                href: format!("{}/api/users/{}", base_url, user.id),
                method: Some("PATCH".to_string()),
            },
        );

        links.insert(
            "delete".to_string(),
            Link {
                href: format!("{}/api/users/{}", base_url, user.id),
                method: Some("DELETE".to_string()),
            },
        );

        Self {
            id: user.id,
            name: user.name,
            email: user.email,
            links,
        }
    }
}
```

## GraphQL Design Patterns

### Pattern 1: Schema Design

```graphql
# schema.graphql

# Clear type definitions
type User {
  id: ID!
  email: String!
  name: String!
  createdAt: DateTime!

  # Relationships
  orders(
    first: Int = 20
    after: String
    status: OrderStatus
  ): OrderConnection!

  profile: UserProfile
}

type Order {
  id: ID!
  status: OrderStatus!
  total: Money!
  items: [OrderItem!]!
  createdAt: DateTime!

  # Back-reference
  user: User!
}

# Pagination pattern (Relay-style)
type OrderConnection {
  edges: [OrderEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type OrderEdge {
  node: Order!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

# Enums for type safety
enum OrderStatus {
  PENDING
  CONFIRMED
  SHIPPED
  DELIVERED
  CANCELLED
}

# Custom scalars
scalar DateTime
scalar Money

# Query root
type Query {
  user(id: ID!): User
  users(
    first: Int = 20
    after: String
    search: String
  ): UserConnection!

  order(id: ID!): Order
}

# Mutation root
type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
  updateUser(input: UpdateUserInput!): UpdateUserPayload!
  deleteUser(id: ID!): DeleteUserPayload!

  createOrder(input: CreateOrderInput!): CreateOrderPayload!
}

# Input types for mutations
input CreateUserInput {
  email: String!
  name: String!
  password: String!
}

# Payload types for mutations
type CreateUserPayload {
  user: User
  errors: [Error!]
}

type Error {
  field: String
  message: String!
}
```

### Pattern 2: Resolver Design

```rust
use async_graphql::{Context, Object, Result, ID};

/// GraphQL Query 根对象
pub struct QueryRoot;

#[Object]
impl QueryRoot {
    /// 根据 ID 查询单个用户
    async fn user(&self, ctx: &Context<'_>, id: ID) -> Result<Option<User>> {
        let user = fetch_user_by_id(id.as_str()).await?;
        Ok(user)
    }

    /// 查询分页用户列表
    async fn users(
        &self,
        ctx: &Context<'_>,
        first: Option<i32>,
        after: Option<String>,
        search: Option<String>,
    ) -> Result<UserConnection> {
        let first = first.unwrap_or(20);

        // 解码游标
        let offset = after
            .and_then(|cursor| decode_cursor(&cursor))
            .unwrap_or(0);

        // 获取用户列表（多取一个以检查是否有下一页）
        let mut users = fetch_users(first + 1, offset, search.as_deref()).await?;

        // 检查是否有下一页
        let has_next = users.len() > first as usize;
        if has_next {
            users.pop();
        }

        // 构建边和游标
        let edges: Vec<UserEdge> = users
            .into_iter()
            .enumerate()
            .map(|(i, user)| UserEdge {
                cursor: encode_cursor(offset + i as i32),
                node: user,
            })
            .collect();

        let page_info = PageInfo {
            has_next_page: has_next,
            has_previous_page: offset > 0,
            start_cursor: edges.first().map(|e| e.cursor.clone()),
            end_cursor: edges.last().map(|e| e.cursor.clone()),
        };

        Ok(UserConnection {
            edges,
            page_info,
            total_count: count_users(search.as_deref()).await?,
        })
    }
}

/// User 类型的字段解析器
#[Object]
impl User {
    async fn id(&self) -> &ID {
        &self.id
    }

    async fn email(&self) -> &str {
        &self.email
    }

    async fn name(&self) -> &str {
        &self.name
    }

    /// 解析用户的订单（使用 DataLoader 防止 N+1）
    async fn orders(
        &self,
        ctx: &Context<'_>,
        first: Option<i32>,
    ) -> Result<Vec<Order>> {
        let loader = ctx.data::<OrdersByUserLoader>()?;
        let orders = loader.load_one(self.id.clone()).await?;

        Ok(orders.unwrap_or_default()
            .into_iter()
            .take(first.unwrap_or(20) as usize)
            .collect())
    }
}

/// GraphQL Mutation 根对象
pub struct MutationRoot;

#[Object]
impl MutationRoot {
    /// 创建用户
    async fn create_user(
        &self,
        ctx: &Context<'_>,
        input: CreateUserInput,
    ) -> Result<CreateUserPayload> {
        // 验证输入
        validate_user_input(&input)?;

        // 创建用户
        match create_user(&input.email, &input.name, &input.password).await {
            Ok(user) => Ok(CreateUserPayload {
                user: Some(user),
                errors: vec![],
            }),
            Err(e) => Ok(CreateUserPayload {
                user: None,
                errors: vec![UserError {
                    field: None,
                    message: e.to_string(),
                }],
            }),
        }
    }
}
```

### Pattern 3: DataLoader (N+1 Problem Prevention)

```rust
use async_graphql::dataloader::{DataLoader, Loader};
use async_trait::async_trait;
use std::collections::HashMap;

/// 用户加载器（批量加载用户）
pub struct UserLoader {
    // 实际应用中这里会有数据库连接池
}

#[async_trait]
impl Loader<String> for UserLoader {
    type Value = User;
    type Error = std::sync::Arc<anyhow::Error>;

    async fn load(&self, keys: &[String]) -> Result<HashMap<String, Self::Value>, Self::Error> {
        // 批量查询多个用户（单次数据库查询）
        let users = fetch_users_by_ids(keys).await?;

        // 构建 ID -> User 的映射
        let user_map = users
            .into_iter()
            .map(|user| (user.id.clone(), user))
            .collect();

        Ok(user_map)
    }
}

/// 用户订单加载器（批量加载用户的订单）
pub struct OrdersByUserLoader {
    // 实际应用中这里会有数据库连接池
}

#[async_trait]
impl Loader<String> for OrdersByUserLoader {
    type Value = Vec<Order>;
    type Error = std::sync::Arc<anyhow::Error>;

    async fn load(&self, user_ids: &[String]) -> Result<HashMap<String, Self::Value>, Self::Error> {
        // 批量查询多个用户的订单（单次数据库查询）
        let orders = fetch_orders_by_user_ids(user_ids).await?;

        // 按 user_id 分组订单
        let mut orders_by_user: HashMap<String, Vec<Order>> = HashMap::new();
        for order in orders {
            orders_by_user
                .entry(order.user_id.clone())
                .or_insert_with(Vec::new)
                .push(order);
        }

        // 确保所有 user_id 都有值（即使是空列表）
        for user_id in user_ids {
            orders_by_user.entry(user_id.clone()).or_insert_with(Vec::new);
        }

        Ok(orders_by_user)
    }
}

/// 创建 GraphQL Context
pub fn create_graphql_context() -> async_graphql::Context<'static> {
    let user_loader = DataLoader::new(UserLoader {}, tokio::spawn);
    let orders_loader = DataLoader::new(OrdersByUserLoader {}, tokio::spawn);

    // 将 loaders 添加到 context
    // context.insert(user_loader);
    // context.insert(orders_loader);

    // 实际使用示例见上面的 resolver 代码
    unimplemented!()
}
```

## Best Practices

### REST APIs
1. **Consistent Naming**: Use plural nouns for collections (`/users`, not `/user`)
2. **Stateless**: Each request contains all necessary information
3. **Use HTTP Status Codes Correctly**: 2xx success, 4xx client errors, 5xx server errors
4. **Version Your API**: Plan for breaking changes from day one
5. **Pagination**: Always paginate large collections
6. **Rate Limiting**: Protect your API with rate limits
7. **Documentation**: Use OpenAPI/Swagger for interactive docs

### GraphQL APIs
1. **Schema First**: Design schema before writing resolvers
2. **Avoid N+1**: Use DataLoaders for efficient data fetching
3. **Input Validation**: Validate at schema and resolver levels
4. **Error Handling**: Return structured errors in mutation payloads
5. **Pagination**: Use cursor-based pagination (Relay spec)
6. **Deprecation**: Use `@deprecated` directive for gradual migration
7. **Monitoring**: Track query complexity and execution time

## Common Pitfalls

- **Over-fetching/Under-fetching (REST)**: Fixed in GraphQL but requires DataLoaders
- **Breaking Changes**: Version APIs or use deprecation strategies
- **Inconsistent Error Formats**: Standardize error responses
- **Missing Rate Limits**: APIs without limits are vulnerable to abuse
- **Poor Documentation**: Undocumented APIs frustrate developers
- **Ignoring HTTP Semantics**: POST for idempotent operations breaks expectations
- **Tight Coupling**: API structure shouldn't mirror database schema

## Resources

- **references/rest-best-practices.md**: Comprehensive REST API design guide
- **references/graphql-schema-design.md**: GraphQL schema patterns and anti-patterns
- **references/api-versioning-strategies.md**: Versioning approaches and migration paths
- **assets/rest-api-template.rs**: Axum REST API template (Rust)
- **assets/graphql-schema-template.graphql**: Complete GraphQL schema example
- **assets/api-design-checklist.md**: Pre-implementation review checklist

## Rust 依赖说明

本 Skill 中的 Rust 示例使用以下依赖（`Cargo.toml`）：

### REST API 依赖

```toml
[dependencies]
# Web 框架
axum = "0.7"
tokio = { version = "1", features = ["full"] }

# 序列化与反序列化
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# 验证
validator = { version = "0.18", features = ["derive"] }

# 日志与追踪
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

# HTTP 工具
tower-http = { version = "0.5", features = ["cors"] }

# 时间处理
chrono = { version = "0.4", features = ["serde"] }

# 错误处理
anyhow = "1.0"
thiserror = "1.0"
```

### GraphQL 依赖（额外）

```toml
[dependencies]
# GraphQL 框架
async-graphql = { version = "7.0", features = ["dataloader"] }
async-graphql-axum = "7.0"
async-trait = "0.1"
```

### 运行示例

```bash
# 克隆或复制 rest-api-template.rs
cp .claude/skills/api-design-principles/assets/rest-api-template.rs src/main.rs

# 运行服务器
cargo run

# 访问 API 文档（如果配置了）
open http://localhost:8000/api/docs
```

### 项目结构建议

```
src/
├── main.rs              # 应用入口
├── api/
│   ├── mod.rs          # API 模块
│   ├── routes.rs       # 路由定义
│   └── handlers/       # 请求处理器
│       ├── mod.rs
│       └── users.rs
├── models/             # 数据模型
│   ├── mod.rs
│   └── user.rs
└── error.rs            # 错误类型定义
```

