# 随手拍找隐患 — 设计文档

> 日期: 2026-03-21
> 模块: 安全管理 → 随手拍

## 1. 概述

在安全管理一级菜单下新增「随手拍」二级菜单，提供隐患上报、三级流转处理（分派→整改→验证）、历史查询功能。同时引入 Django 内置认证体系，支持三种角色的权限控制。

## 2. 用户角色

基于 Django 内置 `User` + `Group`，不自定义用户模型。

| 角色 | Group 名称 | 权限 |
|------|-----------|------|
| 普通员工 | 员工 | 上报隐患、查看列表/详情 |
| 班组长 | 班组长 | 员工权限 + 提交整改（限被分派的隐患） |
| 安全员 | 安全员 | 全部权限：分派、验证通过/驳回 |

用户通过 Django admin 后台创建和分配角色。

## 3. 数据模型

### 3.1 Location（区域）

```python
class Location(models.Model):
    name = CharField(max_length=50, unique=True)
    sort_order = IntegerField(default=0)
    is_active = BooleanField(default=True)
```

- 管理员通过 Django admin 增删改
- 前端下拉从 API 动态获取
- 初始化脚本预填种子数据

### 3.2 HazardReport（隐患主表）

```python
class HazardReport(models.Model):
    LEVEL_CHOICES = [('general', '一般隐患'), ('major', '重大隐患')]
    STATUS_CHOICES = [
        ('pending', '待分派'),
        ('fixing', '整改中'),
        ('verifying', '待验证'),
        ('closed', '已关闭'),
        ('rejected', '驳回'),
    ]

    title = CharField(max_length=100)
    description = TextField()
    level = CharField(max_length=10, choices=LEVEL_CHOICES)
    location = ForeignKey(Location, on_delete=PROTECT)
    location_detail = CharField(max_length=200, blank=True)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reporter = ForeignKey(User, on_delete=PROTECT, related_name='reported_hazards')
    assignee = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True, related_name='assigned_hazards')
    assigned_by = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True, related_name='dispatched_hazards')
    assigned_at = DateTimeField(null=True, blank=True)
    fixed_at = DateTimeField(null=True, blank=True)
    fix_description = TextField(blank=True)
    verified_by = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True, related_name='verified_hazards')
    verified_at = DateTimeField(null=True, blank=True)
    verify_remark = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 3.3 HazardImage（图片）

```python
class HazardImage(models.Model):
    PHASE_CHOICES = [('report', '上报'), ('fix', '整改')]

    hazard = ForeignKey(HazardReport, on_delete=CASCADE, related_name='images')
    image = ImageField(upload_to='hazards/%Y/%m/')
    phase = CharField(max_length=10, choices=PHASE_CHOICES)
    created_at = DateTimeField(auto_now_add=True)
```

- 上报阶段最多 3 张图片
- 整改阶段可选上传，最多 3 张

### 3.4 状态流转

```
pending(待分派) → fixing(整改中) → verifying(待验证) → closed(已关闭)
                                                    ↘ rejected(驳回) → fixing（循环）
```

- `pending → fixing`：安全员分派责任人，状态直接进入 fixing
- `fixing → verifying`：被分派人提交整改说明 + 可选图片
- `verifying → closed`：安全员验证通过
- `verifying → rejected`：安全员驳回，状态回到 fixing，被分派人重新整改

## 4. API 设计

### 4.1 认证 — `apps/users/`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/users/login/` | 登录（username + password），返回用户信息 |
| POST | `/api/users/logout/` | 登出，清除 session |
| GET | `/api/users/me/` | 当前用户信息（id, username, display_name, role） |
| GET | `/api/users/list/` | 用户列表（支持 `?role=班组长` 筛选，安全员分派时选人） |

认证方式：Django SessionAuthentication。

CSRF 处理：
- 前端 axios 设置 `withCredentials: true`
- 从 cookie 读取 `csrftoken`，通过 `X-CSRFToken` 请求头发送
- 后端配置 `CSRF_TRUSTED_ORIGINS = ['http://localhost:5173']`
- 后端配置 `CORS_ALLOW_CREDENTIALS = True`
- `SESSION_COOKIE_SAMESITE = 'Lax'`

