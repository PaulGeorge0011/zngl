# 随手拍找隐患 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hazard reporting feature ("随手拍") to the Safety Management module with photo upload, three-level workflow (report → assign → fix → verify), and historical query with filters.

**Architecture:** Django Session auth with three user roles (员工/班组长/安全员) introduced via a new `apps/users` URL module; `Location`, `HazardReport`, and `HazardImage` models extend `apps/safety`; four new Vue views (login, list, detail, report) with a Pinia user store and route guards.

**Tech Stack:** Django 4.2, DRF SessionAuthentication, Pillow (ImageField), Vue 3 + TypeScript, Element Plus, Pinia

**Spec:** `docs/superpowers/specs/2026-03-21-hazard-reporting-design.md`

---

## Chunk 1: Backend Foundation

### Task 1: Configure Settings for Auth, Media & CSRF

**Files:**
- Modify: `backend/config/settings/base.py`

- [ ] **Step 1: Add settings**

Open `backend/config/settings/base.py` and add after the `CORS_ALLOW_ALL_ORIGINS = True` line:

```python
# Auth & Session
LOGIN_URL = '/api/users/login/'
SESSION_COOKIE_AGE = 86400  # 1 day
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF
CSRF_TRUSTED_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173']
CORS_ALLOW_CREDENTIALS = True

# Media files (for hazard images)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
```

Also update the `REST_FRAMEWORK` dict to add authentication:

```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

And add `apps.users` to `INSTALLED_APPS` (after `apps.safety`):

```python
    'apps.users',
```

- [ ] **Step 2: Add media URL serving to config/urls.py**

Open `backend/config/urls.py` and update to:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.users.urls')),
    path('api/equipment/', include('apps.equipment.urls')),
    path('api/monitoring/', include('apps.monitoring.urls')),
    path('api/ai/', include('apps.ai_analysis.urls')),
    path('api/quality/', include('apps.quality.urls')),
    path('api/safety/', include('apps.safety.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 3: Install Pillow (required for ImageField)**

```bash
cd backend
pip install Pillow
```

Add to `backend/requirements.txt`:
```
Pillow>=10.0.0
```

- [ ] **Step 4: Verify backend starts without errors**

```bash
cd backend
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```bash
git add backend/config/settings/base.py backend/config/urls.py backend/requirements.txt
git commit -m "feat: configure session auth, CSRF, media upload settings"
```

---

### Task 2: Create Users App

**Files:**
- Create: `backend/apps/users/__init__.py`
- Create: `backend/apps/users/apps.py`
- Create: `backend/apps/users/views.py`
- Create: `backend/apps/users/urls.py`

- [ ] **Step 1: Create the users app directory and files**

Create `backend/apps/users/__init__.py` (empty file).

Create `backend/apps/users/apps.py`:

```python
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = '用户管理'
```

- [ ] **Step 2: Create users views**

Create `backend/apps/users/views.py`:

```python
import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _user_data(user):
    """Return serializable dict for a User.

    IMPORTANT: Django's built-in User has no 'role' field.
    We synthesize it here from group membership (安全员 > 班组长 > 员工).
    This is what the frontend UserInfo.role stores and uses for permission checks.
    """
    groups = list(user.groups.values_list('name', flat=True))
    # Determine primary role (安全员 > 班组长 > 员工)
    if '安全员' in groups:
        role = 'safety_officer'
    elif '班组长' in groups:
        role = 'team_leader'
    else:
        role = 'worker'
    return {
        'id': user.id,
        'username': user.username,
        'display_name': user.get_full_name() or user.username,
        'role': role,
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    if not username or not password:
        return Response({'error': '请输入用户名和密码'}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'error': '用户名或密码错误'}, status=401)
    if not user.is_active:
        return Response({'error': '账号已禁用'}, status=403)

    login(request, user)
    logger.info(f"User {username} logged in")
    return Response(_user_data(user))


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({'message': '已退出登录'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(_user_data(request.user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_view(request):
    """List users. Supports ?role=班组长 filter."""
    role_filter = request.query_params.get('role')
    qs = User.objects.filter(is_active=True).prefetch_related('groups')
    if role_filter:
        qs = qs.filter(groups__name=role_filter)
    return Response([_user_data(u) for u in qs])
```

- [ ] **Step 3: Create users URLs**

Create `backend/apps/users/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='users-login'),
    path('logout/', views.logout_view, name='users-logout'),
    path('me/', views.me_view, name='users-me'),
    path('list/', views.user_list_view, name='users-list'),
]
```

- [ ] **Step 4: Verify no import errors**

```bash
cd backend
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```bash
git add backend/apps/users/
git commit -m "feat: add users app with login/logout/me/list endpoints"
```

---

### Task 3: Create Safety Models

**Files:**
- Create: `backend/apps/safety/models.py`
- Create: `backend/apps/safety/admin.py`
- Create: migration file (auto-generated)

- [ ] **Step 1: Create models**

Create `backend/apps/safety/models.py`:

```python
from django.db import models
from django.contrib.auth.models import User


class Location(models.Model):
    """可配置的车间区域"""
    name = models.CharField('区域名称', max_length=50, unique=True)
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True)

    class Meta:
        verbose_name = '区域'
        verbose_name_plural = '区域'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class HazardReport(models.Model):
    """安全隐患上报"""

    LEVEL_CHOICES = [
        ('general', '一般隐患'),
        ('major', '重大隐患'),
    ]
    STATUS_CHOICES = [
        ('pending', '待分派'),
        ('fixing', '整改中'),
        ('verifying', '待验证'),
        ('closed', '已关闭'),
        ('rejected', '驳回'),
    ]

    title = models.CharField('标题', max_length=100)
    description = models.TextField('描述')
    level = models.CharField('等级', max_length=10, choices=LEVEL_CHOICES)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, verbose_name='区域'
    )
    location_detail = models.CharField('具体位置', max_length=200, blank=True)
    status = models.CharField(
        '状态', max_length=20, choices=STATUS_CHOICES, default='pending'
    )

    # 上报
    reporter = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='reported_hazards', verbose_name='上报人'
    )

    # 分派
    assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_hazards', verbose_name='整改责任人'
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dispatched_hazards', verbose_name='分派人'
    )
    assigned_at = models.DateTimeField('分派时间', null=True, blank=True)

    # 整改
    fix_description = models.TextField('整改说明', blank=True)
    fixed_at = models.DateTimeField('整改完成时间', null=True, blank=True)

    # 验证
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_hazards', verbose_name='验证人'
    )
    verified_at = models.DateTimeField('验证时间', null=True, blank=True)
    verify_remark = models.TextField('验证备注', blank=True)

    created_at = models.DateTimeField('上报时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '隐患上报'
        verbose_name_plural = '隐患上报'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"


class HazardImage(models.Model):
    """隐患图片"""

    PHASE_CHOICES = [
        ('report', '上报'),
        ('fix', '整改'),
    ]

    hazard = models.ForeignKey(
        HazardReport, on_delete=models.CASCADE,
        related_name='images', verbose_name='隐患'
    )
    image = models.ImageField('图片', upload_to='hazards/%Y/%m/')
    phase = models.CharField('阶段', max_length=10, choices=PHASE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '隐患图片'
        verbose_name_plural = '隐患图片'
```

- [ ] **Step 2: Create admin**

Create `backend/apps/safety/admin.py`:

```python
from django.contrib import admin
from .models import Location, HazardReport, HazardImage


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'is_active']
    list_editable = ['sort_order', 'is_active']
    ordering = ['sort_order', 'name']


class HazardImageInline(admin.TabularInline):
    model = HazardImage
    extra = 0
    readonly_fields = ['phase', 'created_at']


@admin.register(HazardReport)
class HazardReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'location', 'status', 'reporter', 'created_at']
    list_filter = ['status', 'level', 'location']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [HazardImageInline]
