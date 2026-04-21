# 用户管理 — 设计文档

> 日期: 2026-03-22
> 模块: 系统设置 → 用户管理

## 1. 概述

在侧边栏新增「系统设置」一级导航组，下设「用户管理」二级菜单。提供用户账号的增删改查、角色分配、密码重置功能。操作权限限定为安全员角色，普通用户可查看列表但不可编辑。

## 2. 数据模型

### 2.1 UserProfile（用户扩展信息）

新建 `backend/apps/users/models.py`：

```python
class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    employee_id = models.CharField('工号', max_length=50, unique=True, blank=True, null=True, default=None)
    phone = models.CharField('联系电话', max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 2.2 Django User 字段使用约定

| 用途 | 字段 |
|------|------|
| 登录账号 | `username` |
| 姓名 | `first_name`（全名，不使用 last_name） |
| 是否启用 | `is_active`（False = 禁用） |
| 角色 | `groups`（安全员 / 班组长 / 员工） |

- 创建用户时自动创建对应的 `UserProfile` 记录
- `employee_id` 允许为空（老用户可无工号）
- 禁用用户使用 `is_active=False`（软删除），保留历史数据关联

## 3. API 设计

所有管理接口挂载在 `/api/users/manage/` 前缀下，权限通过 `IsSafetyOfficer` 检查。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/users/manage/` | 已登录用户 | 用户列表（含 profile，支持搜索） |
| POST | `/api/users/manage/` | 安全员 | 创建用户（含初始密码） |
| PUT | `/api/users/manage/{id}/` | 安全员 | 编辑用户信息 + 角色 |
| PATCH | `/api/users/manage/{id}/toggle/` | 安全员 | 切换启用/禁用状态 |
| POST | `/api/users/manage/{id}/reset-password/` | 安全员 | 重置密码 |

### 3.1 列表接口

`GET /api/users/manage/?search=xxx`

- `search` 参数：按姓名 / 用户名 / 工号模糊搜索
- 返回所有用户（含已禁用），前端按状态区分显示

响应结构：
```json
[{
  "id": 1,
  "username": "worker1",
  "display_name": "员工一",
  "role": "worker",
  "employee_id": "EMP001",
  "phone": "13800138000",
  "is_active": true
}]
```

### 3.2 创建接口

`POST /api/users/manage/`

请求体：
```json
{
  "username": "worker2",
  "name": "员工二",
  "password": "初始密码",
  "role": "worker",
  "employee_id": "EMP002",
  "phone": "13800138001"
}
```

### 3.3 编辑接口

`PUT /api/users/manage/{id}/`

请求体（不含 password）：
```json
{
  "name": "员工二（改）",
  "role": "team_leader",
  "employee_id": "EMP002",
  "phone": "13900139000"
}
```

- `username` 创建后不可修改

### 3.4 重置密码接口

`POST /api/users/manage/{id}/reset-password/`

```json
{ "password": "新密码" }
```

### 3.5 切换状态接口

`PATCH /api/users/manage/{id}/toggle/`

无请求体，将 `is_active` 取反，返回更新后的用户数据。

## 4. 前端页面

### 4.1 用户列表页 `/settings/users`

- 顶部：搜索框（按姓名/工号/用户名） + 「新建用户」按钮
- 表格列：姓名、用户名、工号、联系电话、角色标签、状态标签、操作列
- 操作列：「编辑」按钮（打开抽屉）、「禁用/启用」按钮
- 「新建用户」和操作按钮仅安全员可见（前端根据 `userStore.isSafetyOfficer` 控制）

### 4.2 用户抽屉（新建 / 编辑）

宽 480px，两个标签页：

**标签页一：基本信息**
- 姓名（必填）
- 用户名（必填；编辑模式下只读）
- 工号（选填）
- 联系电话（选填）
- 初始密码（仅新建模式显示，必填）

**标签页二：角色与权限**
- 角色单选：安全员 / 班组长 / 员工（必选）
- 重置密码区（仅编辑模式）：
  - 新密码输入框
  - 「重置密码」按钮，单独提交

### 4.3 侧边栏

底部新增「系统设置」导航组：
- 系统设置（标题，可展开/收起）
  - 用户管理 → `/settings/users`

## 5. 文件变更清单

### 新建

**后端：**
- `backend/apps/users/models.py` — UserProfile 模型
- `backend/apps/users/serializers.py` — 用户管理序列化器
- `backend/apps/users/migrations/` — 自动生成迁移

**前端：**
- `frontend/src/views/settings/UserManageView.vue` — 用户列表页
- `frontend/src/components/users/UserDrawer.vue` — 新建/编辑抽屉

### 修改

**后端：**
- `backend/apps/users/views.py` — 新增 manage 系列视图函数
- `backend/apps/users/urls.py` — 新增 manage 路由

**前端：**
- `frontend/src/api/users.ts` — 新增管理 API（list/create/update/toggle/resetPassword）
- `frontend/src/router/index.ts` — 新增 `/settings/users` 路由
- `frontend/src/components/layout/SidebarNav.vue` — 新增系统设置导航组

## 6. 权限说明

- 后端：所有 `/api/users/manage/` 接口使用 `IsSafetyOfficer` 权限类
- 前端：「新建」按钮和操作列按钮通过 `userStore.isSafetyOfficer` 控制显隐
- 所有登录用户均可访问 `/settings/users` 路由（查看），但操作按钮不可见

## 7. 注意事项

- 创建用户时自动创建空的 `UserProfile`（通过 `get_or_create`）
- `employee_id` 字段 `unique=True` 但 `blank=True`，空值不参与唯一性校验（数据库存 `''` 或 `NULL`，推荐用 `NULL`）
- 禁用当前登录用户的操作不做特殊限制（边缘情况，系统保留至少一个安全员是管理员职责）
