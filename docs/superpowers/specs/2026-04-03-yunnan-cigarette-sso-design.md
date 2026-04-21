# 云南中烟单点登录接入设计文档

> 日期: 2026-04-03
> 模块: 用户认证 / 单点登录（双登录并存）
> 展示名称: 云南中烟登录

## 1. 目标与边界

在保留现有本地用户名密码登录的前提下，新增“云南中烟登录”入口，接入用户提供的单点登录集成指南对应的 OIDC / OAuth2 授权码模式。

本次仅产出设计方案，不实施代码。

### 1.1 已确认约束

- 登录模式：双登录并存
- 展示名称：云南中烟登录
- 首次 SSO 登录：自动创建本地账号
- 默认权限：普通用户（worker）
- 唯一标识：工号 / 员工编号
- 退出策略：只退出本系统，不联动退出 SSO
- 部署形态：生产环境使用固定域名，可提前注册 redirect_uri
- 现有接入文档仍然有效，仅修改界面展示名称

### 1.2 非目标

- 不替换现有本地登录接口
- 不把本系统角色权限交给外部 SSO 决定
- 不在前端保存 access_token / refresh_token
- 不在本阶段实现全局单点退出

## 2. 现状分析

### 2.1 当前认证方式

当前系统已采用 Django Session 作为登录态载体：

- 后端登录接口：`backend/apps/users/views.py:43`
- 当前用户接口：`backend/apps/users/views.py:69`
- DRF 认证方式：`backend/config/settings/base.py:101`
- 前端路由守卫通过 `usersApi.me()` 恢复登录态：`frontend/src/router/index.ts:150`
- 前端登录页为本地用户名密码表单：`frontend/src/views/login/LoginView.vue:12`

### 2.2 当前用户模型约束

- Django `User.username` 必填且唯一
- 姓名当前使用 `User.first_name`
- 角色通过 `groups` 映射：安全员 / 班组长 / 员工
- 工号存储于 `UserProfile.employee_id`：`backend/apps/users/models.py:11`
- `employee_id` 已具备唯一约束，可作为 SSO 匹配主键

## 3. 方案选择

采用 **后端主导的 OIDC 授权码闭环**。

### 3.1 方案说明

用户点击“云南中烟登录”后，浏览器先访问本系统后端发起登录接口；后端再重定向到统一认证中心。认证成功后，回调同样先落到后端，由后端完成：

1. `state` 校验
2. `code` 换取 token
3. 获取用户信息
4. 依据工号匹配 / 创建本地用户
5. 建立 Django session
6. 重定向回前端业务页

### 3.2 选型理由

- 与现有 `SessionAuthentication` 架构完全兼容
- `client_secret` 仅保存在后端，安全性更高
- 前端不需要理解和维护 OIDC token 生命周期
- 双登录并存下，对现有本地登录链路影响最小
- 后续审计、账号映射、权限治理更清晰

## 4. 总体架构

### 4.1 认证职责划分

- **SSO 系统**：负责外部身份认证
- **本系统后端**：负责账号映射、自动建号、权限保留、会话建立
- **本系统前端**：只负责展示双入口和消费现有登录态

### 4.2 核心原则

- 双入口并存：本地登录 + 云南中烟登录
- 登录收口统一：最终全部落到 Django session
- 权限仍由本系统本地角色控制
- 首次登录自动建号，但默认最低权限
- SSO 只负责“认人”，不负责“改权”

## 5. 登录流程设计

### 5.1 发起登录

前端登录页新增“云南中烟登录”按钮，点击后跳转：

- `GET /api/users/sso/login/`

后端在该接口中：

1. 生成随机 `state`
2. 将 `state` 写入 session 中的待消费集合，而不是单个固定值
3. 为每个 `state` 记录创建时间、可选的 `next` 和一次性消费标记
4. 拼接认证中心授权地址
5. 302 跳转到 SSO 登录页

授权请求至少包含：

- `client_id`
- `redirect_uri`
- `response_type=code`
- `scope`
- `state`

`state` 设计要求：

- 支持多标签页或重复点击并发发起登录
- 每个 `state` 仅可消费一次
- 设置短 TTL，超时即失效
- 回调成功或失败后都要清理已消费 / 已过期记录

### 5.2 回调处理

SSO 认证完成后，浏览器回到：

- `GET /api/users/sso/callback/?code=...&state=...`

后端处理顺序：

1. 校验 `state`
2. 使用 `code` 请求 token 接口
3. 对返回凭证做最小 OIDC / token 有效性校验
4. 使用合法 token 请求用户信息接口
5. 解析工号、姓名、登录名等关键字段
6. 按工号匹配或创建本地用户
7. 检查账号是否启用
8. 调用 Django `login(request, user)`
9. 清理临时 state
10. 重定向到前端目标页