```

- [ ] **Step 3: Generate and apply migration**

```bash
cd backend
python manage.py makemigrations safety
python manage.py migrate
```

Expected output includes: `Creating tables for apps.safety Location, HazardReport, HazardImage`

- [ ] **Step 4: Commit**

```bash
git add backend/apps/safety/models.py backend/apps/safety/admin.py backend/apps/safety/migrations/
git commit -m "feat: add Location, HazardReport, HazardImage models"
```

---

### Task 4: Create Seed Data Script

**Files:**
- Create: `backend/scripts/init_safety_data.py`

- [ ] **Step 1: Create seed script**

Create `backend/scripts/init_safety_data.py`:

```python
"""
初始化安全模块种子数据：区域 + 演示用户
运行方式：python manage.py shell < scripts/init_safety_data.py
"""
from django.contrib.auth.models import User, Group
from apps.safety.models import Location

# ── 区域 ──────────────────────────────────────────────────────────────────────
LOCATIONS = [
    ('松散回潮', 1), ('切片', 2), ('加料', 3), ('烘丝', 4),
    ('加香', 5), ('储丝', 6), ('配送', 7), ('公共区域', 8), ('办公区域', 9),
]

created = 0
for name, order in LOCATIONS:
    _, made = Location.objects.get_or_create(name=name, defaults={'sort_order': order})
    if made:
        created += 1

print(f"区域：新建 {created} 条，已有 {len(LOCATIONS) - created} 条")

# ── 角色组 ────────────────────────────────────────────────────────────────────
GROUP_NAMES = ['员工', '班组长', '安全员']
groups = {}
for gname in GROUP_NAMES:
    g, _ = Group.objects.get_or_create(name=gname)
    groups[gname] = g

print(f"角色组已就绪：{GROUP_NAMES}")

# ── 演示用户 ──────────────────────────────────────────────────────────────────
DEMO_USERS = [
    ('admin',   '系统管理员', 'admin123',   '安全员'),
    ('leader1', '班组长一',   'leader123',  '班组长'),
    ('worker1', '员工一',     'worker123',  '员工'),
]

for username, fullname, password, role in DEMO_USERS:
    if not User.objects.filter(username=username).exists():
        u = User.objects.create_user(
            username=username,
            password=password,
            first_name=fullname,
            is_staff=(role == '安全员'),
        )
        u.groups.add(groups[role])
        print(f"  创建用户 {username}（{role}）")
    else:
        print(f"  用户 {username} 已存在，跳过")

print("种子数据初始化完成")
```

- [ ] **Step 2: Run the seed script**

```bash
cd backend
python manage.py shell < scripts/init_safety_data.py
```

Expected output:
```
区域：新建 9 条，已有 0 条
角色组已就绪：['员工', '班组长', '安全员']
  创建用户 admin（安全员）
  创建用户 leader1（班组长）
  创建用户 worker1（员工）
种子数据初始化完成
```

- [ ] **Step 3: Verify in Django admin**

Start the server and visit `http://localhost:8000/admin/`. Log in with `admin/admin123`. Confirm that:
- Location admin shows 9 areas
- Users admin shows the 3 demo users with correct groups

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/init_safety_data.py
git commit -m "feat: add safety seed data script (locations + demo users)"
```

---

## Chunk 2: Backend API

### Task 5: Create Safety Serializers

**Files:**
- Create: `backend/apps/safety/serializers.py`

- [ ] **Step 1: Create serializers**

Create `backend/apps/safety/serializers.py`:

```python
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from .models import Location, HazardReport, HazardImage


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'sort_order']


class HazardImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = HazardImage
        fields = ['id', 'image_url', 'phase', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class UserBriefSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name']

    def get_display_name(self, obj):
        return obj.get_full_name() or obj.username


class HazardListSerializer(serializers.ModelSerializer):
    reporter = UserBriefSerializer(read_only=True)
    assignee = UserBriefSerializer(read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = HazardReport
        fields = [
            'id', 'title', 'level', 'level_display',
            'location', 'location_name', 'location_detail',
            'status', 'status_display',
            'reporter', 'assignee', 'created_at',
        ]


class HazardDetailSerializer(serializers.ModelSerializer):
    reporter = UserBriefSerializer(read_only=True)
    assignee = UserBriefSerializer(read_only=True)
    assigned_by = UserBriefSerializer(read_only=True)
    verified_by = UserBriefSerializer(read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    images = HazardImageSerializer(many=True, read_only=True)

    class Meta:
        model = HazardReport
        fields = [
            'id', 'title', 'description',
            'level', 'level_display',
            'location', 'location_name', 'location_detail',
            'status', 'status_display',
            'reporter', 'assignee', 'assigned_by', 'assigned_at',
            'fix_description', 'fixed_at',
            'verified_by', 'verified_at', 'verify_remark',
            'created_at', 'updated_at',
            'images',
        ]


class HazardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HazardReport
        fields = ['title', 'description', 'level', 'location', 'location_detail']

    def validate_level(self, value):
        if value not in ('general', 'major'):
            raise serializers.ValidationError('等级无效')
        return value
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/safety/serializers.py
git commit -m "feat: add safety serializers (location, hazard list/detail/create)"
```

---

### Task 6: Create Safety Permissions

**Files:**
- Create: `backend/apps/safety/permissions.py`

> **Note:** `IsAssignee` is defined here for clarity and potential reuse. The `hazard_fix` view uses an equivalent inline check (`hazard.assignee != request.user`) because the object must be fetched anyway. Both approaches are valid; the class is not dead code — it documents the intended permission boundary.

- [ ] **Step 1: Create permissions**

Create `backend/apps/safety/permissions.py`:

```python
from rest_framework.permissions import BasePermission


def _in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


class IsSafetyOfficer(BasePermission):
    """只有安全员可以操作"""
    message = '只有安全员可以执行此操作'

    def has_permission(self, request, view):
        return request.user.is_authenticated and _in_group(request.user, '安全员')


class IsAssignee(BasePermission):
    """只有该隐患的整改责任人可以提交整改"""
    message = '只有整改责任人可以提交整改'

    def has_object_permission(self, request, view, obj):
        return request.user == obj.assignee
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/safety/permissions.py
git commit -m "feat: add safety permission classes"
```

---

### Task 7: Create Safety Views and Update URLs

**Files:**
- Modify: `backend/apps/safety/views.py`
- Modify: `backend/apps/safety/urls.py`

- [ ] **Step 1: Update safety views**

Open `backend/apps/safety/views.py` and append the following after the existing `search_knowledge` view (keep that view intact):

```python
import logging
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Location, HazardReport, HazardImage
from .serializers import (
    LocationSerializer,
    HazardCreateSerializer,
    HazardListSerializer,
    HazardDetailSerializer,
)
from .permissions import IsSafetyOfficer, IsAssignee
```

> **NOTE:** The existing `views.py` already imports `logging`, `requests`, `settings`, and `Response`. Replace the entire file with the content below to avoid duplicate imports:

Full replacement content for `backend/apps/safety/views.py`:

```python
import logging
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Location, HazardReport, HazardImage
from .serializers import (
    LocationSerializer,
    HazardCreateSerializer,
    HazardListSerializer,
    HazardDetailSerializer,
)
from .permissions import IsSafetyOfficer, IsAssignee

logger = logging.getLogger(__name__)


# ── Knowledge Base (existing) ─────────────────────────────────────────────────

@api_view(['POST'])
def search_knowledge(request):
    """
    查询 RAGflow 安全知识库
    请求体：{"question": "问题内容", "top_n": 5}
    """
    question = request.data.get('question', '').strip()
    if not question:
        return Response({'error': '请输入查询内容'}, status=400)

    top_n = int(request.data.get('top_n', 5))

    if not settings.RAGFLOW_API_KEY or not settings.RAGFLOW_BASE_URL:
        return Response({'error': 'RAGflow 未配置，请联系管理员'}, status=503)

    dataset_id = settings.RAGFLOW_SAFETY_DATASET_ID
    if not dataset_id:
        return Response({'error': '安全知识库未配置'}, status=503)

    url = f"{settings.RAGFLOW_BASE_URL}/api/v1/retrieval"
    headers = {
        "Authorization": f"Bearer {settings.RAGFLOW_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "question": question,
        "dataset_ids": [dataset_id],
        "top_n": top_n,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        chunks = data.get('data', {}).get('chunks', [])

        results = [
            {
                'content': c.get('content', ''),
                'document_name': c.get('document_keyword', '') or c.get('docnm_kwd', ''),
                'score': round(c.get('similarity', 0), 3),
            }
            for c in chunks
        ]

        logger.info(f"安全知识库查询: '{question}' 返回 {len(results)} 条")
        return Response({'question': question, 'results': results, 'total': len(results)})

    except requests.exceptions.ConnectionError:
        return Response({'error': '无法连接到 RAGflow 服务'}, status=503)
    except Exception as e:
        logger.error(f"安全知识库查询失败: {e}")
        return Response({'error': f'查询失败: {str(e)}'}, status=500)


# ── Locations ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def location_list(request):
    """返回启用的区域列表"""
    locations = Location.objects.filter(is_active=True)
    return Response(LocationSerializer(locations, many=True).data)


# ── Hazard Reports ────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def hazard_list_create(request):
    if request.method == 'GET':
        return _hazard_list(request)
    return _hazard_create(request)


def _hazard_list(request):
    qs = HazardReport.objects.select_related(
        'location', 'reporter', 'assignee'
    ).all()

    # Filters
    status_filter = request.query_params.get('status')
    level_filter = request.query_params.get('level')
    location_filter = request.query_params.get('location')
    reporter_filter = request.query_params.get('reporter')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    search = request.query_params.get('search', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if level_filter:
        qs = qs.filter(level=level_filter)
    if location_filter:
        qs = qs.filter(location_id=location_filter)
    if reporter_filter:
        qs = qs.filter(reporter_id=reporter_filter)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(description__icontains=search)

    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    total = qs.count()
    items = qs[start:end]

    serializer = HazardListSerializer(items, many=True, context={'request': request})
    return Response({
        'count': total,     # total matching records (for pagination UI)
        'page': page,
        'page_size': page_size,
        'results': serializer.data,  # list of HazardListItem objects
    })


def _hazard_create(request):
    serializer = HazardCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    hazard = serializer.save(reporter=request.user)

    # Handle uploaded images (field name: images, max 3)
    images = request.FILES.getlist('images')[:3]
    for img in images:
        HazardImage.objects.create(hazard=hazard, image=img, phase='report')

    logger.info(f"隐患上报: {hazard.title} by {request.user.username}")
    return Response(
        HazardDetailSerializer(hazard, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hazard_detail(request, pk):
    try:
        hazard = HazardReport.objects.select_related(
            'location', 'reporter', 'assignee', 'assigned_by', 'verified_by'
        ).prefetch_related('images').get(pk=pk)
    except HazardReport.DoesNotExist:
        return Response({'error': '隐患不存在'}, status=404)

    return Response(HazardDetailSerializer(hazard, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsSafetyOfficer])
def hazard_assign(request, pk):
    """安全员分派整改责任人"""
    try:
        hazard = HazardReport.objects.get(pk=pk)
    except HazardReport.DoesNotExist:
        return Response({'error': '隐患不存在'}, status=404)

    if hazard.status != 'pending':
        return Response({'error': '只有待分派状态的隐患可以分派'}, status=400)

    assignee_id = request.data.get('assignee_id')
    if not assignee_id:
        return Response({'error': '请选择整改责任人'}, status=400)

    from django.contrib.auth.models import User
    try:
        assignee = User.objects.get(pk=assignee_id)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=400)

    hazard.assignee = assignee
    hazard.assigned_by = request.user
    hazard.assigned_at = timezone.now()
    hazard.status = 'fixing'
    hazard.save()

    logger.info(f"隐患分派: {hazard.title} -> {assignee.username}")
    return Response(HazardDetailSerializer(hazard, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def hazard_fix(request, pk):
    """整改责任人提交整改"""
    try:
        hazard = HazardReport.objects.get(pk=pk)
    except HazardReport.DoesNotExist:
        return Response({'error': '隐患不存在'}, status=404)

    if hazard.status not in ('fixing', 'rejected'):
        return Response({'error': '只有整改中或驳回状态的隐患可以提交整改'}, status=400)

    if hazard.assignee != request.user:
        return Response({'error': '只有整改责任人可以提交整改'}, status=403)

    fix_description = request.data.get('fix_description', '').strip()
    if not fix_description:
        return Response({'error': '请填写整改说明'}, status=400)

    hazard.fix_description = fix_description
    hazard.fixed_at = timezone.now()
    hazard.status = 'verifying'
    hazard.save()

    # Optional fix images
    images = request.FILES.getlist('images')[:3]
    for img in images:
        HazardImage.objects.create(hazard=hazard, image=img, phase='fix')

    logger.info(f"隐患整改提交: {hazard.title} by {request.user.username}")
    return Response(HazardDetailSerializer(hazard, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsSafetyOfficer])
def hazard_verify(request, pk):
    """安全员验证整改结果"""
    try:
        hazard = HazardReport.objects.get(pk=pk)
    except HazardReport.DoesNotExist:
        return Response({'error': '隐患不存在'}, status=404)

    if hazard.status != 'verifying':
        return Response({'error': '只有待验证状态的隐患可以验证'}, status=400)

    action = request.data.get('action')
    remark = request.data.get('remark', '')

    if action == 'approve':
        hazard.status = 'closed'
    elif action == 'reject':
        hazard.status = 'rejected'  # UI shows red badge; assignee must re-fix from this state
    else:
        return Response({'error': 'action 必须为 approve 或 reject'}, status=400)

    hazard.verified_by = request.user
    hazard.verified_at = timezone.now()
    hazard.verify_remark = remark
    hazard.save()

    logger.info(f"隐患验证: {hazard.title} -> {action} by {request.user.username}")
    return Response(HazardDetailSerializer(hazard, context={'request': request}).data)
```

- [ ] **Step 2: Update safety URLs**

Replace `backend/apps/safety/urls.py` with:

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
]
```

- [ ] **Step 3: Verify the backend starts and endpoints are accessible**

```bash
cd backend
python manage.py check
python manage.py runserver
```

Test locations endpoint (should require login first):
```bash
curl -s http://localhost:8000/api/safety/locations/
```
Expected: `{"detail":"Authentication credentials were not provided."}`

Login and test:
```bash
# Login
curl -s -c cookies.txt -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"worker1","password":"worker123"}'

# Get CSRF token from cookies.txt, then test locations
curl -s -b cookies.txt http://localhost:8000/api/safety/locations/
```
Expected: JSON array with 9 location objects.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/safety/views.py backend/apps/safety/urls.py
git commit -m "feat: add hazard CRUD API endpoints (list, detail, assign, fix, verify)"
```

---

## Chunk 3: Frontend Foundation

### Task 8: Add User Store & Update http.ts

**Files:**
- Create: `frontend/src/stores/user.ts`
- Modify: `frontend/src/api/http.ts`

- [ ] **Step 1: Create user Pinia store**

Create `frontend/src/stores/user.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: 'worker' | 'team_leader' | 'safety_officer'
}

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => user.value !== null)
  const isSafetyOfficer = computed(() => user.value?.role === 'safety_officer')
  const isTeamLeader = computed(() => user.value?.role === 'team_leader')

  function setUser(u: UserInfo) {
    user.value = u
  }

  function clearUser() {
    user.value = null
  }

  return { user, isLoggedIn, isSafetyOfficer, isTeamLeader, setUser, clearUser }
}, {
  persist: false,  // Don't persist — always verify with server on page load
})
```

- [ ] **Step 2: Update http.ts for CSRF and 401 handling**

Replace `frontend/src/api/http.ts` with:

```typescript
import axios from 'axios'
import { ElMessage } from 'element-plus'

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? match[1] : ''
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000',
  timeout: 15000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use((config) => {
  const csrf = getCsrfToken()
  if (csrf) {
    config.headers['X-CSRFToken'] = csrf
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear the user store on any 401.
      import('@/stores/user').then(({ useUserStore }) => {
        useUserStore().clearUser()
      })
      // Redirect to login, but:
      //   1. Don't redirect if already on /login (avoids redirect loops).
      //   2. Don't redirect if this 401 came from the router guard's me() probe
      //      (the guard returns '/login' itself and handles that path).
      import('@/router').then(({ default: router }) => {
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
      })
      // Re-throw without showing a generic error message.
      // LoginView handles its own error message for login failures.
      // Other views will be redirected before they can act on this error.
      return Promise.reject(error)
    }
    const msg = error.response?.data?.detail || error.response?.data?.error || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default http
```

- [ ] **Step 3: Create users API module**

Create `frontend/src/api/users.ts`:

```typescript
import http from './http'
import type { UserInfo } from '@/stores/user'

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
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/user.ts frontend/src/api/http.ts frontend/src/api/users.ts
git commit -m "feat: add user store, CSRF-aware http client, users API"
```

---

### Task 9: Create Login View & Route Guards

**Files:**
- Create: `frontend/src/views/login/LoginView.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Create login view**

Create `frontend/src/views/login/LoginView.vue`:

```vue
<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-icon">ZS</div>
        <div class="brand-text">
          <div class="brand-title">制丝车间</div>
          <div class="brand-sub">智能管理系统</div>
        </div>
      </div>

      <h2 class="login-heading">登录</h2>

      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            autocomplete="username"
            :disabled="loading"
          >
            <template #prefix>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="7" cy="5" r="3"/>
                <path d="M1 13c0-3.3 2.7-6 6-6s6 2.7 6 6"/>
              </svg>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            autocomplete="current-password"
            show-password
            :disabled="loading"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="6" width="10" height="7" rx="1.5"/>
                <path d="M4.5 6V4a2.5 2.5 0 015 0v2"/>
              </svg>
            </template>
          </el-input>
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width: 100%; margin-top: 8px"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usersApi } from '@/api/users'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await usersApi.login(form.username.trim(), form.password)
    userStore.setUser(data)
    router.push('/dashboard')
  } catch (err: any) {
    // The http interceptor does NOT show an ElMessage for 401 (to avoid
    // polluting session-expiry redirects). We show the login error ourselves.
    const msg = err.response?.data?.error || '用户名或密码错误'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: var(--bg-root);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: 360px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 40px 36px;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.brand-icon {
  width: 40px;
  height: 40px;
  background: var(--color-accent);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.9rem;
  color: #fff;
  letter-spacing: 1px;
}

.brand-title {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.brand-sub {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.login-heading {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 24px;
}
</style>
```

- [ ] **Step 2: Update router with login route and navigation guards**

Replace `frontend/src/router/index.ts` with:

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login/LoginView.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/dashboard/DashboardView.vue'),
          meta: { title: '系统总览' },
        },
        {
          path: 'equipment',
          name: 'EquipmentList',
          component: () => import('@/views/equipment/EquipmentListView.vue'),
          meta: { title: '设备管理' },
        },
        {
          path: 'equipment/new',
          name: 'EquipmentNew',
          component: () => import('@/views/equipment/EquipmentFormView.vue'),
          meta: { title: '新增设备' },
        },
        {
          path: 'equipment/:id',
          name: 'EquipmentDetail',
          component: () => import('@/views/equipment/EquipmentDetailView.vue'),
          meta: { title: '设备详情' },
        },
        {
          path: 'equipment/:id/edit',
          name: 'EquipmentEdit',
          component: () => import('@/views/equipment/EquipmentFormView.vue'),
          meta: { title: '编辑设备' },
        },
        {
          path: 'monitoring',
          name: 'Monitoring',
          component: () => import('@/views/monitoring/MonitoringView.vue'),
          meta: { title: '实时监控' },
        },
        {
          path: 'monitoring/alarms',
          name: 'AlarmHistory',
          component: () => import('@/views/monitoring/AlarmHistoryView.vue'),
          meta: { title: '报警历史' },
        },
        {
          path: 'ai/repair/:alarmId',
          name: 'RepairAdvice',
          component: () => import('@/views/ai/RepairAdviceView.vue'),
          meta: { title: 'AI维修建议' },
        },
        {
          path: 'quality',
          name: 'Quality',
          component: () => import('@/views/quality/QualityView.vue'),
          meta: { title: '质量管理' },
        },
        {
          path: 'quality/knowledge',
          name: 'QualityKnowledge',
          component: () => import('@/views/quality/QualityKnowledgeView.vue'),
          meta: { title: '质量知识库' },
        },
        {
          path: 'safety',
          name: 'Safety',
          component: () => import('@/views/safety/SafetyView.vue'),
          meta: { title: '安全管理' },
        },
        {
          path: 'safety/knowledge',
          name: 'SafetyKnowledge',
          component: () => import('@/views/safety/SafetyKnowledgeView.vue'),
          meta: { title: '安全知识库' },
        },
        {
          path: 'safety/hazard',
          name: 'HazardList',
          component: () => import('@/views/safety/HazardListView.vue'),
          meta: { title: '随手拍' },
        },
        {
          path: 'safety/hazard/report',
          name: 'HazardReport',
          component: () => import('@/views/safety/HazardReportView.vue'),
          meta: { title: '上报隐患' },
        },
        {
          path: 'safety/hazard/:id',
          name: 'HazardDetail',
          component: () => import('@/views/safety/HazardDetailView.vue'),
          meta: { title: '隐患详情' },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  document.title = `${to.meta.title || ''} - 制丝车间智能管理系统`

  if (to.meta.public) return true

  // Check login state from store
  const { useUserStore } = await import('@/stores/user')
  const userStore = useUserStore()

  if (!userStore.isLoggedIn) {
    // Try to restore session from server (page refresh scenario).
    // me() may return 401 — the http interceptor clears the store but
    // does NOT push to /login (to avoid double navigation). We return
    // '/login' here as the authoritative redirect.
    try {
      const { usersApi } = await import('@/api/users')
      const { data } = await usersApi.me()
      userStore.setUser(data)
    } catch {
      // 401 or network error — user is not authenticated
      return '/login'
    }
  }

  return true
})

export default router
```

- [ ] **Step 3: Verify login page renders**

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173/login`. Should show the login form with dark theme.

Test login with `worker1 / worker123`. Should redirect to dashboard.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/login/ frontend/src/router/index.ts
git commit -m "feat: add login view and authentication route guards"
```

---

### Task 10: Add Safety Hazard API Module

**Files:**
- Create: `frontend/src/api/safety.ts`

- [ ] **Step 1: Create safety API module**

Create `frontend/src/api/safety.ts`:

```typescript
import http from './http'

export interface Location {
  id: number
  name: string
  sort_order: number
}

export interface UserBrief {
  id: number
  username: string
  display_name: string
}

export interface HazardImage {
  id: number
  image_url: string
  phase: 'report' | 'fix'
  created_at: string
}

export interface HazardListItem {
  id: number
  title: string
  level: 'general' | 'major'
  level_display: string
  location: number
  location_name: string
  location_detail: string
  status: 'pending' | 'fixing' | 'verifying' | 'closed' | 'rejected'
  status_display: string
  reporter: UserBrief
  assignee: UserBrief | null
  created_at: string
}

export interface HazardDetail extends HazardListItem {
  description: string
  assigned_by: UserBrief | null
  assigned_at: string | null
  fix_description: string
  fixed_at: string | null
  verified_by: UserBrief | null
  verified_at: string | null
  verify_remark: string
  updated_at: string
  images: HazardImage[]
}

export interface HazardListResponse {
  count: number
  page: number
  page_size: number
  results: HazardListItem[]
}

export interface HazardFilters {
  status?: string
  level?: string
  location?: number
  reporter?: number
  date_from?: string
  date_to?: string
  search?: string
  page?: number
  page_size?: number
}

export const safetyApi = {
  // Locations
  getLocations() {
    return http.get<Location[]>('/api/safety/locations/')
  },

  // Hazards
  listHazards(filters: HazardFilters = {}) {
    return http.get<HazardListResponse>('/api/safety/hazards/', { params: filters })
  },

  getHazard(id: number) {
    return http.get<HazardDetail>(`/api/safety/hazards/${id}/`)
  },

  createHazard(formData: FormData) {
    // Must NOT set Content-Type header manually — axios auto-sets
    // multipart/form-data with the correct boundary when given FormData.
    // The default 'application/json' header is overridden by passing undefined.
    return http.post<HazardDetail>('/api/safety/hazards/', formData, {
      headers: { 'Content-Type': undefined },
    })
  },

  assignHazard(id: number, assigneeId: number) {
    return http.post<HazardDetail>(`/api/safety/hazards/${id}/assign/`, { assignee_id: assigneeId })
  },

  fixHazard(id: number, data: FormData) {
    // Same as createHazard — let axios set multipart/form-data boundary automatically.
    return http.post<HazardDetail>(`/api/safety/hazards/${id}/fix/`, data, {
      headers: { 'Content-Type': undefined },
    })
  },

  verifyHazard(id: number, action: 'approve' | 'reject', remark?: string) {
    return http.post<HazardDetail>(`/api/safety/hazards/${id}/verify/`, { action, remark })
  },
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/safety.ts
git commit -m "feat: add safety API module with hazard and location endpoints"
```

---

## Chunk 4: Frontend Hazard Pages

### Task 11: Hazard Report (Upload) View

**Files:**
- Create: `frontend/src/views/safety/HazardReportView.vue`

- [ ] **Step 1: Create the report view**

Create `frontend/src/views/safety/HazardReportView.vue`:

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">上报隐患</h2>
        <p class="page-subtitle">拍照或上传图片记录安全隐患</p>
      </div>
    </div>

    <div class="form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">

        <el-form-item label="隐患标题" prop="title">
          <el-input v-model="form.title" placeholder="简要描述隐患内容" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="详细描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="详细描述隐患的具体情况"
          />
        </el-form-item>

        <div class="form-row">
          <el-form-item label="隐患等级" prop="level" class="form-col">
            <el-radio-group v-model="form.level">
              <el-radio-button value="general">一般隐患</el-radio-button>
              <el-radio-button value="major">
                <span style="color: var(--color-alarm)">重大隐患</span>
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="所在区域" prop="location" class="form-col">
            <el-select v-model="form.location" placeholder="选择区域" style="width: 100%">
              <el-option
                v-for="loc in locations"
                :key="loc.id"
                :label="loc.name"
                :value="loc.id"
              />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="具体位置（补充）">
          <el-input v-model="form.location_detail" placeholder="如：3号烘丝机东侧" maxlength="200" />
        </el-form-item>

        <el-form-item label="现场照片（最多3张）">
          <div class="image-upload-area">
            <div v-for="(preview, idx) in previews" :key="idx" class="image-preview">
              <img :src="preview" alt="预览" />
              <button class="remove-btn" @click="removeImage(idx)">✕</button>
            </div>
            <label v-if="previews.length < 3" class="upload-trigger">
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                multiple
                capture="environment"
                style="display: none"
                @change="handleFileChange"
              />
              <div class="upload-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
              </div>
              <span>拍照 / 上传</span>
            </label>
          </div>
        </el-form-item>

        <div class="form-actions">
          <el-button @click="router.back()">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">提交上报</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { safetyApi } from '@/api/safety'
import type { Location } from '@/api/safety'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const locations = ref<Location[]>([])
const files = ref<File[]>([])
const previews = ref<string[]>([])

const form = reactive({
  title: '',
  description: '',
  level: 'general',
  location: null as number | null,
  location_detail: '',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入隐患标题', trigger: 'blur' }],
  description: [{ required: true, message: '请输入详细描述', trigger: 'blur' }],
  level: [{ required: true }],
  location: [{ required: true, message: '请选择所在区域', trigger: 'change' }],
}

onMounted(async () => {
  try {
    const { data } = await safetyApi.getLocations()
    locations.value = data
  } catch {
    ElMessage.error('加载区域列表失败')
  }
})

function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const newFiles = Array.from(input.files)
  const remaining = 3 - files.value.length
  const toAdd = newFiles.slice(0, remaining)
  toAdd.forEach((f) => {
    files.value.push(f)
    previews.value.push(URL.createObjectURL(f))
  })
  input.value = ''
}

function removeImage(idx: number) {
  URL.revokeObjectURL(previews.value[idx])
  files.value.splice(idx, 1)
  previews.value.splice(idx, 1)
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.title)
    fd.append('description', form.description)
    fd.append('level', form.level)
    fd.append('location', String(form.location))
    fd.append('location_detail', form.location_detail)
    files.value.forEach((f) => fd.append('images', f))

    await safetyApi.createHazard(fd)
    ElMessage.success('隐患上报成功')
    router.push('/safety/hazard')
  } catch {
    // Error shown by interceptor
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 28px 32px;
  max-width: 760px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-col { margin-bottom: 0; }

.image-upload-area {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.image-preview {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border-default);
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0,0,0,0.6);
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 0.65rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-trigger {
  width: 100px;
  height: 100px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 0.75rem;
  transition: border-color var(--transition-fast);
}

.upload-trigger:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
  padding-top: 20px;
  border-top: 1px solid var(--border-subtle);
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/safety/HazardReportView.vue
git commit -m "feat: add hazard report upload view"
```

---

### Task 12: Hazard List View

**Files:**
- Create: `frontend/src/views/safety/HazardListView.vue`

- [ ] **Step 1: Create the list view**

Create `frontend/src/views/safety/HazardListView.vue`:

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">随手拍 · 找隐患</h2>
        <p class="page-subtitle">安全隐患上报与处理跟踪</p>
      </div>
      <el-button type="primary" @click="router.push('/safety/hazard/report')">
        + 上报隐患
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-card">
      <div class="filter-row">
        <el-input
          v-model="filters.search"
          placeholder="搜索标题/描述"
          clearable
          style="width: 220px"
          @keyup.enter="fetchList"
          @clear="fetchList"
        />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px" @change="fetchList">
          <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.level" placeholder="等级" clearable style="width: 120px" @change="fetchList">
          <el-option label="一般隐患" value="general" />
          <el-option label="重大隐患" value="major" />
        </el-select>
        <el-select v-model="filters.location" placeholder="区域" clearable style="width: 130px" @change="fetchList">
          <el-option v-for="loc in locations" :key="loc.id" :label="loc.name" :value="loc.id" />
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
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table
        :data="hazards"
        v-loading="loading"
        row-class-name="table-row-hover"
        @row-click="(row) => router.push(`/safety/hazard/${row.id}`)"
        style="width: 100%"
      >
        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">
            <span class="hazard-title">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="row.level === 'major' ? 'danger' : 'info'" size="small">
              {{ row.level_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="区域" width="110" prop="location_name" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-tag" :class="`status-${row.status}`">
              {{ row.status_display }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="上报人" width="100">
          <template #default="{ row }">{{ row.reporter.display_name }}</template>
        </el-table-column>
        <el-table-column label="整改人" width="100">
          <template #default="{ row }">{{ row.assignee?.display_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="上报时间" width="160" prop="created_at" />
      </el-table>

      <div class="pagination-row">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchList"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { safetyApi } from '@/api/safety'
import type { HazardListItem, Location } from '@/api/safety'

const router = useRouter()
const loading = ref(false)
const hazards = ref<HazardListItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const locations = ref<Location[]>([])
const dateRange = ref<[string, string] | null>(null)

const filters = reactive({
  search: '',
  status: '',
  level: '',
  location: null as number | null,
  date_from: '',
  date_to: '',
})

const STATUS_OPTIONS = [
  { value: 'pending', label: '待分派' },
  { value: 'fixing', label: '整改中' },
  { value: 'verifying', label: '待验证' },
  { value: 'closed', label: '已关闭' },
  { value: 'rejected', label: '驳回' },
]

onMounted(async () => {
  const [, locs] = await Promise.allSettled([
    fetchList(),
    safetyApi.getLocations(),
  ])
  if (locs.status === 'fulfilled') locations.value = locs.value.data
})

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize,
    }
    if (filters.search) params.search = filters.search
    if (filters.status) params.status = filters.status
    if (filters.level) params.level = filters.level
    if (filters.location) params.location = filters.location
    if (filters.date_from) params.date_from = filters.date_from
    if (filters.date_to) params.date_to = filters.date_to

    const { data } = await safetyApi.listHazards(params)
    hazards.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function onDateChange(val: [string, string] | null) {
  filters.date_from = val?.[0] || ''
  filters.date_to = val?.[1] || ''
  fetchList()
}

function resetFilters() {
  Object.assign(filters, { search: '', status: '', level: '', location: null, date_from: '', date_to: '' })
  dateRange.value = null
  currentPage.value = 1
  fetchList()
}
</script>

<style scoped>
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
  padding: 0;
  overflow: hidden;
}

.hazard-title {
  font-weight: 500;
  color: var(--text-primary);
}

.status-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}

.status-pending  { background: var(--color-info-dim); color: var(--color-accent); }
.status-fixing   { background: var(--color-warning-dim); color: var(--color-warning); }
.status-verifying { background: rgba(160, 100, 255, 0.15); color: #a064ff; }
.status-closed   { background: var(--color-healthy-dim); color: var(--color-healthy); }
.status-rejected { background: var(--color-alarm-dim); color: var(--color-alarm); }

.pagination-row {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid var(--border-subtle);
}

:deep(.table-row-hover) {
  cursor: pointer;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/safety/HazardListView.vue
git commit -m "feat: add hazard list view with filters and pagination"
```

---

### Task 13: Hazard Detail View

**Files:**
- Create: `frontend/src/views/safety/HazardDetailView.vue`

- [ ] **Step 1: Create the detail view**

Create `frontend/src/views/safety/HazardDetailView.vue`:

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <el-button text @click="router.back()">
        ← 返回列表
      </el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="6" animated />
    </div>

    <template v-else-if="hazard">
      <!-- 基本信息 -->
      <div class="info-card">
        <div class="info-header">
          <div class="info-title-row">
            <el-tag :type="hazard.level === 'major' ? 'danger' : 'info'" size="large">
              {{ hazard.level_display }}
            </el-tag>
            <h2 class="hazard-title">{{ hazard.title }}</h2>
            <span class="status-tag" :class="`status-${hazard.status}`">
              {{ hazard.status_display }}
            </span>
          </div>
          <p class="hazard-desc">{{ hazard.description }}</p>
        </div>
        <div class="info-meta-grid">
          <div class="meta-item"><span class="meta-label">区域</span><span>{{ hazard.location_name }}</span></div>
          <div v-if="hazard.location_detail" class="meta-item"><span class="meta-label">具体位置</span><span>{{ hazard.location_detail }}</span></div>
          <div class="meta-item"><span class="meta-label">上报人</span><span>{{ hazard.reporter.display_name }}</span></div>
          <div class="meta-item"><span class="meta-label">上报时间</span><span>{{ hazard.created_at }}</span></div>
          <div v-if="hazard.assignee" class="meta-item"><span class="meta-label">整改责任人</span><span>{{ hazard.assignee.display_name }}</span></div>
        </div>
      </div>

      <!-- 上报图片 -->
      <div v-if="reportImages.length" class="section-card">
        <h3 class="section-title">现场照片</h3>
        <div class="image-grid">
          <img
            v-for="img in reportImages"
            :key="img.id"
            :src="img.image_url"
            class="hazard-image"
            @click="previewImage(img.image_url)"
          />
        </div>
      </div>

      <!-- 流转时间线 -->
      <div class="section-card">
        <h3 class="section-title">处理进展</h3>
        <el-timeline>
          <el-timeline-item
            :timestamp="hazard.created_at"
            placement="top"
            type="primary"
          >
            <div class="timeline-content">
              <span class="tl-action">隐患上报</span>
              <span class="tl-actor">{{ hazard.reporter.display_name }}</span>
            </div>
          </el-timeline-item>
          <el-timeline-item
            v-if="hazard.assigned_at"
            :timestamp="hazard.assigned_at"
            placement="top"
            type="warning"
          >
            <div class="timeline-content">
              <span class="tl-action">分派整改</span>
              <span class="tl-actor">{{ hazard.assigned_by?.display_name }} → {{ hazard.assignee?.display_name }}</span>
            </div>
          </el-timeline-item>
          <el-timeline-item
            v-if="hazard.fixed_at"
            :timestamp="hazard.fixed_at"
            placement="top"
            type="warning"
          >
            <div class="timeline-content">
              <span class="tl-action">提交整改</span>
              <span class="tl-actor">{{ hazard.assignee?.display_name }}</span>
              <p class="tl-remark">{{ hazard.fix_description }}</p>
            </div>
          </el-timeline-item>
          <el-timeline-item
            v-if="hazard.verified_at"
            :timestamp="hazard.verified_at"
            placement="top"
            :type="hazard.status === 'closed' ? 'success' : 'danger'"
          >
            <div class="timeline-content">
              <span class="tl-action">{{ hazard.status === 'closed' ? '验证通过' : '驳回整改' }}</span>
              <span class="tl-actor">{{ hazard.verified_by?.display_name }}</span>
              <p v-if="hazard.verify_remark" class="tl-remark">{{ hazard.verify_remark }}</p>
            </div>
          </el-timeline-item>
          <!-- Re-fix after rejection: fixed_at will update when assignee re-submits -->
          <el-timeline-item
            v-if="hazard.status === 'rejected'"
            timestamp="待整改"
            placement="top"
            type="danger"
          >
            <div class="timeline-content">
              <span class="tl-action">已驳回，等待责任人重新整改</span>
              <span class="tl-actor">{{ hazard.assignee?.display_name }}</span>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>

      <!-- 整改图片 -->
      <div v-if="fixImages.length" class="section-card">
        <h3 class="section-title">整改照片</h3>
        <div class="image-grid">
          <img
            v-for="img in fixImages"
            :key="img.id"
            :src="img.image_url"
            class="hazard-image"
            @click="previewImage(img.image_url)"
          />
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-bar" v-if="showActionBar">
        <!-- 安全员分派 -->
        <el-button
          v-if="isSafetyOfficer && hazard.status === 'pending'"
          type="primary"
          @click="showAssignDialog = true"
        >
          分派责任人
        </el-button>

        <!-- 整改责任人提交整改（fixing 或 rejected 状态均可）
             NOTE: 'rejected' IS a distinct persistent status per STATUS_CHOICES.
             The flow is: verifying → rejected (via verify/reject action),
             then rejected → fixing (when assignee re-submits via hazard_fix).
             The assignee must be able to act from the 'rejected' state. -->
        <el-button
          v-if="isAssignee && (hazard.status === 'fixing' || hazard.status === 'rejected')"
          type="warning"
          @click="showFixDialog = true"
        >
          提交整改
        </el-button>

        <!-- 安全员验证 -->
        <template v-if="isSafetyOfficer && hazard.status === 'verifying'">
          <el-button type="success" @click="handleVerify('approve')">验证通过</el-button>
          <el-button type="danger" @click="showRejectDialog = true">驳回整改</el-button>
        </template>
      </div>
    </template>

    <!-- 分派弹窗 -->
    <el-dialog v-model="showAssignDialog" title="分派整改责任人" width="400px">
      <el-select v-model="assigneeId" placeholder="选择责任人" style="width: 100%">
        <el-option
          v-for="u in teamLeaders"
          :key="u.id"
          :label="u.display_name"
          :value="u.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="showAssignDialog = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="handleAssign">确认分派</el-button>
      </template>
    </el-dialog>

    <!-- 整改弹窗 -->
    <el-dialog v-model="showFixDialog" title="提交整改" width="500px">
      <el-input
        v-model="fixDescription"
        type="textarea"
        :rows="4"
        placeholder="描述整改措施和结果"
      />
      <div class="fix-image-upload" style="margin-top: 12px;">
        <label class="upload-btn">
          <input type="file" accept="image/*" multiple style="display:none" @change="handleFixImages" />
          上传整改照片（可选，最多3张）
        </label>
        <div class="fix-previews">
          <img v-for="(p, i) in fixPreviews" :key="i" :src="p" class="fix-thumb" />
        </div>
      </div>
      <template #footer>
        <el-button @click="showFixDialog = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="handleFix">提交整改</el-button>
      </template>
    </el-dialog>

    <!-- 驳回弹窗 -->
    <el-dialog v-model="showRejectDialog" title="驳回整改" width="400px">
      <el-input v-model="rejectRemark" type="textarea" :rows="3" placeholder="填写驳回原因（可选）" />
      <template #footer>
        <el-button @click="showRejectDialog = false">取消</el-button>
        <el-button type="danger" :loading="actionLoading" @click="handleVerify('reject')">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 图片预览 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="[previewUrl]"
      @close="previewVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { safetyApi } from '@/api/safety'
import { usersApi } from '@/api/users'
import { useUserStore } from '@/stores/user'
import type { HazardDetail } from '@/api/safety'
import type { UserInfo } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const hazard = ref<HazardDetail | null>(null)
const loading = ref(true)
const teamLeaders = ref<UserInfo[]>([])

// Action state
const showAssignDialog = ref(false)
const showFixDialog = ref(false)
const showRejectDialog = ref(false)
const actionLoading = ref(false)
const assigneeId = ref<number | null>(null)
const fixDescription = ref('')
const fixFiles = ref<File[]>([])
const fixPreviews = ref<string[]>([])
const rejectRemark = ref('')

// Image preview
const previewVisible = ref(false)
const previewUrl = ref('')

const isSafetyOfficer = computed(() => userStore.isSafetyOfficer)
const isAssignee = computed(() =>
  hazard.value?.assignee?.id === userStore.user?.id
)
const showActionBar = computed(() =>
  (isSafetyOfficer.value && ['pending', 'verifying'].includes(hazard.value?.status || '')) ||
  (isAssignee.value && ['fixing', 'rejected'].includes(hazard.value?.status || ''))
)

const reportImages = computed(() => hazard.value?.images.filter(i => i.phase === 'report') || [])
const fixImages = computed(() => hazard.value?.images.filter(i => i.phase === 'fix') || [])

onMounted(async () => {
  const id = Number(route.params.id)
  try {
    const { data } = await safetyApi.getHazard(id)
    hazard.value = data
  } catch {
    ElMessage.error('加载隐患详情失败')
  } finally {
    loading.value = false
  }

  if (userStore.isSafetyOfficer) {
    try {
      const { data } = await usersApi.list('班组长')
      teamLeaders.value = data
    } catch {}
  }
})

function previewImage(url: string) {
  previewUrl.value = url
  previewVisible.value = true
}

async function handleAssign() {
  if (!assigneeId.value) { ElMessage.warning('请选择责任人'); return }
  actionLoading.value = true
  try {
    const { data } = await safetyApi.assignHazard(hazard.value!.id, assigneeId.value)
    hazard.value = data
    showAssignDialog.value = false
    ElMessage.success('分派成功')
  } finally {
    actionLoading.value = false
  }
}

function handleFixImages(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const newFiles = Array.from(input.files).slice(0, 3)
  fixFiles.value = newFiles
  fixPreviews.value = newFiles.map(f => URL.createObjectURL(f))
}

async function handleFix() {
  if (!fixDescription.value.trim()) { ElMessage.warning('请填写整改说明'); return }
  actionLoading.value = true
  try {
    const fd = new FormData()
    fd.append('fix_description', fixDescription.value.trim())
    fixFiles.value.forEach(f => fd.append('images', f))
    const { data } = await safetyApi.fixHazard(hazard.value!.id, fd)
    hazard.value = data
    showFixDialog.value = false
    ElMessage.success('整改提交成功')
  } finally {
    actionLoading.value = false
  }
}

async function handleVerify(action: 'approve' | 'reject') {
  actionLoading.value = true
  try {
    const remark = action === 'reject' ? rejectRemark.value : undefined
    const { data } = await safetyApi.verifyHazard(hazard.value!.id, action, remark)
    hazard.value = data
    showRejectDialog.value = false
    ElMessage.success(action === 'approve' ? '验证通过' : '已驳回')
  } finally {
    actionLoading.value = false
  }
}
</script>

<style scoped>
.info-card, .section-card, .action-bar {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  margin-bottom: 16px;
}

.info-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.hazard-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
}

.hazard-desc {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.7;
  margin: 0 0 16px;
}

.info-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px 24px;
}

.meta-item {
  display: flex;
  gap: 8px;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.meta-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 16px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.image-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hazard-image {
  width: 120px;
  height: 120px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  cursor: pointer;
  border: 1px solid var(--border-default);
  transition: opacity var(--transition-fast);
}

.hazard-image:hover { opacity: 0.85; }

.timeline-content {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.tl-action {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.tl-actor {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.tl-remark {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 6px 0 0;
  white-space: pre-wrap;
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.status-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 3px;
}

.status-pending   { background: var(--color-info-dim); color: var(--color-accent); }
.status-fixing    { background: var(--color-warning-dim); color: var(--color-warning); }
.status-verifying { background: rgba(160, 100, 255, 0.15); color: #a064ff; }
.status-closed    { background: var(--color-healthy-dim); color: var(--color-healthy); }
.status-rejected  { background: var(--color-alarm-dim); color: var(--color-alarm); }

.upload-btn {
  display: inline-block;
  padding: 6px 14px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.fix-previews { display: flex; gap: 8px; margin-top: 8px; }
.fix-thumb { width: 64px; height: 64px; object-fit: cover; border-radius: 4px; }

.loading-state { padding: 40px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/safety/HazardDetailView.vue
git commit -m "feat: add hazard detail view with timeline and action buttons"
```

---

### Task 14: Update Sidebar Navigation

**Files:**
- Modify: `frontend/src/components/layout/SidebarNav.vue`

- [ ] **Step 1: Read the current sidebar file to understand its exact structure**

Read `frontend/src/components/layout/SidebarNav.vue` in full before making the edit.

The safety section currently has these two sub-items:
```html
<router-link to="/safety" class="nav-sub-item" active-class="active">
  ...安全概览
</router-link>
<router-link to="/safety/knowledge" class="nav-sub-item" active-class="active">
  ...安全知识库
</router-link>
```

Add the 随手拍 sub-item between 安全概览 and 安全知识库:

```html
<router-link to="/safety/hazard" class="nav-sub-item" active-class="active">
  <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M10.5 8.5a2 2 0 01-2 2h-5a2 2 0 01-2-2V5a2 2 0 012-2h1l1-1.5h3L9.5 3h1a2 2 0 012 2v3.5z"/>
    <circle cx="6.5" cy="6.5" r="1.8"/>
  </svg>
  随手拍
</router-link>
```

> **Note on `isSafetyGroupActive`:** Do NOT change this computed. The existing implementation already uses `route.path.startsWith('/safety')` which naturally covers `/safety/hazard` and all sub-routes. No update needed.

- [ ] **Step 2: Verify sidebar renders correctly**

Open the frontend in browser, navigate to `/safety`. Confirm the sidebar shows three sub-items under 安全管理: 安全概览, 随手拍, 安全知识库.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/SidebarNav.vue
git commit -m "feat: add 随手拍 sub-menu item to safety navigation"
```

---

### Task 15: End-to-End Verification

- [ ] **Step 1: Start both servers**

```bash
# Terminal 1 - Backend
cd backend
daphne -b 127.0.0.1 -p 8000 config.asgi:application

# Terminal 2 - Frontend
cd frontend
npm run dev
```

- [ ] **Step 2: Test full workflow**

1. Open `http://localhost:5173` → should redirect to `/login`
2. Login as `worker1 / worker123` → should go to dashboard
3. Navigate to 安全管理 → 随手拍 → should see empty list with 「上报隐患」 button
4. Click 「上报隐患」, fill form, upload a photo, submit → should appear in list with status 「待分派」
5. Logout, login as `admin / admin123` (安全员)
6. Open the hazard, click 「分派责任人」, select `leader1`, confirm → status changes to 「整改中」
7. Logout, login as `leader1 / leader123`
8. Open the hazard, click 「提交整改」, fill description, submit → status changes to 「待验证」
9. Logout, login as `admin / admin123`
10. Open the hazard, click 「验证通过」 → status changes to 「已关闭」

- [ ] **Step 3: Test filter functionality**

On the list page, test each filter: status, level, location, date range, search keyword. Confirm results filter correctly.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete 随手拍找隐患 feature implementation"
```

---

## Summary

| Chunk | Tasks | What it produces |
|-------|-------|-----------------|
| 1 — Backend Foundation | 1–4 | Settings, users app, safety models, seed data |
| 2 — Backend API | 5–7 | Serializers, permissions, all API endpoints |
| 3 — Frontend Foundation | 8–10 | User store, http.ts CSRF, login view, route guards, safety API |
| 4 — Frontend Pages | 11–15 | Report, list, detail views + sidebar update + E2E test |
