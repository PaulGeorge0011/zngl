# 用户管理 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增「系统设置 → 用户管理」功能，支持安全员对用户账号的增删改查、角色分配和密码重置。

**Architecture:** 后端在 `apps/users` 扩展 UserProfile 模型和 manage 系列 API；前端新增用户列表页 + 编辑抽屉，并在侧边栏加入「系统设置」导航组。

**Tech Stack:** Django 4.2 + DRF, Vue 3 + TypeScript + Element Plus, Pinia

**Spec:** `docs/superpowers/specs/2026-03-22-user-management-design.md`

---

## Chunk 1: 后端模型与迁移

### Task 1: 创建 UserProfile 模型

**Files:**
- Create: `backend/apps/users/models.py`
- Auto-generate: `backend/apps/users/migrations/0001_initial.py`

- [ ] **Step 1: 创建模型文件**

创建 `backend/apps/users/models.py`：

```python
from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Django User 的扩展信息（工号、联系电话）"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile', verbose_name='用户'
    )
    employee_id = models.CharField(
        '工号', max_length=50, unique=True, blank=True, null=True, default=None
    )
    phone = models.CharField('联系电话', max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f"{self.user.username} 的资料"
```

- [ ] **Step 2: 生成并应用迁移**

```bash
cd backend
python manage.py makemigrations users
python manage.py migrate
```

期望输出：`Applying users.0001_initial... OK`

- [ ] **Step 3: 验证**

```bash
cd backend
python manage.py check
```

期望：`System check identified no issues (0 silenced).`

- [ ] **Step 4: 提交**

```bash
cd "F:/zs2 Management System"
git add backend/apps/users/models.py backend/apps/users/migrations/
git commit -m "feat: add UserProfile model for employee_id and phone"
```

---

## Chunk 2: 后端 API

### Task 2: 创建用户管理序列化器

**Files:**
- Create: `backend/apps/users/serializers.py`

- [ ] **Step 1: 创建序列化器**

创建 `backend/apps/users/serializers.py`：

```python
from django.contrib.auth.models import User, Group
from rest_framework import serializers

from .models import UserProfile


def _get_role(user):
    groups = list(user.groups.values_list('name', flat=True))
    if '安全员' in groups:
        return 'safety_officer'
    elif '班组长' in groups:
        return 'team_leader'
    return 'worker'


ROLE_TO_GROUP = {
    'safety_officer': '安全员',
    'team_leader': '班组长',
    'worker': '员工',
}

VALID_ROLES = list(ROLE_TO_GROUP.keys())


class UserManageSerializer(serializers.ModelSerializer):
    """用于用户管理列表和详情展示"""
    name = serializers.CharField(source='first_name', read_only=True)
    role = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'role', 'employee_id', 'phone', 'is_active']

    def get_role(self, obj):
        return _get_role(obj)

    def get_employee_id(self, obj):
        try:
            return obj.profile.employee_id or ''
        except UserProfile.DoesNotExist:
            return ''

    def get_phone(self, obj):
        try:
            return obj.profile.phone
        except UserProfile.DoesNotExist:
            return ''


class UserCreateSerializer(serializers.Serializer):
    """创建用户"""
    username = serializers.CharField(max_length=150)
    name = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=6)
    role = serializers.ChoiceField(choices=VALID_ROLES)
    employee_id = serializers.CharField(max_length=50, allow_blank=True, required=False, default='')
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False, default='')

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_employee_id(self, value):
        if value and UserProfile.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError('工号已存在')
        return value or None

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data['name'],
        )
        group_name = ROLE_TO_GROUP[validated_data['role']]
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.set([group])

        UserProfile.objects.create(
            user=user,
            employee_id=validated_data.get('employee_id') or None,
            phone=validated_data.get('phone', ''),
        )
        return user


class UserUpdateSerializer(serializers.Serializer):
    """编辑用户信息（不含 username 和 password）"""
    name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=VALID_ROLES)
    employee_id = serializers.CharField(max_length=50, allow_blank=True, required=False, default='')
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False, default='')

    def validate_employee_id(self, value):
        user = self.context.get('user')
        if value:
            qs = UserProfile.objects.filter(employee_id=value)
            if user:
                qs = qs.exclude(user=user)
            if qs.exists():
                raise serializers.ValidationError('工号已存在')
        return value or None

    def update(self, user, validated_data):
        user.first_name = validated_data['name']
        user.save(update_fields=['first_name'])

        group_name = ROLE_TO_GROUP[validated_data['role']]
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.set([group])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.employee_id = validated_data.get('employee_id') or None
        profile.phone = validated_data.get('phone', '')
        profile.save(update_fields=['employee_id', 'phone', 'updated_at'])
        return user


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6)
```