凭证校验要求：

- 至少校验 `iss`、`aud`、`exp`
- 如果接入流程使用 `id_token` 作为身份断言来源，则必须校验签名与相关声明
- 如果后续发现指南明确要求 `nonce`，则一并纳入发起登录与回调校验
- 不允许“拿到 token 就直接信任用户身份”

### 5.3 成功后的跳转

- 默认跳转：`/dashboard`
- 如果登录前带了 `next`，则跳回对应站内相对路径
- `next` 必须限制为站内相对路径，禁止开放重定向

### 5.4 退出策略

继续沿用现有：

- `POST /api/users/logout/`

只清除本系统 session，不调用外部 SSO logout 接口。

## 6. 用户映射与自动建号规则

### 6.1 唯一匹配键

以 `UserProfile.employee_id` 作为本地用户唯一匹配字段。

匹配规则：

1. 查询 `profile.employee_id == SSO工号`
2. 若存在，直接登录该本地账号
3. 若不存在，自动创建本地账号与 profile

### 6.2 自动创建策略

首次 SSO 登录且未匹配到本地账号时：

- 创建 Django `User`
- 创建 `UserProfile`
- `employee_id` 写入 profile
- `first_name` 写入 SSO 返回姓名
- 默认加入本地 `员工` group（即 `worker` 角色）
- 账号默认启用
- 设置不可用密码：`set_unusable_password()`

### 6.3 username 生成规则

推荐默认直接使用工号作为 `username`。

兼容规则：

1. 优先尝试 `username = employee_id`
2. 如果发生用户名冲突但 profile 不属于同一人，则回退到：
   - `sso_<employee_id>` 或
   - `ynzy_<employee_id>`

实际实现时应把该规则封装为单独方法，避免散落在 view 中。

### 6.4 权限策略

- 新自动创建用户：默认加入本地 `员工` group，对应 `worker` 角色
- 已存在用户：保留原有角色，不被 SSO 覆盖
- SSO 不自动同步本地分组和管理权限
- 角色判断继续沿用现有 `groups -> role` 推导方式，不新增独立 `role` 字段

## 7. 接口与模块设计

### 7.1 后端新增接口

建议在 `backend/apps/users/urls.py` 下新增：

- `GET /api/users/sso/login/`：发起登录跳转
- `GET /api/users/sso/callback/`：处理回调并建立 session
- `GET /api/users/sso/config/`（可选）：返回前端展示配置

首期不是必须新增 logout 接口。

### 7.2 后端内部模块拆分

建议新增服务层，避免所有逻辑堆入 `views.py`：

1. **SSO 配置读取模块**
   - 统一读取 settings / env 中的 SSO 配置
2. **OIDC 客户端模块**
   - 生成授权 URL
   - `code -> token`
   - `token -> userinfo`
3. **用户映射模块**
   - 解析外部用户信息
   - 按工号匹配本地用户
   - 自动创建账号与 profile
4. **登录收口模块**
   - 统一建立 session 并返回跳转结果

建议文件形态：

- `backend/apps/users/services/sso.py`
- `backend/apps/users/services/user_provisioning.py`

如不想拆过多文件，也至少要抽函数，不建议把 HTTP 请求、映射逻辑、登录逻辑全部混在单个 view 中。

### 7.3 前端改动

主要改动集中在登录页：

- `frontend/src/views/login/LoginView.vue`
  - 保留现有用户名密码表单
  - 新增“云南中烟登录”按钮
  - 点击跳转应复用当前前后端部署方式：
    - 同域部署时可直接访问 `/api/users/sso/login/`
    - 若项目继续存在可配置 API 基址，则应通过统一 API 基址配置拼接完整登录发起地址，避免硬编码相对路径
  - 支持显示 SSO 回流错误提示（通过 query 参数）

前端路由守卫原则上无需重写：

- SSO 登录成功后，后端已经建好 session
- 前端仍通过 `usersApi.me()` 判断登录状态

## 8. 配置设计

建议新增后端环境变量：

- `SSO_ENABLED`
- `SSO_BASE_URL`
- `SSO_CLIENT_ID`
- `SSO_CLIENT_SECRET`
- `SSO_REDIRECT_URI`
- `SSO_SCOPE`
- `SSO_AUTHORIZE_URL`（可选，若不从 base_url 拼接）
- `SSO_TOKEN_URL`（可选）
- `SSO_USERINFO_URL`（可选）
- `SSO_INTROSPECT_URL`（可选，首期可不启用）

