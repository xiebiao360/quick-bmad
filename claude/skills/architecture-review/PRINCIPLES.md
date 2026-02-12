# 软件架构设计原则参考

本文档沉淀核心设计原则、最佳实践和常见模式，作为架构决策的参考依据。

**重要提示**：
- 本文档主要针对通用设计原则和前端开发
- **对于 Rust 后端代码，请优先参考 `RUST_DDD_REFERENCE.md`**，该文档提供了针对 Rust 语言特性的 DDD 和 OOP 实践指南

---

## 第一性原理（First Principles）

### 什么是第一性原理？

第一性原理是一种思维方式：回归事物最基本的真理，从根本出发推导，而不是基于类比、经验或惯例。

### 在软件架构中的应用

**错误的思维方式**：
- "其他项目都这么做，我们也这么做"
- "之前一直这样写，现在也继续"
- "框架推荐这种方式，就用这种"

**正确的思维方式**：
- "我们要解决的核心问题是什么？"
- "这个问题的本质是什么？"
- "从根本上看，最简单有效的解决方案是什么？"
- "为什么这个方案比其他方案更好？"

### 实践案例

**场景**：用户认证状态管理

- **表象做法**：因为大家都用 Redux/Vuex，所以也用全局状态管理
- **第一性原理分析**：
  - 核心问题：多个组件需要知道用户是否登录
  - 本质需求：共享状态 + 状态变更通知
  - 最简方案：Context API（React）或 Provide/Inject（Vue）可能就够了
  - 引入复杂状态管理的成本是否值得？取决于应用规模和复杂度

---

## DDD（领域驱动设计）原则

### 核心概念

DDD 的核心是将业务领域知识映射到软件设计中，让代码结构反映业务结构。

### 分层架构

```
┌─────────────────────────────────────┐
│      接口层 (Interface Layer)      │  ← 用户界面、API 端点
├─────────────────────────────────────┤
│      应用层 (Application Layer)    │  ← 用例编排、流程控制
├─────────────────────────────────────┤
│      领域层 (Domain Layer)         │  ← 核心业务逻辑
├─────────────────────────────────────┤
│   基础设施层 (Infrastructure)      │  ← 数据库、外部服务
└─────────────────────────────────────┘
```

#### 各层职责

**接口层（Interface Layer）**
- 职责：处理 HTTP 请求/响应、命令行交互、UI 渲染
- 原则：薄层，仅负责数据转换和调用应用层
- 反例：在 Controller 里写业务逻辑

**应用层（Application Layer）**
- 职责：编排用例、协调领域对象、处理事务
- 原则：无业务规则，只有流程控制
- 示例：`UserRegistrationService.register()`

**领域层（Domain Layer）**
- 职责：核心业务逻辑、业务规则、领域模型
- 原则：不依赖外部技术，纯业务逻辑
- 示例：`User.changePassword()`, `Order.calculateTotal()`

**基础设施层（Infrastructure Layer）**
- 职责：技术实现细节（数据库、消息队列、文件系统）
- 原则：可替换，领域层通过接口依赖
- 示例：`UserRepositoryImpl`, `EmailServiceImpl`

### 领域模型设计

#### 实体（Entity）
- 有唯一标识的对象
- 生命周期中标识不变，属性可变
- 示例：User、Order、Product

#### 值对象（Value Object）
- 无唯一标识，完全由属性定义
- 不可变（immutable）
- 示例：Money、Address、Email

#### 聚合（Aggregate）
- 一组相关对象的集合，有明确的边界
- 通过聚合根（Aggregate Root）访问
- 示例：Order（聚合根）+ OrderItem（聚合内对象）

#### 领域服务（Domain Service）
- 不属于任何实体或值对象的业务逻辑
- 示例：TransferService（跨账户转账）

#### 仓储（Repository）
- 领域对象的持久化抽象
- 提供类似集合的接口
- 示例：`UserRepository.findById(id)`

### DDD 实践原则

1. **面向领域建模，而非数据库建模**
   - 先设计领域模型，再考虑持久化
   - 不要让数据库表结构决定领域模型

2. **保持领域层的纯粹性**
   - 领域层不依赖框架、数据库、UI
   - 核心业务逻辑可独立测试

3. **通过接口解耦**
   - 领域层定义接口，基础设施层实现
   - 示例：`IUserRepository`（领域层） ← `UserRepositoryImpl`（基础设施层）

4. **统一语言（Ubiquitous Language）**
   - 代码中的命名与业务人员的术语一致
   - 避免技术术语污染业务概念

---

## API响应结构设计原则

### HTTP状态码与业务状态码分层

**核心思想**：两者工作在不同层面，互补而非冲突。

**HTTP状态码（传输层/技术层）**：
- 表示HTTP请求本身是否成功处理
- `2xx`：请求成功处理（可能包含业务错误）
- `4xx`：客户端请求错误（认证失败、参数格式错误）
- `5xx`：服务器技术错误（崩溃、不可用）