### 4.2 隐患管理 — `apps/safety/`

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/safety/locations/` | 登录用户 | 区域列表（is_active=True） |
| POST | `/api/safety/hazards/` | 登录用户 | 上报隐患（multipart/form-data） |
| GET | `/api/safety/hazards/` | 登录用户 | 隐患列表（支持筛选分页） |
| GET | `/api/safety/hazards/{id}/` | 登录用户 | 隐患详情 |
| POST | `/api/safety/hazards/{id}/assign/` | 安全员 | 分派：`{assignee_id}` |
| POST | `/api/safety/hazards/{id}/fix/` | 被分派人 | 提交整改：`{fix_description, images?}` |
| POST | `/api/safety/hazards/{id}/verify/` | 安全员 | 验证：`{action: 'approve'|'reject', remark?}` |

### 4.3 筛选参数（GET hazards）

- `status` — 状态
- `level` — 等级
- `location` — 区域 ID
- `reporter` — 上报人 ID
- `date_from` / `date_to` — 时间范围
- `search` — 标题/描述关键词
- `page` / `page_size` — 分页

## 5. 前端页面

### 5.1 登录页 `/login`

- 独立页面，不在 AppLayout 内
- 用户名 + 密码表单
- 登录成功后存储用户信息到 Pinia store，跳转 `/dashboard`
- 工业风深色主题，居中卡片

### 5.2 隐患上报 `/safety/hazard/report`

- 表单字段：标题、描述（textarea）、等级（radio）、区域（select，API 动态获取）、位置补充（input）、图片上传（最多3张）
- 图片支持预览和删除
- 提交后跳转列表页

### 5.3 隐患列表 `/safety/hazard`

- 顶部筛选栏：状态、等级、区域、时间范围、关键词搜索
- 右上角「上报隐患」按钮
- 表格列：标题、等级标签、区域、状态标签、上报人、上报时间、操作
- 状态颜色：待分派(蓝)、整改中(橙)、待验证(紫)、已关闭(绿)、驳回(红)
- 分页
- 点击行进入详情

### 5.4 隐患详情 `/safety/hazard/:id`

- 基本信息卡片：标题、等级、区域+补充、描述、上报人/时间
- 上报图片区（可点击放大）
- 流转时间线：每步显示操作人、时间、备注
- 整改图片区（如有）
- 底部操作按钮（按角色+状态动态显示）：
  - 安全员 + pending → 「分派」（弹窗选人）
  - 被分派人 + fixing → 「提交整改」（弹窗填说明+可选图片）
  - 安全员 + verifying → 「通过」/「驳回」

### 5.5 侧边栏

安全管理子菜单新增「随手拍」项：
- 安全概览 `/safety`
- 随手拍 `/safety/hazard`
- 安全知识库 `/safety/knowledge`

### 5.6 权限控制

- 路由守卫 `router.beforeEach`：未登录 → 跳 `/login`
- Pinia `userStore`：存储 id, username, display_name, role
- http 拦截器：401 响应 → 清除 store + 跳登录页
- 按钮级：根据 `userStore.role` 控制操作按钮显隐

## 6. 文件变更清单

### 新建

**后端：**
- `backend/apps/users/__init__.py`
- `backend/apps/users/apps.py` — UsersConfig
- `backend/apps/users/views.py` — 登录/登出/me/list
- `backend/apps/users/urls.py`
- `backend/apps/safety/models.py` — Location + HazardReport + HazardImage
- `backend/apps/safety/serializers.py`
- `backend/apps/safety/permissions.py` — IsSafetyOfficer, IsAssignee
- `backend/apps/safety/admin.py` — Location admin
- `backend/scripts/init_safety_data.py` — 种子数据

**前端：**
- `frontend/src/views/login/LoginView.vue`
- `frontend/src/views/safety/HazardListView.vue`
- `frontend/src/views/safety/HazardDetailView.vue`
- `frontend/src/views/safety/HazardReportView.vue`
- `frontend/src/api/users.ts`
- `frontend/src/api/safety.ts`
- `frontend/src/stores/user.ts`

### 修改

**后端：**
- `backend/config/settings/base.py` — INSTALLED_APPS 加 `apps.users`，配置 `MEDIA_ROOT = BASE_DIR / 'media'`，`MEDIA_URL = '/media/'`，SESSION/CSRF/CORS 认证相关配置
- `backend/config/urls.py` — users 路由, `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` media 文件服务
- `backend/apps/safety/urls.py` — 隐患+区域路由

**前端：**
- `frontend/src/router/index.ts` — 登录页、隐患页路由、路由守卫
- `frontend/src/components/layout/SidebarNav.vue` — 「随手拍」子菜单
- `frontend/src/api/http.ts` — 401 拦截处理

## 7. 种子数据

### 区域

松散回潮、切片、加料、烘丝、加香、储丝、配送、公共区域、办公区域

### 用户（演示用）

| 用户名 | 角色 | 密码 |
|--------|------|------|
| admin | 安全员 | admin123 |
| leader1 | 班组长 | leader123 |
| worker1 | 员工 | worker123 |