配置原则：

- `client_secret` 只存在于后端
- `redirect_uri` 使用固定域名配置
- 不允许前端提交任意回调地址

## 9. 安全设计

### 9.1 必做安全项

1. **state 校验**
   - 登录前生成随机 `state`
   - 写入 session
   - 回调严格比对
   - 用后删除

2. **固定 redirect_uri**
   - 后端配置固定值，不从前端透传完整 URL

3. **next 白名单校验**
   - 仅允许站内相对路径，如 `/dashboard`
   - 禁止外部域名与协议跳转

4. **工号缺失拒绝登录**
   - 未拿到工号不得自动建号

5. **不自动覆盖本地高权限信息**
   - 不在每次 SSO 登录时回写角色 / 分组

6. **自动创建账号默认最低权限**
   - 避免误授安全员或班组长权限

### 9.2 不建议首期实现的项

- 前端持久化 OIDC token
- 用外部 token 直接访问后端业务接口
- 把 SSO 返回的组织岗位字段直接映射高权限角色
- SSO 全局退出联动

## 10. 异常处理设计

### 10.1 主要失败场景

- 用户取消认证
- `state` 校验失败
- token 接口调用失败
- 用户信息接口调用失败
- SSO 返回数据缺少工号
- 自动建号失败
- 本地账号被禁用

### 10.2 用户可见处理方式

回调失败后，后端不直接暴露原始异常，而是重定向回登录页，例如：

- `/login?sso_error=state_invalid`
- `/login?sso_error=token_exchange_failed`
- `/login?sso_error=employee_id_missing`
- `/login?sso_error=account_disabled`

前端登录页根据 query 参数展示友好中文提示。

### 10.3 日志要求

后端需记录关键审计日志：

- SSO 登录发起
- token 交换失败原因
- 用户信息解析失败原因
- 自动创建账号结果
- 登录成功用户与工号

日志中不得打印敏感 token 明文。

## 11. 文件变更清单（实施阶段）

### 11.1 后端

建议修改 / 新增：

- `backend/config/settings/base.py`
  - 新增 SSO 配置读取
- `backend/apps/users/urls.py`
  - 新增 `/sso/login/`、`/sso/callback/`
- `backend/apps/users/views.py`
  - 新增 SSO 入口视图
- `backend/apps/users/services/sso.py`（建议新增）
  - OIDC 请求与响应处理
- `backend/apps/users/services/user_provisioning.py`（建议新增）
  - 工号匹配、自动建号、默认角色处理

### 11.2 前端

建议修改：

- `frontend/src/views/login/LoginView.vue`
  - 增加“云南中烟登录”按钮
  - 增加 SSO 错误提示
- `frontend/src/api/users.ts`
  - 如需配置接口，可新增 `ssoConfig()`；否则可不改

## 12. 测试方案

### 12.1 正常流程

1. 点击“云南中烟登录”可跳转到认证中心
2. 认证成功后可回到系统并建立 session
3. 已存在工号用户可正常登录
4. 不存在工号用户首次登录时自动建号成功
5. 自动建号后角色为普通用户
6. 登录成功后 `me()` 返回正确用户信息
7. 页面刷新后登录态可恢复

### 12.2 异常流程

8. `state` 不匹配时拒绝登录
9. token 交换失败时回到登录页并提示
10. 用户信息接口失败时回到登录页并提示
11. SSO 返回无工号时拒绝登录
12. 本地禁用账号无法通过 SSO 进入系统
13. 恶意外链 `next` 参数被拦截

### 12.3 兼容性验证

14. 现有本地用户名密码登录仍正常
15. 用户管理页面可查看新自动创建账号
16. 安全员后续可手动调整新账号角色
17. 本地退出后仅退出本系统，不影响外部 SSO 登录态

## 13. 风险与前置确认

实施前仍需核对单点登录文档中的用户信息字段名，确认以下映射：

- 工号字段名
- 姓名字段名
- 登录名字段名
- 是否存在手机号、部门等附加字段

若指南返回字段名称与预期不一致，应在实施前先固定字段映射表，避免上线后因字段差异导致无法建号。

## 14. 结论

本设计推荐在现有 Django Session 认证体系上，新增一条由后端主导的 OIDC 授权码登录链路，实现“云南中烟登录”与本地登录并存。

该方案具有以下优势：

- 与现有系统兼容度高
- 前端改动小
- 密钥安全边界清晰
- 本地权限控制不被外部系统侵入
- 首次自动建号策略与现有用户管理体系一致

在后续实施阶段，应先固定 SSO 字段映射，再进入详细实现计划与开发。
