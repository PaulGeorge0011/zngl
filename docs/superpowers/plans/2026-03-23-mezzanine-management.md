# 夹层施工管理 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增夹层施工人员入离场扫码管理功能，包含入场签到、离场签退、大屏轮播和管理查询四个页面。

**Architecture:** 后端在 `apps/safety` 追加 `MezzanineRecord` 模型和 4 个视图（3 个公开 + 1 个需登录）；前端新建 3 个移动端公开页面（`/m/` 路径）和 1 个管理查询页，侧边栏在安全管理下新增「夹层施工」子项。

**Tech Stack:** Django 4.2 + DRF, Vue 3 + TypeScript + Element Plus, axios

**Spec:** `docs/superpowers/specs/2026-03-23-mezzanine-management-design.md`

---

## Chunk 1: 后端模型与 API

### Task 1: 追加 MezzanineRecord 模型

**Files:**
- Modify: `backend/apps/safety/models.py`
- Auto-generate: `backend/apps/safety/migrations/`

- [ ] **Step 1: 追加模型到 models.py 末尾**

打开 `backend/apps/safety/models.py`，在文件末尾追加：

```python

class MezzanineRecord(models.Model):
    """夹层施工人员入离场记录"""

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

- [ ] **Step 2: 生成并应用迁移**

```bash
cd backend
python manage.py makemigrations safety
python manage.py migrate
```

期望输出：`Applying safety.0002_mezzaninerecord... OK`

- [ ] **Step 3: 验证**

```bash
cd backend
python manage.py check
```

期望：`System check identified no issues (0 silenced).`

- [ ] **Step 4: 提交**

```bash
cd "F:/zs2 Management System"
git add backend/apps/safety/models.py backend/apps/safety/migrations/
git commit -m "feat: add MezzanineRecord model for construction entry/exit tracking"
```

---

### Task 2: 追加夹层施工视图和路由

**Files:**
- Modify: `backend/apps/safety/views.py`
- Modify: `backend/apps/safety/urls.py`

- [ ] **Step 1: 在 views.py 末尾追加导入和视图**

先读取 `backend/apps/safety/views.py` 确认现有 import（已有 `logging`, `requests`, `settings`, `timezone`, `status`, `api_view`, `permission_classes`, `parser_classes`, `IsAuthenticated`, `Response` 等）。

在文件顶部现有 import 块中**新增**（不重复已有的）：
```python
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
```

在文件末尾追加以下视图：

```python
# ── 夹层施工管理 ──────────────────────────────────────────────────────────────

from .models import MezzanineRecord