- [ ] **Step 2: 提交**

```bash
cd "F:/zs2 Management System"
git add backend/apps/users/serializers.py
git commit -m "feat: add user management serializers"
```

---

### Task 3: 添加用户管理视图与路由

**Files:**
- Modify: `backend/apps/users/views.py`
- Modify: `backend/apps/users/urls.py`

- [ ] **Step 1: 在 views.py 末尾追加管理视图**

先读取 `backend/apps/users/views.py` 确认现有 import，然后：

1. 在文件顶部现有 import 块末尾**新增一行**（不重复已有 import）：
```python
from apps.safety.permissions import IsSafetyOfficer
```
以及：
```python
from django.db.models import Q
```

2. 在文件顶部补充缺失的 model import（`from django.contrib.auth.models import User` 已存在，跳过）：
```python
from .models import UserProfile
from .serializers import (
    UserManageSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ResetPasswordSerializer,
)
```

3. 在文件**末尾**追加以下视图函数：

```python
# ── 用户管理（安全员专用写操作，所有人可读）────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_list_create(request):
    """
    GET  — 列出所有用户（已登录用户均可）
    POST — 创建新用户（仅安全员）
    """
    if request.method == 'GET':
        return _manage_list(request)

    # POST：仅安全员
    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'error': '只有安全员可以创建用户'}, status=403)
    return _manage_create(request)


def _manage_list(request):
    search = request.query_params.get('search', '').strip()
    qs = User.objects.prefetch_related('groups', 'profile').order_by('id')
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(username__icontains=search) |
            Q(profile__employee_id__icontains=search)
        )
    return Response(UserManageSerializer(qs, many=True).data)


def _manage_create(request):
    serializer = UserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    logger.info(f"用户创建: {user.username} by {request.user.username}")
    return Response(UserManageSerializer(user).data, status=201)


@api_view(['PUT'])
@permission_classes([IsSafetyOfficer])
def manage_update(request, pk):
    """编辑用户信息（姓名、角色、工号、电话）"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=404)

    serializer = UserUpdateSerializer(data=request.data, context={'user': user})
    serializer.is_valid(raise_exception=True)
    serializer.update(user, serializer.validated_data)
    logger.info(f"用户编辑: {user.username} by {request.user.username}")
    return Response(UserManageSerializer(user).data)


@api_view(['PATCH'])
@permission_classes([IsSafetyOfficer])
def manage_toggle(request, pk):
    """切换用户启用/禁用状态"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=404)

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    action = '启用' if user.is_active else '禁用'
    logger.info(f"用户{action}: {user.username} by {request.user.username}")
    return Response(UserManageSerializer(user).data)


@api_view(['POST'])
@permission_classes([IsSafetyOfficer])
def manage_reset_password(request, pk):
    """重置用户密码"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=404)

    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user.set_password(serializer.validated_data['password'])
    user.save(update_fields=['password'])
    logger.info(f"密码重置: {user.username} by {request.user.username}")
    return Response({'message': '密码已重置'})
```

- [ ] **Step 2: 更新 urls.py**

将 `backend/apps/users/urls.py` 替换为：

