# Rust 中的 DDD 与 OOP 实践参考

本文档专门针对使用 Rust 实现的后端代码，提供 DDD（领域驱动设计）和 OOP（面向对象编程）的实践指导。

---

## 目录

1. [Rust 的 OOP 特性](#rust-的-oop-特性)
2. [DDD 分层架构在 Rust 中的实现](#ddd-分层架构在-rust-中的实现)
3. [SOLID 原则的 Rust 实现](#solid-原则的-rust-实现)
4. [领域模型设计模式](#领域模型设计模式)
5. [错误处理最佳实践](#错误处理最佳实践)
6. [并发与异步设计](#并发与异步设计)
7. [测试策略](#测试策略)

---

## Rust 的 OOP 特性

### 1. 结构体与方法

Rust 通过结构体（struct）和实现块（impl）模拟类的概念：

```rust
// 领域实体示例：产品
pub struct Product {
    id: ProductId,
    name: String,
    price: i64,  // 以分为单位
    stock: u32,
}

impl Product {
    // 构造函数
    pub fn new(name: String, price: i64) -> Self {
        Self {
            id: ProductId::generate(),
            name,
            price,
            stock: 0,
        }
    }

    // 领域行为（可变借用）
    pub fn update_price(&mut self, new_price: i64) -> Result<(), DomainError> {
        if new_price < 0 {
            return Err(DomainError::InvalidPrice);
        }
        self.price = new_price;
        Ok(())
    }

    pub fn reserve_stock(&mut self, quantity: u32) -> Result<(), DomainError> {
        if self.stock < quantity {
            return Err(DomainError::InsufficientStock);
        }
        self.stock -= quantity;
        Ok(())
    }

    // 查询方法（不可变借用）
    pub fn id(&self) -> &ProductId {
        &self.id
    }

    pub fn available_stock(&self) -> u32 {
        self.stock
    }
}
```

### 2. Trait 系统（行为抽象）

Trait 是 Rust 中的接口机制，用于定义行为契约：

```rust
use async_trait::async_trait;

// 仓储接口示例
#[async_trait]
pub trait Repository<T, ID>: Send + Sync {
    async fn find_by_id(&self, id: &ID) -> Result<Option<T>, RepositoryError>;
    async fn save(&self, entity: &T) -> Result<(), RepositoryError>;
    async fn delete(&self, id: &ID) -> Result<(), RepositoryError>;
}

// 领域服务接口示例
#[async_trait]
pub trait PaymentService: Send + Sync {
    async fn process_payment(&self, request: PaymentRequest) 
        -> Result<PaymentResult, PaymentError>;
}

// 特性：Send + Sync 确保线程安全
// 特性：async_trait 宏支持异步方法
```

### 3. 枚举与模式匹配（类型安全的多态）

枚举提供类型安全的状态建模和模式匹配：

```rust
// 订单状态枚举（携带状态相关数据）
#[derive(Debug, Clone, PartialEq)]
pub enum OrderStatus {
    Pending,
    Processing { assigned_to: UserId },
    Shipped { tracking_number: String },
    Cancelled { reason: String },
}

impl OrderStatus {
    pub fn can_cancel(&self) -> bool {
        matches!(self, Self::Pending | Self::Processing { .. })
    }

    pub fn transition_to_processing(&self, user_id: UserId) -> Result<Self, DomainError> {
        match self {
            Self::Pending => Ok(Self::Processing { assigned_to: user_id }),
            _ => Err(DomainError::InvalidStateTransition(
                format!("Cannot transition from {:?} to Processing", self)
            )),
        }
    }
}

// 领域事件枚举
#[derive(Debug, Clone)]
pub enum DomainEvent {
    UserRegistered { user_id: UserId, email: String },
    OrderCreated { order_id: OrderId, amount: i64 },
    PaymentProcessed { payment_id: PaymentId, order_id: OrderId },
}

impl DomainEvent {
    pub fn event_type(&self) -> &'static str {
        match self {
            Self::UserRegistered { .. } => "UserRegistered",
            Self::OrderCreated { .. } => "OrderCreated",
            Self::PaymentProcessed { .. } => "PaymentProcessed",
        }
    }
}
```

---

## DDD 分层架构在 Rust 中的实现

### 架构分层

```
┌─────────────────────────────────────────────────┐
│      接口层 (Presentation/API Layer)           │
│      - HTTP handlers (Axum/Actix)             │
│      - GraphQL resolvers                       │
│      - gRPC services                           │
├─────────────────────────────────────────────────┤
│      应用层 (Application Layer)                │
│      - Use cases / Commands / Queries         │
│      - DTOs (Data Transfer Objects)           │
│      - Application services                    │
├─────────────────────────────────────────────────┤
│      领域层 (Domain Layer)                     │
│      - Entities (实体)                         │
│      - Value Objects (值对象)                  │
│      - Aggregates (聚合)                       │
│      - Domain Services (领域服务)              │
│      - Repository Interfaces (仓储接口)       │
│      - Domain Events (领域事件)                │
├─────────────────────────────────────────────────┤
│   基础设施层 (Infrastructure Layer)            │
│      - Repository Implementations             │
│      - Database (sqlx, diesel, sea-orm)       │
│      - External APIs                          │
│      - Message Queue (RabbitMQ, Kafka)        │
│      - Cache (Redis)                          │
└─────────────────────────────────────────────────┘
```

### 项目目录结构示例

```
src/
├── main.rs
├── lib.rs
├── api/                    # 接口层
│   ├── mod.rs
│   ├── handlers/           # HTTP handlers
│   │   ├── user.rs
│   │   ├── order.rs
│   │   └── payment.rs
│   ├── dto/                # 数据传输对象
│   │   ├── user_dto.rs
│   │   └── order_dto.rs
│   └── routes.rs           # 路由定义
├── application/            # 应用层
│   ├── mod.rs
│   ├── commands/           # 命令（写操作）
│   │   ├── create_user.rs
│   │   ├── create_order.rs
│   │   └── process_payment.rs
│   ├── queries/            # 查询（读操作）
│   │   ├── get_user.rs
│   │   └── list_orders.rs
│   └── services/           # 应用服务
│       └── user_service.rs
├── domain/                 # 领域层
│   ├── mod.rs
│   ├── user/               # 用户聚合
│   │   ├── mod.rs
│   │   ├── entity.rs       # User 实体
│   │   ├── value_objects.rs # Email, UserId 等值对象
│   │   └── repository.rs   # UserRepository trait
│   ├── order/              # 订单聚合
│   │   ├── mod.rs
│   │   ├── entity.rs
│   │   ├── order_item.rs
│   │   └── repository.rs
│   ├── payment/            # 支付聚合
│   │   ├── mod.rs
│   │   ├── entity.rs
│   │   └── service.rs      # 领域服务
│   ├── events.rs           # 领域事件定义
│   └── errors.rs           # 领域错误
└── infrastructure/         # 基础设施层
    ├── mod.rs
    ├── persistence/        # 持久化
    │   ├── postgres/
    │   │   ├── user_repo.rs
    │   │   └── order_repo.rs
    │   └── migrations/
    ├── cache/              # 缓存
    │   └── redis_cache.rs
    ├── messaging/          # 消息队列
    │   └── event_bus.rs
    └── external/           # 外部服务
        └── payment_gateway.rs
```

### 各层实现示例

#### 1. 领域层（Domain Layer）

```rust
// domain/user/entity.rs - 用户实体（聚合根）
use super::value_objects::{Email, UserId, Username};
use crate::domain::events::DomainEvent;

pub struct User {
    id: UserId,
    username: Username,
    email: Email,
    password_hash: String,
    uncommitted_events: Vec<DomainEvent>,
}

impl User {
    // 工厂方法：创建新用户
    pub fn register(username: Username, email: Email, password: &str) 
        -> Result<Self, DomainError> {
        Self::validate_password(password)?;
        
        let mut user = Self {
            id: UserId::generate(),
            username: username.clone(),
            email: email.clone(),
            password_hash: Self::hash_password(password)?,
            uncommitted_events: Vec::new(),
        };

        // 记录领域事件
        user.record_event(DomainEvent::UserRegistered {
            user_id: user.id.clone(),
            email: email.to_string(),
        });

        Ok(user)
    }

    // 领域行为：修改邮箱
    pub fn change_email(&mut self, new_email: Email) -> Result<(), DomainError> {
        if self.email == new_email {
            return Err(DomainError::EmailUnchanged);
        }
        self.email = new_email;
        Ok(())
    }

    // 事件管理
    fn record_event(&mut self, event: DomainEvent) {
        self.uncommitted_events.push(event);
    }

    pub fn take_uncommitted_events(&mut self) -> Vec<DomainEvent> {
        std::mem::take(&mut self.uncommitted_events)
    }

    // 查询方法
    pub fn id(&self) -> &UserId { &self.id }
    pub fn email(&self) -> &Email { &self.email }
    pub fn password_hash(&self) -> &str { &self.password_hash }

    // 私有辅助方法
    fn validate_password(password: &str) -> Result<(), DomainError> {
        if password.len() < 8 {
            return Err(DomainError::WeakPassword("密码至少8位".into()));
        }
        Ok(())
    }

    fn hash_password(password: &str) -> Result<String, DomainError> {
        bcrypt::hash(password, bcrypt::DEFAULT_COST)
            .map_err(|e| DomainError::PasswordHashError(e.to_string()))
    }

    // 从持久化存储重建（供仓储层使用）
    pub fn reconstruct(
        id: UserId, username: Username, email: Email, password_hash: String
    ) -> Self {
        Self { id, username, email, password_hash, uncommitted_events: Vec::new() }
    }
}

// domain/user/value_objects.rs - 值对象
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct UserId(uuid::Uuid);

impl UserId {
    pub fn generate() -> Self {
        Self(uuid::Uuid::new_v4())
    }

    pub fn from_string(s: &str) -> Result<Self, DomainError> {
        let uuid = uuid::Uuid::parse_str(s)
            .map_err(|_| DomainError::InvalidUserId)?;
        Ok(Self(uuid))
    }

    pub fn as_uuid(&self) -> &uuid::Uuid {
        &self.0
    }
}

impl fmt::Display for UserId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Email(String);

impl Email {
    pub fn new(email: String) -> Result<Self, DomainError> {
        // 邮箱格式验证
        if !email.contains('@') || email.len() < 5 {
            return Err(DomainError::InvalidEmail);
        }

        // 更严格的邮箱验证可以使用 email-validator crate
        Ok(Self(email.to_lowercase()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for Email {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Username(String);

impl Username {
    pub fn new(username: String) -> Result<Self, DomainError> {
        if username.len() < 3 || username.len() > 20 {
            return Err(DomainError::InvalidUsername("用户名长度需在3-20字符之间".into()));
        }

        // 只允许字母、数字和下划线
        if !username.chars().all(|c| c.is_alphanumeric() || c == '_') {
            return Err(DomainError::InvalidUsername("用户名只能包含字母、数字和下划线".into()));
        }

        Ok(Self(username))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

// domain/user/repository.rs - 仓储接口（领域层定义）
use async_trait::async_trait;

#[async_trait]
pub trait UserRepository: Send + Sync {
    async fn find_by_id(&self, id: &UserId) -> Result<Option<User>, RepositoryError>;
    async fn find_by_email(&self, email: &Email) -> Result<Option<User>, RepositoryError>;
    async fn find_by_username(&self, username: &Username) -> Result<Option<User>, RepositoryError>;
    async fn save(&self, user: &User) -> Result<(), RepositoryError>;
    async fn delete(&self, id: &UserId) -> Result<(), RepositoryError>;
    async fn exists_by_email(&self, email: &Email) -> Result<bool, RepositoryError>;
    async fn exists_by_username(&self, username: &Username) -> Result<bool, RepositoryError>;
}
```

#### 2. 应用层（Application Layer）

```rust
// application/commands/create_user.rs - 创建用户命令
use std::sync::Arc;
use crate::domain::user::{Email, User, Username, UserRepository};
use crate::domain::events::DomainEvent;
use crate::infrastructure::messaging::EventPublisher;
use crate::application::errors::ApplicationError;

pub struct CreateUserCommand {
    pub username: String,
    pub email: String,
    pub password: String,
}

pub struct CreateUserResult {
    pub user_id: String,
    pub username: String,
    pub email: String,
}

pub struct CreateUserHandler<R: UserRepository, E: EventPublisher> {
    user_repository: Arc<R>,
    event_publisher: Arc<E>,
}

impl<R: UserRepository, E: EventPublisher> CreateUserHandler<R, E> {
    pub fn new(user_repository: Arc<R>, event_publisher: Arc<E>) -> Self {
        Self {
            user_repository,
            event_publisher,
        }
    }

    pub async fn handle(&self, command: CreateUserCommand) -> Result<CreateUserResult, ApplicationError> {
        // 1. 值对象构造与验证
        let username = Username::new(command.username)?;
        let email = Email::new(command.email)?;

        // 2. 业务规则检查：用户名和邮箱唯一性
        if self.user_repository.exists_by_username(&username).await? {
            return Err(ApplicationError::UsernameAlreadyExists);
        }

        if self.user_repository.exists_by_email(&email).await? {
            return Err(ApplicationError::EmailAlreadyExists);
        }

        // 3. 创建领域对象（聚合根）
        let mut user = User::register(username.clone(), email.clone(), &command.password)?;

        // 4. 持久化
        self.user_repository.save(&user).await?;

        // 5. 发布领域事件
        let events = user.take_uncommitted_events();
        for event in events {
            self.event_publisher.publish(event).await?;
        }

        // 6. 返回结果
        Ok(CreateUserResult {
            user_id: user.id().to_string(),
            username: user.username().to_string(),
            email: user.email().to_string(),
        })
    }
}

// application/queries/get_user.rs - 查询用户
pub struct GetUserQuery {
    pub user_id: String,
}

pub struct UserDto {
    pub id: String,
    pub username: String,
    pub email: String,
    pub created_at: String,
}

pub struct GetUserHandler<R: UserRepository> {
    user_repository: Arc<R>,
}

impl<R: UserRepository> GetUserHandler<R> {
    pub fn new(user_repository: Arc<R>) -> Self {
        Self { user_repository }
    }

    pub async fn handle(&self, query: GetUserQuery) -> Result<UserDto, ApplicationError> {
        let user_id = UserId::from_string(&query.user_id)?;

        let user = self.user_repository
            .find_by_id(&user_id)
            .await?
            .ok_or(ApplicationError::UserNotFound)?;

        Ok(UserDto {
            id: user.id().to_string(),
            username: user.username().to_string(),
            email: user.email().to_string(),
            created_at: user.created_at().to_rfc3339(),
        })
    }
}
```

#### 3. 基础设施层（Infrastructure Layer）

```rust
// infrastructure/persistence/postgres/user_repo.rs - 用户仓储实现
use sqlx::{PgPool, Row};
use async_trait::async_trait;
use crate::domain::user::{User, UserId, Email, Username, UserRepository};

pub struct PostgresUserRepository {
    pool: PgPool,
}

impl PostgresUserRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl UserRepository for PostgresUserRepository {
    async fn find_by_id(&self, id: &UserId) -> Result<Option<User>, RepositoryError> {
        let result = sqlx::query(
            r#"
            SELECT id, username, email, password_hash, created_at, updated_at
            FROM users
            WHERE id = $1
            "#
        )
        .bind(id.as_uuid())
        .fetch_optional(&self.pool)
        .await?;

        match result {
            Some(row) => {
                let user = Self::row_to_user(row)?;
                Ok(Some(user))
            }
            None => Ok(None),
        }
    }

    async fn find_by_email(&self, email: &Email) -> Result<Option<User>, RepositoryError> {
        let result = sqlx::query(
            r#"
            SELECT id, username, email, password_hash, created_at, updated_at
            FROM users
            WHERE email = $1
            "#
        )
        .bind(email.as_str())
        .fetch_optional(&self.pool)
        .await?;

        match result {
            Some(row) => Ok(Some(Self::row_to_user(row)?)),
            None => Ok(None),
        }
    }

    async fn save(&self, user: &User) -> Result<(), RepositoryError> {
        sqlx::query(
            r#"
            INSERT INTO users (id, username, email, password_hash, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE SET
                username = EXCLUDED.username,
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                updated_at = EXCLUDED.updated_at
            "#
        )
        .bind(user.id().as_uuid())
        .bind(user.username().as_str())
        .bind(user.email().as_str())
        .bind(user.password_hash())
        .bind(user.created_at())
        .bind(user.updated_at())
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    async fn delete(&self, id: &UserId) -> Result<(), RepositoryError> {
        let result = sqlx::query("DELETE FROM users WHERE id = $1")
            .bind(id.as_uuid())
            .execute(&self.pool)
            .await?;

        if result.rows_affected() == 0 {
            return Err(RepositoryError::NotFound);
        }

        Ok(())
    }

    async fn exists_by_email(&self, email: &Email) -> Result<bool, RepositoryError> {
        let result: (bool,) = sqlx::query_as(
            "SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)"
        )
        .bind(email.as_str())
        .fetch_one(&self.pool)
        .await?;

        Ok(result.0)
    }

    async fn exists_by_username(&self, username: &Username) -> Result<bool, RepositoryError> {
        let result: (bool,) = sqlx::query_as(
            "SELECT EXISTS(SELECT 1 FROM users WHERE username = $1)"
        )
        .bind(username.as_str())
        .fetch_one(&self.pool)
        .await?;

        Ok(result.0)
    }
}

impl PostgresUserRepository {
    fn row_to_user(row: sqlx::postgres::PgRow) -> Result<User, RepositoryError> {
        // 将数据库行转换为领域对象
        // 注意：这里需要 User 提供重构方法或使用构造器模式
        User::reconstruct(
            UserId::from_uuid(row.get("id")),
            Username::new(row.get("username"))?,
            Email::new(row.get("email"))?,
            row.get("password_hash"),
            row.get("created_at"),
            row.get("updated_at"),
        )
    }
}
```

#### 4. 接口层（API Layer）

```rust
// api/handlers/user.rs - HTTP 处理器
use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde::{Deserialize, Serialize};

// 请求 DTO
#[derive(Debug, Deserialize)]
pub struct CreateUserRequest {
    pub username: String,
    pub email: String,
    pub password: String,
}

// 响应 DTO
#[derive(Debug, Serialize)]
pub struct UserResponse {
    pub id: String,
    pub username: String,
    pub email: String,
    pub created_at: String,
}

// HTTP 处理器
pub async fn create_user(
    State(handler): State<Arc<CreateUserHandler<PostgresUserRepository, EventBus>>>,
    Json(req): Json<CreateUserRequest>,
) -> Result<Json<UserResponse>, ApiError> {
    let command = CreateUserCommand {
        username: req.username,
        email: req.email,
        password: req.password,
    };

    let result = handler.handle(command).await?;

    Ok(Json(UserResponse {
        id: result.user_id,
        username: result.username,
        email: result.email,
        created_at: chrono::Utc::now().to_rfc3339(),
    }))
}

pub async fn get_user(
    State(handler): State<Arc<GetUserHandler<PostgresUserRepository>>>,
    Path(user_id): Path<String>,
) -> Result<Json<UserResponse>, ApiError> {
    let query = GetUserQuery { user_id };
    let user = handler.handle(query).await?;

    Ok(Json(UserResponse {
        id: user.id,
        username: user.username,
        email: user.email,
        created_at: user.created_at,
    }))
}

// 错误处理
#[derive(Debug)]
pub enum ApiError {
    Application(ApplicationError),
    Validation(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            ApiError::Application(ApplicationError::UserNotFound) => {
                (StatusCode::NOT_FOUND, "用户不存在")
            }
            ApiError::Application(ApplicationError::UsernameAlreadyExists) => {
                (StatusCode::CONFLICT, "用户名已存在")
            }
            ApiError::Application(ApplicationError::EmailAlreadyExists) => {
                (StatusCode::CONFLICT, "邮箱已被使用")
            }
            ApiError::Validation(msg) => {
                (StatusCode::BAD_REQUEST, msg.as_str())
            }
            _ => (StatusCode::INTERNAL_SERVER_ERROR, "服务器内部错误"),
        };

        (status, Json(serde_json::json!({ "error": message }))).into_response()
    }
}
```

---

## SOLID 原则的 Rust 实现

### 1. 单一职责原则（SRP）

每个模块只有一个变更理由：

```rust
// ❌ 错误：多职责混杂
struct UserService {
    // 业务逻辑 + 数据库 + 邮件 + 日志...
}

// ✅ 正确：职责分离，通过依赖注入组合
struct UserService {
    repository: Arc<dyn UserRepository>,  // 持久化
    email_service: Arc<dyn EmailService>, // 邮件
    logger: Arc<dyn Logger>,              // 日志
}
```

### 2. 开闭原则（OCP）

对扩展开放，对修改封闭：

```rust
// 定义抽象接口
#[async_trait]
pub trait PaymentProcessor: Send + Sync {
    async fn process(&self, request: &PaymentRequest) -> Result<PaymentResult, PaymentError>;
}

// 现有实现
pub struct CreditCardProcessor { /* ... */ }

#[async_trait]
impl PaymentProcessor for CreditCardProcessor {
    async fn process(&self, request: &PaymentRequest) -> Result<PaymentResult, PaymentError> {
        // 信用卡逻辑
    }
}

// ✅ 扩展新功能无需修改现有代码
pub struct AlipayProcessor { /* ... */ }

#[async_trait]
impl PaymentProcessor for AlipayProcessor {
    async fn process(&self, request: &PaymentRequest) -> Result<PaymentResult, PaymentError> {
        // 支付宝逻辑
    }
}

// 服务通过策略注册扩展
pub struct PaymentService {
    processors: HashMap<PaymentMethod, Arc<dyn PaymentProcessor>>,
}
```

### 3. 里氏替换原则（LSP）

子类型必须能够完全替换基类型：

```rust
// 存储抽象
#[async_trait]
pub trait Storage: Send + Sync {
    async fn save(&self, key: &str, value: &[u8]) -> Result<(), StorageError>;
    async fn load(&self, key: &str) -> Result<Vec<u8>, StorageError>;
}

// MemoryStorage 实现
pub struct MemoryStorage { /* ... */ }

#[async_trait]
impl Storage for MemoryStorage {
    async fn save(&self, key: &str, value: &[u8]) -> Result<(), StorageError> { /* ... */ }
    async fn load(&self, key: &str) -> Result<Vec<u8>, StorageError> { /* ... */ }
}

// FileStorage 实现 - 完全可替换 MemoryStorage
pub struct FileStorage { /* ... */ }

#[async_trait]
impl Storage for FileStorage {
    async fn save(&self, key: &str, value: &[u8]) -> Result<(), StorageError> { /* ... */ }
    async fn load(&self, key: &str) -> Result<Vec<u8>, StorageError> { /* ... */ }
}

// ✅ 可以使用任何 Storage 实现，行为一致
pub struct CacheService<S: Storage> {
    storage: Arc<S>,
}
```

### 4. 接口隔离原则（ISP）

客户端不应被迫依赖不使用的接口：

```rust
// ✅ 细粒度 trait，按需实现
pub trait Readable {
    fn read(&self) -> Result<Vec<u8>, IoError>;
}

pub trait Writable {
    fn write(&mut self, data: &[u8]) -> Result<(), IoError>;
}

// 只读文件只需实现 Readable
pub struct ReadOnlyFile { /* ... */ }
impl Readable for ReadOnlyFile { /* ... */ }

// 可读写文件实现两者
pub struct ReadWriteFile { /* ... */ }
impl Readable for ReadWriteFile { /* ... */ }
impl Writable for ReadWriteFile { /* ... */ }

// ✅ 客户端只依赖需要的接口
pub fn backup<R: Readable>(reader: &R) -> Result<Vec<u8>, IoError> {
    reader.read()
}
```

### 5. 依赖倒置原则（DIP）

高层模块依赖抽象，不依赖具体实现：

```rust
// ✅ 高层业务逻辑依赖抽象接口
pub struct OrderService {
    order_repo: Arc<dyn OrderRepository>,
    payment: Arc<dyn PaymentService>,
    notification: Arc<dyn NotificationService>,
}

impl OrderService {
    // 通过构造函数注入依赖
    pub fn new(
        order_repo: Arc<dyn OrderRepository>,
        payment: Arc<dyn PaymentService>,
        notification: Arc<dyn NotificationService>,
    ) -> Self {
        Self { order_repo, payment, notification }
    }

    pub async fn create_order(&self, request: CreateOrderRequest) 
        -> Result<Order, OrderError> {
        let order = Order::create(request)?;
        self.order_repo.save(&order).await?;
        self.payment.process_payment(order.id(), order.total()).await?;
        Ok(order)
    }
}
```

---

## 领域模型设计模式

### 1. 实体（Entity）

有唯一标识，生命周期中标识不变：

```rust
pub struct Product {
    id: ProductId,        // 唯一标识
    name: String,
    price: i64,
    stock: u32,
    version: u32,         // 乐观锁
}

impl Product {
    pub fn id(&self) -> &ProductId { &self.id }

    pub fn update_price(&mut self, new_price: i64) -> Result<(), DomainError> {
        if new_price < 0 { return Err(DomainError::InvalidPrice); }
        self.price = new_price;
        Ok(())
    }
}

// 特点：通过 id 识别，属性可变，有业务行为
```

### 2. 值对象（Value Object）

无唯一标识，不可变，由属性完全定义：

```rust
// Money 值对象
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Money {
    amount: i64,      // 以分为单位避免浮点数
    currency: Currency,
}

impl Money {
    pub fn new(amount: i64, currency: Currency) -> Result<Self, DomainError> {
        if amount < 0 { return Err(DomainError::NegativeAmount); }
        Ok(Self { amount, currency })
    }

    pub fn add(&self, other: Money) -> Result<Self, DomainError> {
        if self.currency != other.currency {
            return Err(DomainError::CurrencyMismatch);
        }
        Ok(Self { amount: self.amount + other.amount, currency: self.currency })
    }
}

// 特点：不可变、无标识、相等性基于所有属性、可 Copy
```

### 3. 聚合（Aggregate）与聚合根

```rust
// Order 是聚合根，控制 OrderItem
pub struct Order {
    id: OrderId,
    items: Vec<OrderItem>,  // 聚合内实体
    status: OrderStatus,
}

impl Order {
    // ✅ 通过聚合根操作聚合内对象
    pub fn add_item(&mut self, product_id: ProductId, quantity: u32, price: i64)
        -> Result<(), DomainError> {
        if !self.status.can_modify() {
            return Err(DomainError::OrderNotModifiable);
        }
        
        let item = OrderItem::new(product_id, quantity, price)?;
        self.items.push(item);
        Ok(())
    }

    pub fn total(&self) -> i64 {
        self.items.iter().map(|item| item.subtotal()).sum()
    }
}

// 聚合内实体（private，不直接暴露）
struct OrderItem {
    product_id: ProductId,
    quantity: u32,
    unit_price: i64,
}

impl OrderItem {
    fn new(product_id: ProductId, quantity: u32, unit_price: i64) -> Result<Self, DomainError> {
        if quantity == 0 { return Err(DomainError::InvalidQuantity); }
        Ok(Self { product_id, quantity, unit_price })
    }
    
    fn subtotal(&self) -> i64 {
        self.unit_price * self.quantity as i64
    }
}

// 特点：聚合根控制聚合边界，外部只能通过聚合根访问
```

### 4. 领域服务（Domain Service）

跨聚合的业务逻辑：

```rust
// 转账服务（跨两个账户聚合）
pub struct TransferService;

impl TransferService {
    pub fn transfer(
        &self,
        from: &mut Account,
        to: &mut Account,
        amount: i64,
    ) -> Result<(), DomainError> {
        if from.id() == to.id() {
            return Err(DomainError::CannotTransferToSelf);
        }
        from.withdraw(amount)?;
        to.deposit(amount)?;
        Ok(())
    }
}

// 特点：无状态，协调多个聚合的业务逻辑
```

---

## 错误处理最佳实践

### 使用 thiserror 定义领域错误

```rust
use thiserror::Error;

// 领域错误
#[derive(Debug, Error)]
pub enum DomainError {
    #[error("用户不存在")]
    UserNotFound,

    #[error("无效的邮箱地址")]
    InvalidEmail,

    #[error("无效的用户ID")]
    InvalidUserId,

    #[error("无效的用户名: {0}")]
    InvalidUsername(String),

    #[error("用户名已存在")]
    UsernameAlreadyExists,

    #[error("邮箱未改变")]
    EmailUnchanged,

    #[error("无效的凭证")]
    InvalidCredentials,

    #[error("余额不足")]
    InsufficientFunds,

    #[error("账户未激活")]
    AccountNotActive,

    #[error("无效金额: {0}")]
    InvalidAmount(String),

    #[error("负数金额")]
    NegativeAmount,

    #[error("货币不匹配")]
    CurrencyMismatch,

    #[error("无效价格")]
    InvalidPrice,

    #[error("库存不足")]
    InsufficientStock,

    #[error("无效的状态转换: {0}")]
    InvalidStateTransition(String),

    #[error("密码强度不足: {0}")]
    WeakPassword(String),

    #[error("密码哈希错误: {0}")]
    PasswordHashError(String),

    #[error("无效地址")]
    InvalidAddress,

    #[error("订单不可修改")]
    OrderNotModifiable,

    #[error("无效数量")]
    InvalidQuantity,

    #[error("不能转账给自己")]
    CannotTransferToSelf,
}

// 基础设施错误
#[derive(Debug, Error)]
pub enum RepositoryError {
    #[error("数据库错误: {0}")]
    DatabaseError(#[from] sqlx::Error),

    #[error("记录未找到")]
    NotFound,

    #[error("序列化错误: {0}")]
    SerializationError(String),
}

// 应用层错误
#[derive(Debug, Error)]
pub enum ApplicationError {
    #[error("领域错误: {0}")]
    Domain(#[from] DomainError),

    #[error("仓储错误: {0}")]
    Repository(#[from] RepositoryError),

    #[error("用户不存在")]
    UserNotFound,

    #[error("用户名已存在")]
    UsernameAlreadyExists,

    #[error("邮箱已被使用")]
    EmailAlreadyExists,
}
```

### Result 类型的使用

```rust
// 领域层
impl User {
    pub fn change_password(&mut self, old_pwd: &str, new_pwd: &str)
        -> Result<(), DomainError> {
        // 业务逻辑
        Ok(())
    }
}

// 应用层
impl CreateUserHandler {
    pub async fn handle(&self, cmd: CreateUserCommand)
        -> Result<CreateUserResult, ApplicationError> {
        // 使用 ? 操作符传播错误
        let username = Username::new(cmd.username)?;
        let email = Email::new(cmd.email)?;

        if self.user_repo.exists_by_email(&email).await? {
            return Err(ApplicationError::EmailAlreadyExists);
        }

        // ...
        Ok(result)
    }
}
```

---

## 并发与异步设计

### 使用 tokio 和 async/await

```rust
use tokio;
use std::sync::Arc;

// 异步仓储
#[async_trait]
pub trait UserRepository: Send + Sync {
    async fn find_by_id(&self, id: &UserId) -> Result<Option<User>, RepositoryError>;
    async fn save(&self, user: &User) -> Result<(), RepositoryError>;
}

// 异步应用服务
pub struct UserService {
    repo: Arc<dyn UserRepository>,
}

impl UserService {
    pub async fn get_user(&self, id: UserId) -> Result<User, ApplicationError> {
        self.repo
            .find_by_id(&id)
            .await?
            .ok_or(ApplicationError::UserNotFound)
    }

    // 并发操作多个仓储
    pub async fn get_users_by_ids(&self, ids: Vec<UserId>) -> Result<Vec<User>, ApplicationError> {
        let futures = ids.into_iter().map(|id| self.get_user(id));
        
        let results = futures::future::join_all(futures).await;
        
        results.into_iter().collect::<Result<Vec<_>, _>>()
    }
}
```

### 线程安全的共享状态

```rust
use tokio::sync::{RwLock, Mutex};
use std::sync::Arc;

// 使用 Arc + RwLock 共享可变状态
pub struct CacheService {
    data: Arc<RwLock<HashMap<String, Vec<u8>>>>,
}

impl CacheService {
    pub async fn get(&self, key: &str) -> Option<Vec<u8>> {
        let data = self.data.read().await;
        data.get(key).cloned()
    }

    pub async fn set(&self, key: String, value: Vec<u8>) {
        let mut data = self.data.write().await;
        data.insert(key, value);
    }
}
```

---

## 测试策略

### 单元测试（领域层）

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_user_registration() {
        let username = Username::new("testuser".into()).unwrap();
        let email = Email::new("test@example.com".into()).unwrap();
        let user = User::register(username, email, "password123").unwrap();
        
        assert_eq!(user.email().as_str(), "test@example.com");
    }

    #[test]
    fn test_invalid_quantity() {
        let result = OrderItem::new(ProductId::generate(), 0, 100);
        assert!(matches!(result, Err(DomainError::InvalidQuantity)));
    }
}
```

### 集成测试（应用层）

```rust
#[tokio::test]
async fn test_create_user_flow() {
    let pool = setup_test_db().await;
    let repo = Arc::new(PostgresUserRepository::new(pool));
    let event_bus = Arc::new(InMemoryEventBus::new());
    let handler = CreateUserHandler::new(repo, event_bus);

    let command = CreateUserCommand {
        username: "test".into(),
        email: "test@example.com".into(),
        password: "pass123".into(),
    };

    let result = handler.handle(command).await.unwrap();
    assert_eq!(result.username, "test");
}
```

### Mock 测试（使用 mockall）

```rust
use mockall::*;

#[automock]
#[async_trait]
pub trait UserRepository: Send + Sync {
    async fn find_by_id(&self, id: &UserId) -> Result<Option<User>, RepositoryError>;
}

#[tokio::test]
async fn test_with_mock() {
    let mut mock_repo = MockUserRepository::new();
    mock_repo.expect_find_by_id()
        .returning(|_| Ok(Some(create_test_user())));

    let service = UserService::new(Arc::new(mock_repo));
    let user = service.get_user(UserId::generate()).await.unwrap();
    assert_eq!(user.email().as_str(), "test@example.com");
}
```

---

## 实践建议

### 1. 从领域模型开始

- 先设计领域模型（实体、值对象、聚合），再考虑持久化
- 领域层不依赖基础设施层

### 2. 保持类型安全

- 充分利用 Rust 的类型系统
- 用新类型（newtype）包装原始类型（如 UserId, Email）
- 使用枚举表示状态和变体

### 3. 错误处理要明确

- 使用 `Result` 类型
- 用 `thiserror` 定义语义化的错误类型
- 不同层级使用不同的错误类型

### 4. 异步优先

- 后端服务优先使用 `async/await`
- 仓储和外部服务接口都应该是异步的

### 5. 依赖注入

- 通过构造函数注入依赖
- 依赖抽象（trait）而非具体实现

### 6. 测试覆盖

- 领域逻辑必须有单元测试
- 关键流程必须有集成测试
- 使用 mock 隔离外部依赖

---

## 参考资料

本文档基于以下资源整理：
- 《领域驱动设计》（Eric Evans）
- Rust 官方文档
- Rust 社区最佳实践
- 项目实际经验总结
