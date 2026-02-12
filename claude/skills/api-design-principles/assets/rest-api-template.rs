//! 生产级 REST API 模板（使用 Axum）
//! 包含分页、过滤、错误处理和最佳实践

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Json, Response},
    routing::{delete, get, patch, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::net::TcpListener;
use tower_http::cors::{Any, CorsLayer};
use validator::Validate;

// ========== 数据模型 ==========

/// 用户状态枚举
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum UserStatus {
    Active,
    Inactive,
    Suspended,
}

/// 用户基础模型
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserBase {
    pub email: String,
    pub name: String,
    pub status: UserStatus,
}

/// 创建用户请求
#[derive(Debug, Deserialize, Validate)]
pub struct UserCreate {
    #[validate(email(message = "Invalid email format"))]
    pub email: String,
    #[validate(length(min = 1, max = 100, message = "Name must be 1-100 characters"))]
    pub name: String,
    #[validate(length(min = 8, message = "Password must be at least 8 characters"))]
    pub password: String,
    #[serde(default = "default_user_status")]
    pub status: UserStatus,
}

fn default_user_status() -> UserStatus {
    UserStatus::Active
}

/// 更新用户请求（部分更新）
#[derive(Debug, Deserialize, Validate)]
pub struct UserUpdate {
    #[validate(email(message = "Invalid email format"))]
    pub email: Option<String>,
    #[validate(length(min = 1, max = 100))]
    pub name: Option<String>,
    pub status: Option<UserStatus>,
}

/// 用户完整模型（包含系统字段）
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: String,
    pub email: String,
    pub name: String,
    pub status: UserStatus,
    pub created_at: String,
    pub updated_at: String,
}

// ========== 分页相关 ==========

/// 分页查询参数
#[derive(Debug, Deserialize)]
pub struct PaginationParams {
    #[serde(default = "default_page")]
    pub page: i64,
    #[serde(default = "default_page_size")]
    pub page_size: i64,
}

fn default_page() -> i64 {
    1
}

fn default_page_size() -> i64 {
    20
}

/// 用户列表查询参数
#[derive(Debug, Deserialize)]
pub struct ListUsersQuery {
    #[serde(default = "default_page")]
    pub page: i64,
    #[serde(default = "default_page_size")]
    pub page_size: i64,
    pub status: Option<UserStatus>,
    pub search: Option<String>,
}

/// 分页响应
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
        Self {
            items,
            total,
            page,
            page_size,
            pages,
        }
    }

    pub fn has_next(&self) -> bool {
        self.page < self.pages
    }

    pub fn has_prev(&self) -> bool {
        self.page > 1
    }
}

// ========== 统一响应格式 ==========

/// API 统一响应结构
#[derive(Debug, Serialize)]
pub struct ApiResponse<T> {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<T>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<ApiError>,
}

impl<T> ApiResponse<T> {
    pub fn success(data: T) -> Self {
        Self {
            data: Some(data),
            error: None,
        }
    }

    pub fn error(code: u16, message: String) -> ApiResponse<()> {
        ApiResponse {
            data: None,
            error: Some(ApiError {
                code,
                message,
                details: None,
            }),
        }
    }
}

/// API 错误详情
#[derive(Debug, Serialize)]
pub struct ApiError {
    pub code: u16,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<Vec<ErrorDetail>>,
}

/// 字段级错误详情
#[derive(Debug, Serialize)]
pub struct ErrorDetail {
    pub field: Option<String>,
    pub message: String,
}

// ========== 应用状态 ==========

#[derive(Clone)]
pub struct AppState {
    // 在实际应用中，这里会包含数据库连接池、Redis 客户端等
}

// ========== 路由处理器 ==========

/// 列出用户（分页和过滤）
async fn list_users(
    State(_state): State<Arc<AppState>>,
    Query(query): Query<ListUsersQuery>,
) -> Result<Json<ApiResponse<PaginatedResponse<User>>>, AppError> {
    // 验证分页参数
    if query.page < 1 {
        return Err(AppError::BadRequest("page must be >= 1".to_string()));
    }
    if query.page_size < 1 || query.page_size > 100 {
        return Err(AppError::BadRequest(
            "page_size must be between 1 and 100".to_string(),
        ));
    }

    // TODO: 从数据库查询数据
    // 这里使用模拟数据
    let total = 100;
    let start = ((query.page - 1) * query.page_size) as usize;
    let end = (query.page * query.page_size).min(total) as usize;

    let mut items = Vec::new();
    for i in start..end {
        items.push(User {
            id: i.to_string(),
            email: format!("user{}@example.com", i),
            name: format!("User {}", i),
            status: UserStatus::Active,
            created_at: "2024-01-01T00:00:00Z".to_string(),
            updated_at: "2024-01-01T00:00:00Z".to_string(),
        });
    }

    let response = PaginatedResponse::new(items, total, query.page, query.page_size);
    Ok(Json(ApiResponse::success(response)))
}