```python
from django.urls import path
from . import views

urlpatterns = [
    # 认证
    path('login/', views.login_view, name='users-login'),
    path('logout/', views.logout_view, name='users-logout'),
    path('me/', views.me_view, name='users-me'),
    path('list/', views.user_list_view, name='users-list'),

    # 用户管理（GET=所有人, POST=安全员）
    path('manage/', views.manage_list_create, name='users-manage'),
    # 以下接口均需安全员权限
    path('manage/<int:pk>/', views.manage_update, name='users-manage-update'),
    path('manage/<int:pk>/toggle/', views.manage_toggle, name='users-manage-toggle'),
    path('manage/<int:pk>/reset-password/', views.manage_reset_password, name='users-manage-reset-password'),
]
```

- [ ] **Step 3: 验证**

```bash
cd backend
python manage.py check
```

期望：`System check identified no issues (0 silenced).`

- [ ] **Step 4: 冒烟测试（需后端已运行）**

```bash
# 先登录获取 cookie
curl -s -c /tmp/cookies.txt -X POST http://127.0.0.1:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 测试用户列表
curl -s -b /tmp/cookies.txt http://127.0.0.1:8000/api/users/manage/
```

期望：返回用户列表 JSON 数组。

- [ ] **Step 5: 提交**

```bash
cd "F:/zs2 Management System"
git add backend/apps/users/views.py backend/apps/users/urls.py
git commit -m "feat: add user manage API (list, create, update, toggle, reset-password)"
```

---

## Chunk 3: 前端 API 与路由

### Task 4: 扩展前端用户 API 模块

**Files:**
- Modify: `frontend/src/api/users.ts`

- [ ] **Step 1: 读取当前 users.ts 内容，然后追加管理 API**

将 `frontend/src/api/users.ts` 替换为完整内容：

```typescript
import http from './http'
import type { UserInfo } from '@/stores/user'

// ── 认证相关（原有）─────────────────────────────────────────────────────────

export const usersApi = {
  login(username: string, password: string) {
    return http.post<UserInfo>('/api/users/login/', { username, password })
  },

  logout() {
    return http.post('/api/users/logout/')
  },

  me() {
    return http.get<UserInfo>('/api/users/me/')
  },

  list(role?: string) {
    return http.get<UserInfo[]>('/api/users/list/', { params: role ? { role } : {} })
  },
}

// ── 用户管理相关（新增）──────────────────────────────────────────────────────

export interface ManagedUser {
  id: number
  username: string
  name: string
  role: 'worker' | 'team_leader' | 'safety_officer'
  employee_id: string
  phone: string
  is_active: boolean
}

export interface CreateUserPayload {
  username: string
  name: string
  password: string
  role: string
  employee_id?: string
  phone?: string
}

export interface UpdateUserPayload {
  name: string
  role: string
  employee_id?: string
  phone?: string
}

export const userManageApi = {
  list(search?: string) {
    return http.get<ManagedUser[]>('/api/users/manage/', {
      params: search ? { search } : {},
    })
  },

  create(data: CreateUserPayload) {
    return http.post<ManagedUser>('/api/users/manage/', data)
  },

  update(id: number, data: UpdateUserPayload) {
    return http.put<ManagedUser>(`/api/users/manage/${id}/`, data)
  },

  toggle(id: number) {
    return http.patch<ManagedUser>(`/api/users/manage/${id}/toggle/`)
  },

  resetPassword(id: number, password: string) {
    return http.post(`/api/users/manage/${id}/reset-password/`, { password })
  },
}
```

- [ ] **Step 2: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/api/users.ts
git commit -m "feat: add user management API module"
```

---

### Task 5: 添加路由并更新侧边栏

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/layout/SidebarNav.vue`

- [ ] **Step 1: 在 router/index.ts 的 children 数组末尾添加设置路由**

在现有最后一个子路由（`safety/hazard/:id`）之后，追加：

```typescript
{
  path: 'settings/users',
  name: 'UserManage',
  component: () => import('@/views/settings/UserManageView.vue'),
  meta: { title: '用户管理' },
},
```

- [ ] **Step 2: 在 SidebarNav.vue 添加「系统设置」导航组**

