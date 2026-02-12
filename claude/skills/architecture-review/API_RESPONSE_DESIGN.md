# 统一API响应结构规范

> 本规范适用于 LiangX 系统所有微服务的 HTTP API 响应设计

## 核心原则

**HTTP状态码与业务状态码分层设计**：
- **HTTP状态码**（传输层）：表示HTTP请求本身是否成功处理（2xx/4xx/5xx）
- **业务状态码**（应用层）：**仅在HTTP=2xx时有效**，表示业务逻辑执行结果（0=成功，其他=业务错误）

此设计符合业界主流实践（阿里云、腾讯云、AWS）。

---

## 响应结构规范

### 1. 统一响应类型

所有API端点 **MUST** 使用以下统一结构：

```rust
/// libs/liangx-core/src/api/response.rs
pub struct ApiResponse<T> {
    /// 业务状态码（仅在HTTP=2xx时有效）
    /// 0: 成功，其他: 业务错误码
    pub code: i32,

    /// 消息描述
    pub message: String,

    /// 响应数据（成功时包含，失败时为None）
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<T>,

    /// 错误详情（可选）
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<serde_json::Value>,
}
```

### 2. 错误码分段

业务错误码采用5位数字，按服务分段：

```
0:           成功
10000-19999: 通用错误（所有服务共享）
20000-29999: Member服务
30000-39999: Merchant/Product服务
40000-49999: Trade/Order服务
50000-59999: Payment服务
60000-69999: Marketing服务
70000-79999: Inventory服务
80000-89999: Operation服务
90000-99999: Analytics服务
```

错误码定义集中在 `libs/liangx-core/src/api/error_codes.rs`。

---

## 实现要求

### 1. 导入规范

Handler文件 **MUST** 包含以下导入：

```rust
use liangx_core::{ApiResponse, error_codes};
```

### 2. Handler返回类型

**MUST** 使用以下返回类型模式：

```rust
pub async fn handler(...) -> Result<
    Json<ApiResponse<SuccessData>>,
    (StatusCode, Json<ApiResponse<()>>)
> {
    // ...
}
```

**注意**：错误响应类型通常使用 `ApiResponse<()>`，避免类型推断问题。

### 3. 成功响应

```rust
// 业务成功（HTTP 200）
Ok(Json(ApiResponse::success(data)))
```

### 4. 业务错误响应

业务错误（如余额不足、权限不足）**MUST** 返回：

```rust
// HTTP 200 + 业务错误码
Err((
    StatusCode::OK,
    Json(ApiResponse::business_error(
        error_codes::INSUFFICIENT_BALANCE,
        "会员余额不足"
    ))
))
```

### 5. 技术错误响应

技术错误（如认证失败、参数错误）**MUST** 返回：

```rust
// HTTP 4xx/5xx + 错误码
Err((
    StatusCode::UNAUTHORIZED,
    Json(ApiResponse::<()>::error(
        error_codes::UNAUTHORIZED,
        "未提供认证令牌"
    ))
))
```

**注意**：技术错误需要显式类型标注 `ApiResponse::<()>`。

---

## HTTP状态码映射

| 场景 | HTTP状态码 | 业务码 | 示例 |
|------|-----------|--------|------|
| 业务成功 | 200 OK | 0 | 查询成功 |
| 业务错误 | 200 OK | 非0 | 余额不足、商品售罄 |
| 参数错误 | 400 Bad Request | 10002 | 参数格式错误 |
| 未认证 | 401 Unauthorized | 10003 | 缺少token |
| 权限不足 | 403 Forbidden | 10004 | 非管理员 |
| 资源不存在 | 404 Not Found | 10005 | 会员不存在 |
| 服务器错误 | 500 Internal Server Error | 10001 | 数据库连接失败 |

---

## 错误码选择原则

1. **优先使用通用错误码**（10000-19999）：
   - `NOT_FOUND` (10005)
   - `INVALID_PARAM` (10002)
   - `UNAUTHORIZED` (10003)
   - `FORBIDDEN` (10004)

2. **服务专属错误使用服务段错误码**：
   - Member服务：20000-29999
   - Trade服务：40000-49999
   - 等等

3. **错误消息 MUST 清晰具体**：
   - ✅ "会员余额不足100积分，当前余额50积分"
   - ❌ "NullPointerException at line 123"

---

## 常见实现问题

### 问题1：类型推断失败

```rust
// ❌ 错误
let body = Json(ApiResponse::error(code, message));
// 编译错误：cannot infer type of the type parameter `T`

// ✅ 正确
let body = Json(ApiResponse::<()>::error(code, message));
```

### 问题2：方法签名变更

从旧格式迁移时注意：

```rust
// 旧代码（1个参数）
ApiResponse::error("错误消息".to_string())

// 新代码（2个参数）
ApiResponse::error(error_codes::INTERNAL_ERROR, "错误消息")
```

---

## 实施检查清单

迁移现有服务或实现新端点时，**MUST** 确认：

- [ ] 已导入 `use liangx_core::{ApiResponse, error_codes};`
- [ ] Handler返回类型符合规范
- [ ] 成功响应使用 `ApiResponse::success(data)`
- [ ] 业务错误返回 HTTP 200 + `business_error()`
- [ ] 技术错误返回正确的 HTTP 4xx/5xx + `error()`
- [ ] 错误码选择合理（通用 vs 服务专属）
- [ ] 错误消息清晰具体
- [ ] 编译通过，无类型推断错误

---

## 前端集成

前端 **SHOULD** 使用以下模式处理响应：

```typescript
async function request<T>(url: string): Promise<T> {
  const response = await fetch(url);
  const json: ApiResponse<T> = await response.json();

  if (response.ok && json.code === 0) {
    return json.data!;
  } else if (response.ok && json.code !== 0) {
    throw new BusinessError(json.code, json.message);
  } else {
    throw new TechnicalError(response.status, json.message);
  }
}
```

---

## 参考资料

- 错误码定义：`libs/liangx-core/src/api/error_codes.rs`
- 响应结构实现：`libs/liangx-core/src/api/response.rs`
- 云服务商API设计：阿里云、腾讯云、AWS API规范

**文档版本**: v1.0
**最后更新**: 2024-01-14