/// 创建用户
async fn create_user(
    State(_state): State<Arc<AppState>>,
    Json(payload): Json<UserCreate>,
) -> Result<(StatusCode, Json<ApiResponse<User>>), AppError> {
    // 验证输入
    payload
        .validate()
        .map_err(|e| AppError::ValidationError(format!("{}", e)))?;

    // TODO: 保存到数据库
    let user = User {
        id: "123".to_string(),
        email: payload.email,
        name: payload.name,
        status: payload.status,
        created_at: "2024-01-01T00:00:00Z".to_string(),
        updated_at: "2024-01-01T00:00:00Z".to_string(),
    };

    Ok((StatusCode::CREATED, Json(ApiResponse::success(user))))
}

/// 获取单个用户
async fn get_user(
    State(_state): State<Arc<AppState>>,
    Path(user_id): Path<String>,
) -> Result<Json<ApiResponse<User>>, AppError> {
    // TODO: 从数据库查询
    // 模拟：如果 ID 为 "999" 则返回 404
    if user_id == "999" {
        return Err(AppError::NotFound(format!(
            "User with id {} not found",
            user_id
        )));
    }

    let user = User {
        id: user_id,
        email: "user@example.com".to_string(),
        name: "User Name".to_string(),
        status: UserStatus::Active,
        created_at: "2024-01-01T00:00:00Z".to_string(),
        updated_at: "2024-01-01T00:00:00Z".to_string(),
    };

    Ok(Json(ApiResponse::success(user)))
}

/// 部分更新用户
async fn update_user(
    State(_state): State<Arc<AppState>>,
    Path(user_id): Path<String>,
    Json(payload): Json<UserUpdate>,
) -> Result<Json<ApiResponse<User>>, AppError> {
    // 验证输入
    payload
        .validate()
        .map_err(|e| AppError::ValidationError(format!("{}", e)))?;

    // TODO: 从数据库查询现有用户
    if user_id == "999" {
        return Err(AppError::NotFound(format!(
            "User with id {} not found",
            user_id
        )));
    }

    // TODO: 应用更新并保存到数据库
    let user = User {
        id: user_id,
        email: payload.email.unwrap_or("user@example.com".to_string()),
        name: payload.name.unwrap_or("User Name".to_string()),
        status: payload.status.unwrap_or(UserStatus::Active),
        created_at: "2024-01-01T00:00:00Z".to_string(),
        updated_at: "2024-01-01T00:00:00Z".to_string(),
    };

    Ok(Json(ApiResponse::success(user)))
}

/// 删除用户
async fn delete_user(
    State(_state): State<Arc<AppState>>,
    Path(user_id): Path<String>,
) -> Result<StatusCode, AppError> {
    // TODO: 从数据库删除
    if user_id == "999" {
        return Err(AppError::NotFound(format!(
            "User with id {} not found",
            user_id
        )));
    }

    Ok(StatusCode::NO_CONTENT)
}

// ========== 错误处理 ==========

/// 应用错误类型
#[derive(Debug)]
pub enum AppError {
    NotFound(String),
    BadRequest(String),
    ValidationError(String),
    InternalError(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, msg),
            AppError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg),
            AppError::ValidationError(msg) => (StatusCode::UNPROCESSABLE_ENTITY, msg),
            AppError::InternalError(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
        };

        let body = Json(ApiResponse::<()>::error(status.as_u16(), message));
        (status, body).into_response()
    }
}

// ========== 应用初始化 ==========

fn app_router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/api/users", get(list_users).post(create_user))
        .route(
            "/api/users/:user_id",
            get(get_user).patch(update_user).delete(delete_user),
        )
        .with_state(state)
        .layer(
            CorsLayer::new()
                .allow_origin(Any) // TODO: 生产环境需要配置具体的允许源
                .allow_methods(Any)
                .allow_headers(Any),
        )
}

#[tokio::main]
async fn main() {
    // 初始化日志
    tracing_subscriber::fmt::init();

    // 创建应用状态
    let state = Arc::new(AppState {});

    // 创建路由
    let app = app_router(state);

    // 启动服务器
    let listener = TcpListener::bind("0.0.0.0:8000").await.unwrap();
    tracing::info!("Server listening on {}", listener.local_addr().unwrap());

    axum::serve(listener, app).await.unwrap();
}