先读取 `frontend/src/components/layout/SidebarNav.vue` 文件，找到安全管理导航组的结束位置（`</div>` 关闭处），在其后、底部状态栏之前插入系统设置导航组。

参考现有安全管理导航组的结构，新增内容如下（放在安全管理组之后）：

```html
<!-- 系统设置 -->
<div class="nav-group">
  <button class="nav-group-header" @click="toggleSettings">
    <div class="nav-group-left">
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="7.5" cy="7.5" r="2"/>
        <path d="M7.5 1v1.5M7.5 12.5V14M1 7.5h1.5M12.5 7.5H14M2.8 2.8l1 1M11.2 11.2l1 1M11.2 2.8l-1 1M3.8 11.2l-1 1"/>
      </svg>
      <span>系统设置</span>
    </div>
    <svg class="chevron" :class="{ rotated: settingsExpanded }" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M3 4.5l3 3 3-3"/>
    </svg>
  </button>
  <div class="nav-sub" :class="{ open: settingsExpanded }">
    <router-link to="/settings/users" class="nav-sub-item" active-class="active">
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="6.5" cy="4" r="2.5"/>
        <path d="M1 12c0-3 2.5-5 5.5-5s5.5 2 5.5 5"/>
      </svg>
      用户管理
    </router-link>
  </div>
</div>
```

在 `<script setup>` 中添加对应的响应式变量和函数（参考现有的 `safetyExpanded`、`toggleSafety` 模式）：

```typescript
const settingsExpanded = ref(false)
const isSettingsGroupActive = computed(() => route.path.startsWith('/settings'))
watch(isSettingsGroupActive, (v) => { if (v) settingsExpanded.value = true }, { immediate: true })
function toggleSettings() { settingsExpanded.value = !settingsExpanded.value }
```

- [ ] **Step 3: 验证前端启动无报错**

```bash
cd frontend
npm run dev
```

打开浏览器访问系统，确认左侧导航栏底部出现「系统设置」折叠菜单，展开后显示「用户管理」。

- [ ] **Step 4: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/router/index.ts frontend/src/components/layout/SidebarNav.vue
git commit -m "feat: add settings route and sidebar navigation group"
```

---

## Chunk 4: 前端页面

### Task 6: 创建用户编辑抽屉组件

**Files:**
- Create: `frontend/src/components/users/UserDrawer.vue`

- [ ] **Step 1: 创建抽屉组件**

创建 `frontend/src/components/users/UserDrawer.vue`：

```vue
<template>
  <el-drawer
    v-model="visible"
    :title="isEdit ? '编辑用户' : '新建用户'"
    size="480px"
    :before-close="handleClose"
    direction="rtl"
  >
    <el-tabs v-model="activeTab">
      <!-- 标签页一：基本信息 -->
      <el-tab-pane label="基本信息" name="basic">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="姓名" prop="name">
            <el-input v-model="form.name" placeholder="请输入姓名" />
          </el-form-item>

          <el-form-item label="用户名（登录账号）" prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              :disabled="isEdit"
            />
          </el-form-item>

          <el-form-item label="工号" prop="employee_id">
            <el-input v-model="form.employee_id" placeholder="如：EMP001（可选）" />
          </el-form-item>

          <el-form-item label="联系电话" prop="phone">
            <el-input v-model="form.phone" placeholder="如：13800138000（可选）" />
          </el-form-item>

          <el-form-item v-if="!isEdit" label="初始密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="至少6位"
              show-password
            />
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 标签页二：角色与权限 -->
      <el-tab-pane label="角色与权限" name="role">
        <el-form label-position="top">
          <el-form-item label="角色">
            <el-radio-group v-model="form.role" style="flex-direction: column; gap: 12px; align-items: flex-start">
              <el-radio value="safety_officer">安全员 — 可分派隐患、验证整改、管理用户</el-radio>
              <el-radio value="team_leader">班组长 — 可提交整改</el-radio>
              <el-radio value="worker">员工 — 可上报隐患</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 重置密码（仅编辑模式） -->
          <template v-if="isEdit">
            <el-divider>重置密码</el-divider>
            <el-form-item label="新密码">
              <el-input
                v-model="newPassword"
                type="password"
                placeholder="至少6位"
                show-password
                style="width: 240px"
              />
            </el-form-item>
            <el-button
              :loading="resetting"
              :disabled="newPassword.length < 6"
              @click="handleResetPassword"
            >
              重置密码
            </el-button>
          </template>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { userManageApi, type ManagedUser } from '@/api/users'

