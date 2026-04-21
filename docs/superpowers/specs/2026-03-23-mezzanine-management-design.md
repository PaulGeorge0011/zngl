# 夹层施工管理 — 设计文档

> 日期: 2026-03-23
> 模块: 安全管理 → 夹层施工

## 1. 概述

在安全管理一级菜单下新增「夹层施工」二级菜单，实现夹层施工人员的入离场扫码管理。现场张贴两个固定二维码（入场码/离场码），施工人员用手机扫码完成签到签退，无需系统账号。同时提供大屏轮播页面展示实时在场人员，以及管理后台的历史查询功能。

## 2. 数据模型

### 2.1 MezzanineRecord（夹层施工记录）

追加到 `backend/apps/safety/models.py`：

```python
class MezzanineRecord(models.Model):
    name = models.CharField('姓名', max_length=50)
    phone = models.CharField('手机号', max_length=20)
    company = models.CharField('施工单位', max_length=100, blank=True)
    project = models.CharField('施工项目', max_length=200)
    check_in_at = models.DateTimeField('入场时间', auto_now_add=True)
    check_out_at = models.DateTimeField('离场时间', null=True, blank=True)

    class Meta:
        verbose_name = '夹层施工记录'
        verbose_name_plural = '夹层施工记录'
        ordering = ['-check_in_at']

    def __str__(self):
        return f"{self.name} - {self.project} ({self.check_in_at:%Y-%m-%d})"
```

- 无外键关联 User（访客无需系统账号）
- `check_out_at` 为 NULL 表示尚在现场
- `phone` 不设唯一约束（同一人可多次入场）

## 3. API 设计

### 3.1 公开接口（无需登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/safety/mezzanine/checkin/` | 入场签到，提交姓名/手机号/施工单位/施工项目 |
| GET | `/api/safety/mezzanine/onsite/` | 当前在场人员列表（大屏轮播 + 离场签退用） |
| POST | `/api/safety/mezzanine/checkout/` | 离场签退，提交 `record_id` |

所有公开接口使用 `@permission_classes([AllowAny])` 并豁免 CSRF（`@csrf_exempt`）。

### 3.2 认证接口（需登录）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/safety/mezzanine/history/` | 已登录用户 | 历史记录查询 |

### 3.3 签到接口详情

`POST /api/safety/mezzanine/checkin/`

请求体：
```json
{
  "name": "张三",
  "phone": "13800138000",
  "company": "XX施工队",
  "project": "电缆敷设"
}
```

响应：
```json
{
  "id": 1,
  "name": "张三",
  "check_in_at": "2026-03-23 09:15:00",
  "message": "签到成功"
}
```

### 3.4 在场人员接口

`GET /api/safety/mezzanine/onsite/`

返回 `check_out_at` 为 NULL 的所有记录，按 `check_in_at` 升序：
```json
[{
  "id": 1,
  "name": "张三",
  "phone": "138****8000",
  "company": "XX施工队",
  "project": "电缆敷设",
  "check_in_at": "2026-03-23 09:15:00"
}]
```

注意：`phone` 字段脱敏处理（中间四位 `****`），保护隐私。

### 3.5 签退接口

`POST /api/safety/mezzanine/checkout/`

请求体：
```json
{ "record_id": 1, "phone_last4": "8000" }
```

后端校验 `phone_last4` 与该记录的手机号后四位是否匹配，匹配则将 `check_out_at` 设为当前时间，不匹配返回 400。

### 3.6 历史查询接口

`GET /api/safety/mezzanine/history/?search=xxx&project=xxx&date_from=xxx&date_to=xxx&status=onsite|left&page=1&page_size=20`

筛选参数：
- `search` — 姓名或手机号模糊搜索
- `project` — 施工项目关键词
- `date_from` / `date_to` — 入场时间范围
- `status` — `onsite`（在场）/ `left`（已离场）
- `page` — 分页（使用全局 PAGE_SIZE=20，不暴露 page_size 参数）

## 4. 前端页面

### 4.1 入场登记页 `/m/checkin`