def _mask_phone(phone: str) -> str:
    """脱敏手机号，保留前3位和后4位，中间4位替换为 ****
    例：13800138000 → 138****8000（phone[:3] + '****' + phone[7:]）
    """
    if len(phone) >= 8:
        return phone[:3] + '****' + phone[7:]
    return phone


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mezzanine_checkin(request):
    """入场签到（公开接口，无需登录）"""
    name = request.data.get('name', '').strip()
    phone = request.data.get('phone', '').strip()
    company = request.data.get('company', '').strip()
    project = request.data.get('project', '').strip()

    if not name:
        return Response({'error': '请填写姓名'}, status=400)
    if not phone:
        return Response({'error': '请填写手机号'}, status=400)
    if not project:
        return Response({'error': '请填写施工项目'}, status=400)

    record = MezzanineRecord.objects.create(
        name=name, phone=phone, company=company, project=project
    )
    logger.info(f"夹层施工签到: {name} ({phone}) - {project}")
    return Response({
        'id': record.id,
        'name': record.name,
        'check_in_at': record.check_in_at.strftime('%Y-%m-%d %H:%M:%S'),
        'message': '签到成功',
    }, status=201)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def mezzanine_onsite(request):
    """当前在场人员列表（公开接口，手机号脱敏）"""
    records = MezzanineRecord.objects.filter(
        check_out_at__isnull=True
    ).order_by('check_in_at')
    data = [
        {
            'id': r.id,
            'name': r.name,
            'phone': _mask_phone(r.phone),
            'company': r.company,
            'project': r.project,
            'check_in_at': r.check_in_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for r in records
    ]
    return Response(data)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mezzanine_checkout(request):
    """离场签退（公开接口，需验证手机号后四位）"""
    record_id = request.data.get('record_id')
    phone_last4 = request.data.get('phone_last4', '').strip()

    if not record_id:
        return Response({'error': '缺少 record_id'}, status=400)
    if not phone_last4 or len(phone_last4) != 4 or not phone_last4.isdigit():
        return Response({'error': '请输入手机号后四位（4位数字）'}, status=400)

    try:
        record = MezzanineRecord.objects.get(pk=record_id, check_out_at__isnull=True)
    except MezzanineRecord.DoesNotExist:
        return Response({'error': '记录不存在或已签退'}, status=404)

    if not record.phone.endswith(phone_last4):
        return Response({'error': '手机号后四位不匹配'}, status=400)

    record.check_out_at = timezone.now()
    record.save(update_fields=['check_out_at'])
    logger.info(f"夹层施工签退: {record.name} ({record.phone})")
    return Response({
        'name': record.name,
        'check_out_at': record.check_out_at.strftime('%Y-%m-%d %H:%M:%S'),
        'message': '签退成功',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mezzanine_history(request):
    """历史记录查询（需登录，返回完整手机号）"""
    from django.db.models import Q
    from django.utils import timezone as tz
    import datetime

    qs = MezzanineRecord.objects.all()

    search = request.query_params.get('search', '').strip()
    project = request.query_params.get('project', '').strip()
    date_from = request.query_params.get('date_from', '').strip()
    date_to = request.query_params.get('date_to', '').strip()
    status_filter = request.query_params.get('status', '').strip()

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(phone__icontains=search))
    if project:
        qs = qs.filter(project__icontains=project)
    if date_from:
        qs = qs.filter(check_in_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(check_in_at__date__lte=date_to)
    if status_filter == 'onsite':
        qs = qs.filter(check_out_at__isnull=True)
    elif status_filter == 'left':
        qs = qs.filter(check_out_at__isnull=False)

    # 手动分页，page_size 固定为 20（不接受客户端传入的 page_size 参数，与全局 PAGE_SIZE=20 保持一致）
    page = int(request.query_params.get('page', 1))
    page_size = 20  # 硬编码，不从 query_params 读取
    total = qs.count()
    records = qs[(page - 1) * page_size: page * page_size]

    # 今日统计
    today = tz.localdate()
    today_count = MezzanineRecord.objects.filter(check_in_at__date=today).count()
    onsite_count = MezzanineRecord.objects.filter(check_out_at__isnull=True).count()

    def duration_str(r):
        end = r.check_out_at or tz.now()
        delta = end - r.check_in_at
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        return f"{hours}h{minutes:02d}m"

    data = [
        {
            'id': r.id,
            'name': r.name,
            'phone': r.phone,
            'company': r.company,
            'project': r.project,
            'check_in_at': r.check_in_at.strftime('%Y-%m-%d %H:%M:%S'),
            'check_out_at': r.check_out_at.strftime('%Y-%m-%d %H:%M:%S') if r.check_out_at else None,
            'duration': duration_str(r),
            'status': 'onsite' if r.check_out_at is None else 'left',
        }
        for r in records
    ]
    return Response({
        'count': total,
        'page': page,
        'results': data,
        'stats': {
            'today_count': today_count,
            'onsite_count': onsite_count,
        },
    })
```

- [ ] **Step 2: 更新 urls.py**

将 `backend/apps/safety/urls.py` 替换为：

```python
from django.urls import path
from . import views

urlpatterns = [
    # Knowledge base (existing)
    path('knowledge/search/', views.search_knowledge, name='safety-knowledge-search'),

    # Locations
    path('locations/', views.location_list, name='safety-location-list'),

    # Hazard reports
    path('hazards/', views.hazard_list_create, name='safety-hazard-list'),
    path('hazards/<int:pk>/', views.hazard_detail, name='safety-hazard-detail'),
    path('hazards/<int:pk>/assign/', views.hazard_assign, name='safety-hazard-assign'),
    path('hazards/<int:pk>/fix/', views.hazard_fix, name='safety-hazard-fix'),
    path('hazards/<int:pk>/verify/', views.hazard_verify, name='safety-hazard-verify'),

    # 夹层施工管理
    path('mezzanine/checkin/', views.mezzanine_checkin, name='mezzanine-checkin'),
    path('mezzanine/onsite/', views.mezzanine_onsite, name='mezzanine-onsite'),
    path('mezzanine/checkout/', views.mezzanine_checkout, name='mezzanine-checkout'),
    path('mezzanine/history/', views.mezzanine_history, name='mezzanine-history'),
]
```

- [ ] **Step 3: 验证**

```bash
cd backend
python manage.py check
```

期望：`System check identified no issues (0 silenced).`

- [ ] **Step 4: 提交**

```bash
cd "F:/zs2 Management System"
git add backend/apps/safety/views.py backend/apps/safety/urls.py
git commit -m "feat: add mezzanine check-in/out/onsite/history API endpoints"
```

---

## Chunk 2: 前端 API 模块与路由

### Task 3: 前端 API 模块

**Files:**
- Create: `frontend/src/api/mezzanine.ts`

- [ ] **Step 1: 创建 API 模块**

创建 `frontend/src/api/mezzanine.ts`：

```typescript
import http from './http'

export interface MezzanineOnsite {
  id: number
  name: string
  phone: string        // 脱敏（138****8000）
  company: string
  project: string
  check_in_at: string
}

export interface MezzanineRecord {
  id: number
  name: string
  phone: string        // 完整手机号（管理端）
  company: string
  project: string
  check_in_at: string
  check_out_at: string | null
  duration: string
  status: 'onsite' | 'left'
}

export interface MezzanineHistoryResponse {
  count: number
  page: number
  results: MezzanineRecord[]
  stats: {
    today_count: number
    onsite_count: number
  }
}

export interface CheckinPayload {
  name: string
  phone: string
  company?: string
  project: string
}

export interface CheckoutPayload {
  record_id: number
  phone_last4: string
}

export interface HistoryFilters {
  search?: string
  project?: string
  date_from?: string
  date_to?: string
  status?: 'onsite' | 'left' | ''
  page?: number
}

export const mezzanineApi = {
  checkin(data: CheckinPayload) {
    return http.post<{ id: number; name: string; check_in_at: string; message: string }>(
      '/api/safety/mezzanine/checkin/',
      data
    )
  },

  onsite() {
    return http.get<MezzanineOnsite[]>('/api/safety/mezzanine/onsite/')
  },

  checkout(data: CheckoutPayload) {
    return http.post<{ name: string; check_out_at: string; message: string }>(
      '/api/safety/mezzanine/checkout/',
      data
    )
  },

  history(filters: HistoryFilters = {}) {
    return http.get<MezzanineHistoryResponse>('/api/safety/mezzanine/history/', {
      params: filters,
    })
  },
}
```

- [ ] **Step 2: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/api/mezzanine.ts
git commit -m "feat: add mezzanine API module"
```

---

### Task 4: 路由配置与侧边栏

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/layout/SidebarNav.vue`

- [ ] **Step 1: 在 router/index.ts 新增路由**

先读取 `frontend/src/router/index.ts`。

在顶层路由数组中（`/login` 路由之后，`/` 重定向之前）新增 3 条公开路由：

```typescript
{
  path: '/m/checkin',
  name: 'MobileCheckin',
  component: () => import('@/views/mobile/CheckinView.vue'),
  meta: { public: true, title: '入场登记' },
},
{
  path: '/m/checkout',
  name: 'MobileCheckout',
  component: () => import('@/views/mobile/CheckoutView.vue'),
  meta: { public: true, title: '离场签退' },
},
{
  path: '/m/mezzanine-board',
  name: 'MezzanineBoard',
  component: () => import('@/views/mobile/MezzanineBoardView.vue'),
  meta: { public: true, title: '夹层施工现场' },
},
```

在 AppLayout children 数组中（`safety/knowledge` 路由之后，`safety/hazard` 路由之前）新增 1 条认证路由：

```typescript
{
  path: 'safety/mezzanine',
  name: 'MezzanineManage',
  component: () => import('@/views/safety/MezzanineManageView.vue'),
  meta: { title: '夹层施工' },
},
```

- [ ] **Step 2: 在 SidebarNav.vue 安全管理子菜单添加「夹层施工」**

先读取 `frontend/src/components/layout/SidebarNav.vue`，找到安全管理的 `nav-sub` 区域（在 `随手拍` 和 `安全知识库` 之间）。

在 `随手拍` router-link 之后、`安全知识库` 之前插入：

```html
          <router-link to="/safety/mezzanine" class="nav-sub-item" active-class="active">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="1" y="3" width="11" height="8" rx="1.5"/>
              <path d="M4 3V2a1 1 0 011-1h3a1 1 0 011 1v1"/>
              <path d="M4 7h5M4 9h3"/>
            </svg>
            夹层施工
          </router-link>
```

- [ ] **Step 3: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/router/index.ts frontend/src/components/layout/SidebarNav.vue
git commit -m "feat: add mezzanine routes and sidebar nav item"
```

---

## Chunk 3: 移动端公开页面

### Task 5: 入场登记页

**Files:**
- Create: `frontend/src/views/mobile/CheckinView.vue`

- [ ] **Step 1: 创建入场登记页**

创建 `frontend/src/views/mobile/CheckinView.vue`：

```vue
<template>
  <div class="mobile-page">
    <!-- 成功状态 -->
    <div v-if="success" class="success-card">
      <div class="success-icon">✓</div>
      <h2>签到成功</h2>
      <p class="success-name">{{ successData.name }}</p>
      <p class="success-time">入场时间：{{ successData.check_in_at }}</p>
      <button class="btn-secondary" @click="resetForm">继续签到</button>
    </div>

    <!-- 表单状态 -->
    <template v-else>
      <div class="page-header">
        <div class="header-icon">🏗</div>
        <h1>夹层施工入场登记</h1>
        <p>请填写以下信息完成入场登记</p>
      </div>

      <div class="form-card">
        <div class="form-item" :class="{ error: errors.name }">
          <label>姓名 <span class="required">*</span></label>
          <input v-model="form.name" type="text" placeholder="请输入姓名" maxlength="50" />
          <span class="error-msg" v-if="errors.name">{{ errors.name }}</span>
        </div>

        <div class="form-item" :class="{ error: errors.phone }">
          <label>手机号 <span class="required">*</span></label>
          <input v-model="form.phone" type="tel" placeholder="请输入手机号" maxlength="20" />
          <span class="error-msg" v-if="errors.phone">{{ errors.phone }}</span>
        </div>

        <div class="form-item">
          <label>施工单位</label>
          <input v-model="form.company" type="text" placeholder="选填" maxlength="100" />
        </div>

        <div class="form-item" :class="{ error: errors.project }">
          <label>施工项目 <span class="required">*</span></label>
          <input v-model="form.project" type="text" placeholder="请输入施工项目名称" maxlength="200" />
          <span class="error-msg" v-if="errors.project">{{ errors.project }}</span>
        </div>

        <button class="btn-primary" :disabled="submitting" @click="handleSubmit">
          {{ submitting ? '提交中...' : '确认签到' }}
        </button>

        <p v-if="submitError" class="submit-error">{{ submitError }}</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { mezzanineApi } from '@/api/mezzanine'

const form = reactive({ name: '', phone: '', company: '', project: '' })
const errors = reactive({ name: '', phone: '', project: '' })
const submitting = ref(false)
const submitError = ref('')
const success = ref(false)
const successData = reactive({ name: '', check_in_at: '' })

function validate() {
  errors.name = form.name.trim() ? '' : '请填写姓名'
  errors.phone = form.phone.trim() ? '' : '请填写手机号'
  errors.project = form.project.trim() ? '' : '请填写施工项目'
  return !errors.name && !errors.phone && !errors.project
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  submitError.value = ''
  try {
    const { data } = await mezzanineApi.checkin({
      name: form.name.trim(),
      phone: form.phone.trim(),
      company: form.company.trim(),
      project: form.project.trim(),
    })
    successData.name = data.name
    successData.check_in_at = data.check_in_at
    success.value = true
  } catch (err: any) {
    submitError.value = err.response?.data?.error || '提交失败，请重试'
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  Object.assign(form, { name: '', phone: '', company: '', project: '' })
  Object.assign(errors, { name: '', phone: '', project: '' })
  submitError.value = ''
  success.value = false
}
</script>

<style scoped>
.mobile-page {
  min-height: 100vh;
  background: var(--bg-root);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
  padding-top: 16px;
}

.header-icon { font-size: 2.5rem; margin-bottom: 8px; }

.page-header h1 {
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.page-header p { font-size: 0.875rem; color: var(--text-muted); margin: 0; }

.form-card {
  width: 100%;
  max-width: 480px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item { display: flex; flex-direction: column; gap: 6px; }

.form-item label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.required { color: var(--color-alarm); }

.form-item input {
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 1rem;
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--transition-fast);
  width: 100%;
  box-sizing: border-box;
}

.form-item input:focus { border-color: var(--color-accent); }
.form-item.error input { border-color: var(--color-alarm); }

.error-msg { font-size: 0.8rem; color: var(--color-alarm); }

.btn-primary {
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 14px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
  margin-top: 8px;
  transition: opacity var(--transition-fast);
}

.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary:active { opacity: 0.85; }

.submit-error { color: var(--color-alarm); font-size: 0.875rem; text-align: center; margin: 0; }

/* 成功状态 */
.success-card {
  width: 100%;
  max-width: 480px;
  background: var(--bg-card);
  border: 1px solid var(--color-healthy);
  border-radius: var(--radius-lg);
  padding: 40px 24px;
  text-align: center;
  margin-top: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.success-icon {
  width: 64px;
  height: 64px;
  background: var(--color-healthy);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: #fff;
  margin-bottom: 8px;
}

.success-card h2 { font-size: 1.4rem; color: var(--color-healthy); margin: 0; }
.success-name { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.success-time { font-size: 0.875rem; color: var(--text-muted); margin: 0; }

.btn-secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 10px 24px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
  margin-top: 8px;
  transition: all var(--transition-fast);
}

.btn-secondary:active { background: var(--bg-elevated); }
</style>
```

- [ ] **Step 2: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/views/mobile/CheckinView.vue
git commit -m "feat: add mobile check-in view"
```

---

### Task 6: 离场签退页

**Files:**
- Create: `frontend/src/views/mobile/CheckoutView.vue`

- [ ] **Step 1: 创建离场签退页**

创建 `frontend/src/views/mobile/CheckoutView.vue`：

```vue
<template>
  <div class="mobile-page">
    <div class="page-header">
      <div class="header-icon">🚪</div>
      <h1>夹层施工离场签退</h1>
      <p>请选择您的姓名完成离场签退</p>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <p>加载中...</p>
    </div>

    <!-- 签退成功 -->
    <div v-else-if="success" class="success-card">
      <div class="success-icon">✓</div>
      <h2>签退成功</h2>
      <p class="success-name">{{ successName }}</p>
      <p class="success-time">离场时间：{{ successTime }}</p>
    </div>

    <!-- 无人在场 -->
    <div v-else-if="!loading && onsite.length === 0" class="empty-state">
      <div class="empty-icon">🏗</div>
      <p>当前无人在夹层作业</p>
    </div>

    <!-- 人员列表 -->
    <template v-else>
      <div class="person-list">
        <div
          v-for="person in onsite"
          :key="person.id"
          class="person-card"
          @click="selectPerson(person)"
        >
          <div class="person-name">{{ person.name }}</div>
          <div class="person-info">{{ person.project }}</div>
          <div class="person-time">入场：{{ person.check_in_at }}</div>
        </div>
      </div>

      <!-- 确认签退弹窗 -->
      <div v-if="selected" class="confirm-overlay" @click.self="selected = null">
        <div class="confirm-card">
          <h3>确认签退</h3>
          <p>{{ selected.name }}，请输入手机号后四位验证身份</p>
          <input
            v-model="phoneLast4"
            type="tel"
            placeholder="手机号后四位"
            maxlength="4"
            class="phone-input"
            @keyup.enter="handleCheckout"
          />
          <p v-if="checkoutError" class="error-msg">{{ checkoutError }}</p>
          <div class="confirm-actions">
            <button class="btn-secondary" @click="selected = null">取消</button>
            <button
              class="btn-primary"
              :disabled="checkingOut || phoneLast4.length !== 4"
              @click="handleCheckout"
            >
              {{ checkingOut ? '签退中...' : '确认签退' }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { mezzanineApi, type MezzanineOnsite } from '@/api/mezzanine'

const onsite = ref<MezzanineOnsite[]>([])
const loading = ref(true)
const selected = ref<MezzanineOnsite | null>(null)
const phoneLast4 = ref('')
const checkingOut = ref(false)
const checkoutError = ref('')
const success = ref(false)
const successName = ref('')
const successTime = ref('')

onMounted(async () => {
  try {
    const { data } = await mezzanineApi.onsite()
    onsite.value = data
  } catch {
    // 静默处理，列表为空
  } finally {
    loading.value = false
  }
})

function selectPerson(person: MezzanineOnsite) {
  selected.value = person
  phoneLast4.value = ''
  checkoutError.value = ''
}

async function handleCheckout() {
  if (!selected.value || phoneLast4.value.length !== 4) return
  checkingOut.value = true
  checkoutError.value = ''
  try {
    const { data } = await mezzanineApi.checkout({
      record_id: selected.value.id,
      phone_last4: phoneLast4.value,
    })
    successName.value = data.name
    successTime.value = data.check_out_at
    selected.value = null
    success.value = true
  } catch (err: any) {
    checkoutError.value = err.response?.data?.error || '签退失败，请重试'
  } finally {
    checkingOut.value = false
  }
}
</script>

<style scoped>
.mobile-page {
  min-height: 100vh;
  background: var(--bg-root);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
  padding-top: 16px;
}

.header-icon { font-size: 2.5rem; margin-bottom: 8px; }

.page-header h1 {
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.page-header p { font-size: 0.875rem; color: var(--text-muted); margin: 0; }

.person-list {
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.person-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.person-card:active { background: var(--bg-elevated); border-color: var(--color-accent); }

.person-name { font-size: 1.05rem; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.person-info { font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 2px; }
.person-time { font-size: 0.8rem; color: var(--text-muted); }

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-icon { font-size: 3rem; margin-bottom: 12px; }

/* 弹窗 */
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}

.confirm-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.confirm-card h3 { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.confirm-card p { font-size: 0.9rem; color: var(--text-secondary); margin: 0; }

.phone-input {
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 1.2rem;
  text-align: center;
  letter-spacing: 0.3em;
  color: var(--text-primary);
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.phone-input:focus { border-color: var(--color-accent); }

.error-msg { color: var(--color-alarm); font-size: 0.85rem; margin: 0; }

.confirm-actions { display: flex; gap: 10px; margin-top: 4px; }

.btn-primary {
  flex: 1;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  flex: 1;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 12px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
}

/* 成功状态 */
.success-card {
  width: 100%;
  max-width: 480px;
  background: var(--bg-card);
  border: 1px solid var(--color-healthy);
  border-radius: var(--radius-lg);
  padding: 40px 24px;
  text-align: center;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.success-icon {
  width: 64px;
  height: 64px;
  background: var(--color-healthy);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: #fff;
}

.success-card h2 { font-size: 1.4rem; color: var(--color-healthy); margin: 0; }
.success-name { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.success-time { font-size: 0.875rem; color: var(--text-muted); margin: 0; }

.loading-state { color: var(--text-muted); margin-top: 60px; }
</style>
```

- [ ] **Step 2: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/views/mobile/CheckoutView.vue
git commit -m "feat: add mobile check-out view"
```

---

### Task 7: 大屏轮播页

**Files:**
- Create: `frontend/src/views/mobile/MezzanineBoardView.vue`

- [ ] **Step 1: 创建大屏轮播页**

创建 `frontend/src/views/mobile/MezzanineBoardView.vue`：

```vue
<template>
  <div class="board-page">
    <!-- 顶部标题栏 -->
    <div class="board-header">
      <div class="header-left">
        <h1 class="board-title">夹层施工现场人员</h1>
        <span class="board-time">{{ currentTime }}</span>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-value">{{ onsite.length }}</span>
          <span class="stat-label">当前在场</span>
        </div>
      </div>
    </div>

    <!-- 无人在场 -->
    <div v-if="onsite.length === 0" class="empty-board">
      <div class="empty-icon">🏗</div>
      <p>当前无人在夹层作业</p>
    </div>

    <!-- 人员卡片轮播 -->
    <div v-else class="cards-container">
      <transition-group name="card-fade" tag="div" class="cards-grid">
        <div
          v-for="person in currentPage"
          :key="person.id"
          class="person-card"
        >
          <div class="card-name">{{ person.name }}</div>
          <div class="card-project">{{ person.project }}</div>
          <div v-if="person.company" class="card-company">{{ person.company }}</div>
          <div class="card-time">
            <span class="time-label">入场</span>
            <span class="time-value">{{ person.check_in_at }}</span>
          </div>
          <div class="card-duration">已在场 {{ getDuration(person.check_in_at) }}</div>
        </div>
      </transition-group>

      <!-- 页码指示器 -->
      <div v-if="totalPages > 1" class="page-indicator">
        <span
          v-for="i in totalPages"
          :key="i"
          class="indicator-dot"
          :class="{ active: i - 1 === currentPageIndex }"
        ></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { mezzanineApi, type MezzanineOnsite } from '@/api/mezzanine'

const PAGE_SIZE = 6       // 每页显示人数
const SLIDE_INTERVAL = 5000   // 5 秒切换
const REFRESH_INTERVAL = 30000 // 30 秒刷新数据

const onsite = ref<MezzanineOnsite[]>([])
const currentPageIndex = ref(0)
const currentTime = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(onsite.value.length / PAGE_SIZE)))

const currentPage = computed(() => {
  const start = currentPageIndex.value * PAGE_SIZE
  return onsite.value.slice(start, start + PAGE_SIZE)
})

function getDuration(checkInAt: string): string {
  const now = new Date()
  const checkin = new Date(checkInAt)
  const diffMs = now.getTime() - checkin.getTime()
  const hours = Math.floor(diffMs / 3600000)
  const minutes = Math.floor((diffMs % 3600000) / 60000)
  return `${hours}h${String(minutes).padStart(2, '0')}m`
}

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

async function fetchData() {
  try {
    const { data } = await mezzanineApi.onsite()
    onsite.value = data
    if (currentPageIndex.value >= totalPages.value) {
      currentPageIndex.value = 0
    }
  } catch {
    // 静默处理，保留上次数据
  }
}

let slideTimer: ReturnType<typeof setInterval>
let refreshTimer: ReturnType<typeof setInterval>
let clockTimer: ReturnType<typeof setInterval>

onMounted(async () => {
  await fetchData()
  updateTime()

  slideTimer = setInterval(() => {
    if (onsite.value.length > 0) {
      currentPageIndex.value = (currentPageIndex.value + 1) % totalPages.value
    }
  }, SLIDE_INTERVAL)

  refreshTimer = setInterval(fetchData, REFRESH_INTERVAL)
  clockTimer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(slideTimer)
  clearInterval(refreshTimer)
  clearInterval(clockTimer)
})
</script>

<style scoped>
.board-page {
  min-height: 100vh;
  background: var(--bg-root);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 40px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.board-title {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 4px;
  letter-spacing: 0.05em;
}

.board-time {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--text-muted);
}

.header-stats { display: flex; gap: 32px; }

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--color-accent);
  line-height: 1;
}

.stat-label { font-size: 0.8rem; color: var(--text-muted); }

.empty-board {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  gap: 16px;
}

.empty-icon { font-size: 4rem; }
.empty-board p { font-size: 1.2rem; }

.cards-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 32px 40px;
  gap: 24px;
  overflow: hidden;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  flex: 1;
}

.person-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all var(--transition-normal);
}

.card-name {
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
}

.card-project {
  font-size: 1rem;
  color: var(--color-accent);
  font-weight: 500;
}

.card-company { font-size: 0.9rem; color: var(--text-secondary); }

.card-time {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: auto;
}

.time-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-elevated);
  padding: 2px 6px;
  border-radius: 3px;
}

.time-value {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.card-duration {
  font-size: 0.85rem;
  color: var(--color-warning);
  font-family: var(--font-mono);
}

/* 轮播动画 */
.card-fade-enter-active,
.card-fade-leave-active { transition: all 0.4s ease; }

.card-fade-enter-from { opacity: 0; transform: translateY(10px); }
.card-fade-leave-to { opacity: 0; transform: translateY(-10px); }

/* 页码指示器 */
.page-indicator {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-default);
  transition: all var(--transition-fast);
}

.indicator-dot.active {
  background: var(--color-accent);
  transform: scale(1.3);
}
</style>
```

- [ ] **Step 2: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/views/mobile/MezzanineBoardView.vue
git commit -m "feat: add mezzanine board display view with auto-refresh"
```

---

## Chunk 4: 管理查询页面

### Task 8: 管理查询页

**Files:**
- Create: `frontend/src/views/safety/MezzanineManageView.vue`

- [ ] **Step 1: 创建管理查询页**

创建 `frontend/src/views/safety/MezzanineManageView.vue`：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">夹层施工管理</h2>
        <p class="page-subtitle">施工人员入离场记录查询</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.today_count }}</div>
        <div class="stat-label">今日入场人次</div>
      </div>
      <div class="stat-card stat-card--accent">
        <div class="stat-value">{{ stats.onsite_count }}</div>
        <div class="stat-label">当前在场人数</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-card">
      <div class="filter-row">
        <el-input
          v-model="filters.search"
          placeholder="姓名 / 手机号"
          clearable
          style="width: 200px"
          @keyup.enter="fetchData"
          @clear="fetchData"
        />
        <el-input
          v-model="filters.project"
          placeholder="施工项目"
          clearable
          style="width: 180px"
          @keyup.enter="fetchData"
          @clear="fetchData"
        />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="fetchData">
          <el-option label="在场中" value="onsite" />
          <el-option label="已离场" value="left" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="~"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="onDateChange"
        />
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" @click="fetchData">查询</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table :data="records" v-loading="loading" style="width: 100%">
        <el-table-column label="姓名" width="100" prop="name" />
        <el-table-column label="手机号" width="130" prop="phone" />
        <el-table-column label="施工单位" min-width="140" prop="company">
          <template #default="{ row }">{{ row.company || '—' }}</template>
        </el-table-column>
        <el-table-column label="施工项目" min-width="180" prop="project" />
        <el-table-column label="入场时间" width="160" prop="check_in_at" />
        <el-table-column label="离场时间" width="160">
          <template #default="{ row }">
            {{ row.check_out_at || '—' }}
          </template>
        </el-table-column>
        <el-table-column label="在场时长" width="100" prop="duration" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <span class="status-tag" :class="row.status === 'onsite' ? 'status-onsite' : 'status-left'">
              {{ row.status === 'onsite' ? '在场中' : '已离场' }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-row">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="20"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { mezzanineApi, type MezzanineRecord } from '@/api/mezzanine'

const loading = ref(false)
const records = ref<MezzanineRecord[]>([])
const total = ref(0)
const currentPage = ref(1)
const dateRange = ref<[string, string] | null>(null)
const stats = reactive({ today_count: 0, onsite_count: 0 })

const filters = reactive({
  search: '',
  project: '',
  status: '' as '' | 'onsite' | 'left',
  date_from: '',
  date_to: '',
})

onMounted(fetchData)

async function fetchData() {
  loading.value = true
  try {
    const { data } = await mezzanineApi.history({
      search: filters.search || undefined,
      project: filters.project || undefined,
      status: filters.status || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      page: currentPage.value,
    })
    records.value = data.results
    total.value = data.count
    stats.today_count = data.stats.today_count
    stats.onsite_count = data.stats.onsite_count
  } finally {
    loading.value = false
  }
}

function onDateChange(val: [string, string] | null) {
  filters.date_from = val?.[0] || ''
  filters.date_to = val?.[1] || ''
  fetchData()
}

function resetFilters() {
  Object.assign(filters, { search: '', project: '', status: '', date_from: '', date_to: '' })
  dateRange.value = null
  currentPage.value = 1
  fetchData()
}
</script>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(2, 200px);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  text-align: center;
}

.stat-card--accent { border-color: var(--color-accent); }

.stat-value {
  font-family: var(--font-mono);
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-accent);
  line-height: 1;
  margin-bottom: 6px;
}

.stat-label { font-size: 0.85rem; color: var(--text-muted); }

.filter-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.table-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.status-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}

.status-onsite {
  background: var(--color-healthy-dim);
  color: var(--color-healthy);
}

.status-left {
  background: var(--bg-elevated);
  color: var(--text-muted);
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid var(--border-subtle);
}
</style>
```

- [ ] **Step 2: 运行 TypeScript 检查**

```bash
cd frontend
npx vue-tsc --noEmit
```

期望：无报错。

- [ ] **Step 3: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/views/safety/MezzanineManageView.vue
git commit -m "feat: add mezzanine management query view"
```

---

### Task 9: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd backend
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

- [ ] **Step 2: 启动前端**

```bash
cd frontend
npm run dev
```

- [ ] **Step 3: 测试入场登记**

用手机或浏览器访问 `http://127.0.0.1:3001/m/checkin`（无需登录）。填写姓名「张三」、手机号「13800138000」、施工项目「电缆敷设」，点提交。应显示「签到成功」。

- [ ] **Step 4: 测试大屏轮播**

访问 `http://127.0.0.1:3001/m/mezzanine-board`（无需登录）。应显示刚刚签到的「张三」，顶部在场人数为 1。

- [ ] **Step 5: 测试离场签退**

访问 `http://127.0.0.1:3001/m/checkout`（无需登录）。应看到「张三」的卡片，点击，输入手机号后四位「8000」，确认签退。应显示「签退成功」。

- [ ] **Step 6: 测试管理查询**

用 `admin / admin123` 登录系统，点击「安全管理 → 夹层施工」，应显示刚才的入离场记录，统计卡片显示今日入场 1 人，当前在场 0 人。

- [ ] **Step 7: 最终提交**

```bash
cd "F:/zs2 Management System"
git add .
git commit -m "feat: complete mezzanine construction management feature"
```

---

## 文件变更汇总

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/apps/safety/models.py` | 修改 | 追加 MezzanineRecord |
| `backend/apps/safety/migrations/` | 自动生成 | MezzanineRecord 迁移 |
| `backend/apps/safety/views.py` | 修改 | 追加 4 个视图函数 |
| `backend/apps/safety/urls.py` | 修改 | 追加 4 条路由 |
| `frontend/src/api/mezzanine.ts` | 新建 | API 模块 |
| `frontend/src/router/index.ts` | 修改 | 新增 4 条路由 |
| `frontend/src/components/layout/SidebarNav.vue` | 修改 | 安全管理下加「夹层施工」 |
| `frontend/src/views/mobile/CheckinView.vue` | 新建 | 入场登记移动页 |
| `frontend/src/views/mobile/CheckoutView.vue` | 新建 | 离场签退移动页 |
| `frontend/src/views/mobile/MezzanineBoardView.vue` | 新建 | 大屏轮播页 |
| `frontend/src/views/safety/MezzanineManageView.vue` | 新建 | 管理查询页 |