const props = defineProps<{
  modelValue: boolean
  user?: ManagedUser | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.user)
const activeTab = ref('basic')
const formRef = ref<FormInstance>()
const saving = ref(false)
const resetting = ref(false)
const newPassword = ref('')

const form = reactive({
  name: '',
  username: '',
  employee_id: '',
  phone: '',
  password: '',
  role: 'worker' as string,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
}

// 打开抽屉时初始化表单
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      activeTab.value = 'basic'
      newPassword.value = ''
      if (props.user) {
        form.name = props.user.name
        form.username = props.user.username
        form.employee_id = props.user.employee_id
        form.phone = props.user.phone
        form.password = ''
        form.role = props.user.role
      } else {
        Object.assign(form, { name: '', username: '', employee_id: '', phone: '', password: '', role: 'worker' })
      }
    }
  }
)

function handleClose() {
  visible.value = false
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    activeTab.value = 'basic'
    return
  }

  saving.value = true
  try {
    if (isEdit.value && props.user) {
      await userManageApi.update(props.user.id, {
        name: form.name,
        role: form.role,
        employee_id: form.employee_id,
        phone: form.phone,
      })
      ElMessage.success('用户信息已更新')
    } else {
      await userManageApi.create({
        username: form.username,
        name: form.name,
        password: form.password,
        role: form.role,
        employee_id: form.employee_id,
        phone: form.phone,
      })
      ElMessage.success('用户创建成功')
    }
    visible.value = false
    emit('saved')
  } catch {
    // 错误由 http 拦截器展示
  } finally {
    saving.value = false
  }
}

async function handleResetPassword() {
  if (!props.user) return
  resetting.value = true
  try {
    await userManageApi.resetPassword(props.user.id, newPassword.value)
    ElMessage.success('密码已重置')
    newPassword.value = ''
  } catch {
    // 错误由 http 拦截器展示
  } finally {
    resetting.value = false
  }
}
</script>
```

- [ ] **Step 2: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/components/users/UserDrawer.vue
git commit -m "feat: add user edit drawer component"
```

---

### Task 7: 创建用户列表页

**Files:**
- Create: `frontend/src/views/settings/UserManageView.vue`

- [ ] **Step 1: 创建用户列表页**

创建 `frontend/src/views/settings/UserManageView.vue`：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">用户管理</h2>
        <p class="page-subtitle">管理系统账号与角色权限</p>
      </div>
      <el-button
        v-if="userStore.isSafetyOfficer"
        type="primary"
        @click="openDrawer(null)"
      >
        + 新建用户
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="filter-card">
      <el-input
        v-model="searchText"
        placeholder="搜索姓名 / 用户名 / 工号"
        clearable
        style="width: 280px"
        @keyup.enter="fetchUsers"
        @clear="fetchUsers"
      />
      <el-button @click="fetchUsers">搜索</el-button>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column label="姓名" min-width="100">
          <template #default="{ row }">
            <span :class="{ 'text-muted': !row.is_active }">{{ row.name || row.username }}</span>
          </template>
        </el-table-column>
        <el-table-column label="用户名" width="130" prop="username" />
        <el-table-column label="工号" width="120" prop="employee_id">
          <template #default="{ row }">{{ row.employee_id || '—' }}</template>
        </el-table-column>
        <el-table-column label="联系电话" width="140" prop="phone">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <span class="status-dot" :class="row.is_active ? 'active' : 'inactive'">
              {{ row.is_active ? '启用' : '禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column v-if="userStore.isSafetyOfficer" label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openDrawer(row)">编辑</el-button>
            <el-button
              text
              size="small"
              :type="row.is_active ? 'danger' : 'success'"
              @click="handleToggle(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 抽屉 -->
    <UserDrawer v-model="drawerVisible" :user="drawerUser" @saved="fetchUsers" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { userManageApi, type ManagedUser } from '@/api/users'
import { useUserStore } from '@/stores/user'
import UserDrawer from '@/components/users/UserDrawer.vue'

const userStore = useUserStore()
const loading = ref(false)
const users = ref<ManagedUser[]>([])
const searchText = ref('')
const drawerVisible = ref(false)
const drawerUser = ref<ManagedUser | null>(null)

onMounted(fetchUsers)

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await userManageApi.list(searchText.value || undefined)
    users.value = data
  } finally {
    loading.value = false
  }
}