**业务状态码（应用层）**：
- **仅在HTTP=2xx的前提下**，表示业务逻辑执行结果
- `code=0`：业务成功
- `code!=0`：业务失败（余额不足、商品售罄、会员冻结等）

### 实践要点

1. **业务错误返回HTTP 200**
   - 余额不足、库存不足、权限不足等业务错误
   - HTTP 200 + 业务错误码

2. **技术错误返回HTTP 4xx/5xx**
   - 认证失败 → HTTP 401
   - 参数格式错误 → HTTP 400
   - 服务器内部错误 → HTTP 500

3. **错误消息清晰具体**
   - 面向用户的业务错误消息
   - 不暴露技术栈信息

4. **前端分层处理**
   - 业务错误：用户友好提示
   - 技术错误：系统错误提示或重定向

**参考文档**：`.claude/skills/architecture-review/API_RESPONSE_DESIGN.md`

---

## SOLID 原则

### S - 单一职责原则（Single Responsibility Principle）

**定义**：一个类应该只有一个引起它变化的原因。

**实践**：
- 每个模块、类、函数只做一件事
- 如果一个类承担多个职责，职责间的变化会相互影响

**反例**：
```typescript
// ❌ UserService 承担太多职责
class UserService {
  register() { /* 注册逻辑 */ }
  sendEmail() { /* 邮件发送 */ }
  saveToDatabase() { /* 数据库操作 */ }
  generateReport() { /* 报表生成 */ }
}
```

**正例**：
```typescript
// ✓ 职责分离
class UserRegistrationService {
  register() { /* 注册逻辑 */ }
}

class EmailService {
  send() { /* 邮件发送 */ }
}

class UserRepository {
  save() { /* 数据库操作 */ }
}
```

### O - 开闭原则（Open-Closed Principle）

**定义**：软件实体应该对扩展开放，对修改关闭。

**实践**：
- 通过抽象和多态实现扩展
- 新增功能时不修改已有代码

**示例**：
```typescript
// ✓ 通过策略模式实现开闭原则
interface PaymentStrategy {
  pay(amount: number): void;
}

class CreditCardPayment implements PaymentStrategy {
  pay(amount: number) { /* 信用卡支付 */ }
}

class AlipayPayment implements PaymentStrategy {
  pay(amount: number) { /* 支付宝支付 */ }
}

// 新增支付方式时，无需修改已有代码，只需新增实现类
```

### L - 里氏替换原则（Liskov Substitution Principle）

**定义**：子类对象应该能够替换父类对象，程序行为不变。

**实践**：
- 子类不应该违反父类的契约
- 子类不应该抛出父类未声明的异常
- 子类不应该加强前置条件或削弱后置条件

### I - 接口隔离原则（Interface Segregation Principle）

**定义**：客户端不应该依赖它不需要的接口。

**实践**：
- 接口应该小而专注
- 避免"胖接口"

**反例**：
```typescript
// ❌ 胖接口
interface Worker {
  work(): void;
  eat(): void;
  sleep(): void;
}

// Robot 不需要 eat() 和 sleep()，但被迫实现
class Robot implements Worker {
  work() { /* 工作 */ }
  eat() { throw new Error('Robot cannot eat'); }
  sleep() { throw new Error('Robot cannot sleep'); }
}
```

**正例**：
```typescript
// ✓ 接口隔离
interface Workable {
  work(): void;
}

interface Eatable {
  eat(): void;
}

interface Sleepable {
  sleep(): void;
}

class Robot implements Workable {
  work() { /* 工作 */ }
}

class Human implements Workable, Eatable, Sleepable {
  work() { /* 工作 */ }
  eat() { /* 吃饭 */ }
  sleep() { /* 睡觉 */ }
}
```

### D - 依赖倒置原则（Dependency Inversion Principle）

**定义**：
- 高层模块不应该依赖低层模块，两者都应该依赖抽象
- 抽象不应该依赖细节，细节应该依赖抽象

**实践**：
- 依赖接口而非具体实现
- 使用依赖注入

**反例**：
```typescript
// ❌ 高层依赖低层具体实现
class UserService {
  private repo = new MySQLUserRepository(); // 直接依赖具体实现
  
  getUser(id: string) {
    return this.repo.findById(id);
  }
}
```

**正例**：
```typescript
// ✓ 依赖抽象
interface IUserRepository {
  findById(id: string): User;
}

class UserService {
  constructor(private repo: IUserRepository) {} // 依赖注入
  
  getUser(id: string) {
    return this.repo.findById(id);
  }
}

// 具体实现可替换
class MySQLUserRepository implements IUserRepository { /* ... */ }
class MongoUserRepository implements IUserRepository { /* ... */ }
```

---

## 前端架构最佳实践

### React 最佳实践

#### 组件设计原则

1. **组件职责单一**
   - 一个组件只做一件事
   - 复杂组件拆分成多个小组件

2. **容器组件与展示组件分离**
   - 容器组件（Smart Component）：处理逻辑、状态管理
   - 展示组件（Dumb Component）：只负责渲染，接收 props