- **访问方式**：手机扫二维码直接打开
- **无需登录**，不套 AppLayout
- 移动端适配，深色主题
- 顶部标题：「夹层施工入场登记」
- 表单：姓名（必填）、手机号（必填）、施工单位（选填）、施工项目（必填）
- 提交后显示「签到成功」卡片 + 入场时间

### 4.2 离场签退页 `/m/checkout`

- **访问方式**：手机扫二维码直接打开
- **无需登录**，不套 AppLayout
- 移动端适配，深色主题
- 从 `/api/safety/mezzanine/onsite/` 获取在场人员列表
- 显示每人的姓名 + 施工项目 + 入场时间
- 点击自己的名字 → 输入手机号后四位确认身份 → 调用签退接口 → 显示「签退成功」
- 无人在场时显示空状态提示

### 4.3 大屏轮播页 `/m/mezzanine-board`

- **无需登录**，不套 AppLayout
- 全屏页面，适合投屏到现场电视
- 顶部：标题「夹层施工现场人员」+ 当前在场人数统计
- 主体：卡片式轮播（姓名、施工单位、施工项目、入场时间、已在场时长）
- 每 5 秒自动切换一组（每组约 4-6 人）
- 每 30 秒从后端拉取最新数据
- 无人在场时显示「当前无人在夹层作业」

### 4.4 管理查询页 `/safety/mezzanine`

- **需登录**，在 AppLayout 内
- 侧边栏入口：安全管理 → 夹层施工
- 顶部统计卡片：今日入场人次、当前在场人数
- 筛选栏：搜索（姓名/手机号）、施工项目、时间范围、状态（在场/已离场）
- 表格列：姓名、手机号、施工单位、施工项目、入场时间、离场时间、在场时长、状态
- 状态标签：在场(绿) / 已离场(灰)
- 分页

### 4.5 侧边栏变更

安全管理子菜单顺序：
1. 安全概览
2. 随手拍
3. **夹层施工** → `/safety/mezzanine`（新增）
4. 安全知识库

### 4.6 二维码内容

- 入场码 URL：`http://{host}/m/checkin`
- 离场码 URL：`http://{host}/m/checkout`

管理员自行将这两个 URL 生成二维码并打印张贴到现场。

## 5. 路由设计

### 公开路由（meta.public = true）

```
/m/checkin           → CheckinView（入场登记）
/m/checkout          → CheckoutView（离场签退）
/m/mezzanine-board   → MezzanineBoardView（大屏轮播）
```

这三个路由独立于 AppLayout，不经过登录守卫。

### 认证路由（AppLayout 子路由）

```
/safety/mezzanine    → MezzanineManageView（管理查询）
```

## 6. 文件变更清单

### 新建

**前端：**
- `frontend/src/views/mobile/CheckinView.vue` — 入场登记
- `frontend/src/views/mobile/CheckoutView.vue` — 离场签退
- `frontend/src/views/mobile/MezzanineBoardView.vue` — 大屏轮播
- `frontend/src/views/safety/MezzanineManageView.vue` — 管理查询
- `frontend/src/api/mezzanine.ts` — 夹层施工 API 模块

### 修改

**后端：**
- `backend/apps/safety/models.py` — 追加 MezzanineRecord 模型
- `backend/apps/safety/views.py` — 追加 4 个视图函数
- `backend/apps/safety/urls.py` — 追加 mezzanine 路由
- `backend/apps/safety/migrations/` — 自动生成迁移

**前端：**
- `frontend/src/router/index.ts` — 新增 4 条路由
- `frontend/src/components/layout/SidebarNav.vue` — 安全管理下加「夹层施工」子菜单

## 7. 安全考虑

- 公开接口不返回完整手机号，中间四位脱敏（`138****8000`）
- 签退接口要求提交手机号后四位作为身份验证，防止他人冒签
- 公开接口使用 `@permission_classes([AllowAny])` + `@csrf_exempt`
- 公开 API 复用现有 `http` 实例是安全的（后端已 csrf_exempt + AllowAny，withCredentials 不影响功能）
- 历史查询接口需登录，返回完整手机号供管理使用