function openDrawer(user: ManagedUser | null) {
  drawerUser.value = user
  drawerVisible.value = true
}

async function handleToggle(user: ManagedUser) {
  const action = user.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${user.name || user.username}」吗？`,
      '确认操作',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await userManageApi.toggle(user.id)
    ElMessage.success(`已${action}`)
    fetchUsers()
  } catch {
    // 错误由拦截器展示
  }
}

const ROLE_LABELS: Record<string, string> = {
  safety_officer: '安全员',
  team_leader: '班组长',
  worker: '员工',
}

const ROLE_TAG_TYPES: Record<string, string> = {
  safety_officer: 'danger',
  team_leader: 'warning',
  worker: 'info',
}

function roleLabel(role: string) { return ROLE_LABELS[role] || role }
function roleTagType(role: string) { return ROLE_TAG_TYPES[role] || 'info' }
</script>

<style scoped>
.filter-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.table-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.text-muted {
  opacity: 0.45;
}

.status-dot {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}

.status-dot.active {
  background: var(--color-healthy-dim);
  color: var(--color-healthy);
}

.status-dot.inactive {
  background: var(--color-alarm-dim);
  color: var(--color-alarm);
}
</style>
```

- [ ] **Step 2: 运行 TypeScript 检查**

```bash
cd frontend
npx vue-tsc --noEmit
```

期望：无报错输出。

- [ ] **Step 3: 提交**

```bash
cd "F:/zs2 Management System"
git add frontend/src/views/settings/UserManageView.vue
git commit -m "feat: add user management list view"
```

---

### Task 8: 端到端验证

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

- [ ] **Step 3: 测试完整流程**

1. 用 `admin / admin123`（安全员）登录
2. 点击左侧「系统设置」→「用户管理」，应看到用户列表
3. 点击「新建用户」，填写姓名、用户名、工号、电话、初始密码，选角色「员工」，点「创建」
4. 列表中出现新用户 ✓
5. 点「编辑」，修改姓名和角色，保存
6. 点「禁用」，确认后用户状态变为禁用 ✓
7. 在「角色与权限」标签页，填写新密码，点「重置密码」✓
8. 用 `worker1 / worker123`（员工）登录，进入用户管理页，应只能查看，无操作按钮 ✓

- [ ] **Step 4: 最终提交**

```bash
cd "F:/zs2 Management System"
git add .
git commit -m "feat: complete user management feature"
```

---

## 文件变更汇总

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/apps/users/models.py` | 新建 | UserProfile 模型 |
| `backend/apps/users/serializers.py` | 新建 | 用户管理序列化器 |
| `backend/apps/users/migrations/` | 自动生成 | UserProfile 迁移 |
| `backend/apps/users/views.py` | 追加 | 5 个 manage 视图函数 |
| `backend/apps/users/urls.py` | 修改 | 新增 manage 路由 |
| `frontend/src/api/users.ts` | 修改 | 新增 userManageApi |
| `frontend/src/router/index.ts` | 修改 | 新增 /settings/users 路由 |
| `frontend/src/components/layout/SidebarNav.vue` | 修改 | 新增系统设置导航组 |
| `frontend/src/components/users/UserDrawer.vue` | 新建 | 用户编辑抽屉 |
| `frontend/src/views/settings/UserManageView.vue` | 新建 | 用户列表页 |