3. **组件组合优于继承**
   - 使用 children 和组合模式
   - 避免类组件继承

#### Hooks 使用规范

**useState / useReducer**
```typescript
// ✓ 相关状态合并
const [user, setUser] = useState({ name: '', age: 0 });

// ✗ 过度拆分
const [userName, setUserName] = useState('');
const [userAge, setUserAge] = useState(0);

// ✓ 复杂状态使用 useReducer
const [state, dispatch] = useReducer(reducer, initialState);
```

**useEffect**
```typescript
// ✓ 依赖项完整
useEffect(() => {
  fetchData(userId);
}, [userId]); // userId 改变时重新执行

// ✗ 缺少依赖项（可能导致 bug）
useEffect(() => {
  fetchData(userId);
}, []); // userId 改变时不会重新执行
```

**useMemo / useCallback**
```typescript
// ✓ 优化昂贵计算
const expensiveResult = useMemo(() => {
  return computeExpensiveValue(a, b);
}, [a, b]);

// ✓ 避免子组件不必要的重渲染
const handleClick = useCallback(() => {
  doSomething(a);
}, [a]);

// ✗ 过度使用（简单计算不需要 useMemo）
const sum = useMemo(() => a + b, [a, b]); // 不必要
```

**自定义 Hooks**
```typescript
// ✓ 复用逻辑
function useUser(userId: string) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchUser(userId).then(setUser).finally(() => setLoading(false));
  }, [userId]);
  
  return { user, loading };
}

// 使用
const { user, loading } = useUser('123');
```

#### 状态管理策略

**选择合适的状态管理方案**：
- 简单应用：useState + Context API
- 中等复杂度：Zustand、Jotai
- 复杂应用：Redux Toolkit

**状态放置原则**：
- 组件私有状态：useState
- 跨组件共享：提升到共同父组件或 Context
- 全局状态：全局状态管理库

#### 性能优化

1. **React.memo**：避免不必要的重渲染
2. **懒加载**：`React.lazy()` + `Suspense`
3. **虚拟列表**：长列表使用 react-window 或 react-virtualized
4. **代码分割**：按路由或功能分割

### Vue 最佳实践

#### Composition API 使用规范

```typescript
// ✓ 按功能组织代码
export default defineComponent({
  setup() {
    // 用户相关逻辑
    const { user, fetchUser } = useUser();
    
    // 权限相关逻辑
    const { hasPermission } = usePermission();
    
    // 表单相关逻辑
    const { form, handleSubmit } = useForm();
    
    return { user, hasPermission, form, handleSubmit };
  }
});
```

#### 组件通信

- **父子通信**：props + emit
- **跨层级通信**：provide / inject
- **全局状态**：Pinia

### 通用前端原则

1. **类型安全**：充分使用 TypeScript
2. **样式隔离**：CSS Modules、Styled Components、Scoped CSS
3. **错误边界**：捕获和处理组件错误
4. **无障碍性（A11y）**：语义化 HTML、ARIA 属性、键盘导航

---

## 常见反模式（Anti-patterns）

### 1. 上帝对象（God Object）
**问题**：一个类承担太多职责，成为系统的中心
**解决**：拆分职责，遵循单一职责原则

### 2. 循环依赖（Circular Dependency）
**问题**：模块 A 依赖 B，B 又依赖 A
**解决**：引入中间层，或重新设计模块边界

### 3. 硬编码（Hard Coding）
**问题**：魔法数字、固定的配置值散落在代码中
**解决**：提取常量、配置文件

### 4. 过早优化（Premature Optimization）
**问题**：在没有性能问题时就进行复杂优化
**解决**：先保证正确性，再根据 profiling 结果优化

### 5. 过度设计（Over-engineering）
**问题**：为了可能的未来需求，设计过于复杂的架构
**解决**：YAGNI（You Aren't Gonna Need It），只实现当前需要的

### 6. 意大利面代码（Spaghetti Code）
**问题**：逻辑混乱，控制流难以追踪
**解决**：清晰的分层，职责分离

### 7. Copy-Paste 编程
**问题**：重复代码散落各处
**解决**：提取公共逻辑，复用

---

## 架构决策记录模板（ADR）

当做重要架构决策时，可以记录：

```markdown
# ADR-001: [决策标题]

## 状态
[提议中 / 已接受 / 已弃用]

## 背景
[为什么需要做这个决策？当前面临什么问题？]

## 决策
[我们决定采用什么方案？]

## 理由
[为什么选择这个方案？]
- 优点 1
- 优点 2
- 考虑了其他方案，但...

## 后果
[这个决策会带来什么影响？]
- 正面影响
- 负面影响（需要权衡）

## 替代方案
[考虑过哪些其他方案？为什么没选？]
```

---

## 持续改进

本文档应该随着项目经验不断完善：
- 发现新的设计模式时，补充到文档
- 踩过的坑，记录为反模式
- 成功的架构决策，总结为原则

**重要提醒**：原则是指导，不是教条。根据实际情况灵活应用，避免为了原则而原则。
