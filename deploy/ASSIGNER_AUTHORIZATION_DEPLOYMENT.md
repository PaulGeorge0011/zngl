# 整改分派人授权功能部署指南

## 📋 功能概述

系统管理员可以将"分派人"角色授予其他用户，使被授权的用户也能够分派整改任务。授权界面集成在整改中心页面中，无需单独的管理页面。

### 核心特性
- ✅ 单一权限：只需"分派人"角色，简单明确
- ✅ UI 集成：授权界面在整改中心内，操作便捷
- ✅ 三级权限：超级用户/安全员 > 整改分派人 > 验证人
- ✅ 不影响其他模块：只修改整改中心相关代码

---

## 📦 部署文件清单

### 后端文件（4 个）

#### 新增文件（1 个）
```
zngl/backend/apps/safety/management/commands/
└── init_rectification_groups.py                # Group 初始化脚本（40 行）
```

#### 修改文件（3 个）
```
zngl/backend/apps/safety/
├── rectification_views.py                      # 权限检查 + API 视图（+130 行）
│   ├── 第 29-58 行：权限检查函数（修改 + 新增）
│   └── 第 439-548 行：4 个 API 端点（新增）
├── urls.py                                     # API 路由（+4 行）
│   └── 第 79-83 行：分派人管理路由
└── __init__.py                                 # 确保 management 目录被识别
```

### 前端文件（2 个）

#### 新增文件（1 个）
```
zngl/frontend/src/components/safety/
└── AssignerManagementDialog.vue                # 分派人管理对话框（220 行）
```

#### 修改文件（1 个）
```
zngl/frontend/src/views/safety/
└── RectificationCenterView.vue                 # 集成管理按钮（+10 行）
```

---

## 🚀 部署步骤

### 1. 后端部署

#### 1.1 上传文件到服务器
```bash
# 上传新增文件
scp E:/zngl-master/zngl/backend/apps/safety/management/commands/init_rectification_groups.py \
    root@172.24.69.125:/opt/zs2/backend/apps/safety/management/commands/

# 上传修改文件
scp E:/zngl-master/zngl/backend/apps/safety/rectification_views.py \
    E:/zngl-master/zngl/backend/apps/safety/urls.py \
    root@172.24.69.125:/opt/zs2/backend/apps/safety/
```

#### 1.2 初始化用户组
```bash
ssh root@172.24.69.125
cd /opt/zs2/backend
source venv/bin/activate  # 如果使用虚拟环境
python manage.py init_rectification_groups
```

**预期输出**：
```
成功创建用户组: 整改分派人
用户组已存在: 安全员

整改中心用户组初始化完成！
```

#### 1.3 重启服务
```bash
systemctl restart zs2
```

#### 1.4 验证后端
```bash
# 检查服务状态
systemctl status zs2

# 测试 API 端点（需要安全员权限）
curl -X GET http://localhost:9527/api/safety/rectifications/assigners/ \
  -H "Authorization: Bearer <token>"
```

### 2. 前端部署

#### 2.1 本地构建
```powershell
cd E:\zngl-master\zngl\frontend

# 构建生产版本
npm run build
```

#### 2.2 上传构建产物
```bash
scp -r dist/* root@172.24.69.125:/opt/zs2/frontend/dist/
```

#### 2.3 验证前端
访问整改中心页面，安全员应该能看到"分派人管理"按钮。

---

## ✅ 功能验证清单

### 后端验证
- [ ] 服务正常启动，无错误日志
- [ ] 用户组初始化成功
- [ ] API 端点可访问：
  - [ ] `GET /api/safety/rectifications/assigners/` - 分派人列表
  - [ ] `POST /api/safety/rectifications/assigners/grant/` - 授予权限
  - [ ] `POST /api/safety/rectifications/assigners/revoke/` - 撤销权限
  - [ ] `GET /api/safety/rectifications/assigners/candidates/` - 候选用户

### 前端验证
- [ ] 整改中心页面正常显示
- [ ] 安全员可以看到"分派人管理"按钮
- [ ] 普通用户看不到"分派人管理"按钮
- [ ] 点击按钮打开对话框
- [ ] 对话框有两个标签页（已授权用户、授予权限）
- [ ] 可以授予权限
- [ ] 可以撤销权限
- [ ] 操作有成功/失败提示

### 权限功能验证

#### 测试场景 1：超级用户
- [ ] 超级用户可以分派所有整改工单
- [ ] 超级用户可以管理分派人

#### 测试场景 2：安全员
- [ ] 安全员可以分派所有整改工单
- [ ] 安全员可以管理分派人
- [ ] 安全员可以验证整改

#### 测试场景 3：授权的分派人
- [ ] 被授权的分派人可以分派整改工单
- [ ] 分派人不能验证整改（除非是指派的验证人）
- [ ] 分派人不能管理其他分派人

#### 测试场景 4：验证人（对象级权限）
- [ ] 被指定为验证人的用户可以分派自己负责的工单
- [ ] 验证人可以验证自己负责的工单

#### 测试场景 5：普通用户
- [ ] 普通用户看不到"分派人管理"按钮
- [ ] 普通用户不能分派整改工单
- [ ] 普通用户只能提交自己负责的整改

#### 测试场景 6：停用用户
- [ ] 停用的用户即使在"整改分派人"组中也无法分派工单
- [ ] 停用的安全员无法管理分派人

---

## 🎯 核心功能说明

### 权限层级
```
1. 超级用户/安全员
   ├─ 可分派所有工单
   ├─ 可验证所有工单
   └─ 可管理分派人

2. 整改分派人（被授权）
   ├─ 可分派所有工单
   └─ 不能验证工单（除非是验证人）

3. 验证人（对象级权限）
   ├─ 可分派自己负责的工单
   └─ 可验证自己负责的工单

4. 普通用户
   └─ 只能提交自己负责的整改
```

### API 端点

#### 1. 查询已授权的分派人
```http
GET /api/safety/rectifications/assigners/
Authorization: Bearer <token>

Response:
{
  "assigners": [
    {
      "id": 123,
      "username": "zhangsan",
      "display_name": "张三"
    }
  ]
}
```

#### 2. 授予分派权限
```http
POST /api/safety/rectifications/assigners/grant/
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": 123
}

Response:
{
  "success": true,
  "message": "已授予 zhangsan 分派权限"
}
```

#### 3. 撤销分派权限
```http
POST /api/safety/rectifications/assigners/revoke/
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": 123
}

Response:
{
  "success": true,
  "message": "已撤销 zhangsan 的分派权限"
}
```

#### 4. 获取候选用户列表
```http
GET /api/safety/rectifications/assigners/candidates/
Authorization: Bearer <token>

Response:
{
  "candidates": [
    {
      "id": 456,
      "username": "lisi",
      "display_name": "李四"
    }
  ]
}
```

---

## 🔧 使用说明

### 管理员操作指南

#### 1. 授予分派权限
1. 以安全员身份登录系统
2. 访问"整改中心"页面
3. 点击页面右上角的"分派人管理"按钮
4. 在弹出的对话框中切换到"授予权限"标签页
5. 从下拉列表中选择要授权的用户
6. 点击"授予权限"按钮
7. 看到成功提示后，用户即可分派整改任务

#### 2. 撤销分派权限
1. 在"分派人管理"对话框中
2. 切换到"已授权用户"标签页
3. 找到要撤销权限的用户
4. 点击该用户行的"撤销"按钮
5. 在确认对话框中点击"确定"
6. 看到成功提示后，用户将无法再分派整改任务

### 分派人操作指南

被授予分派权限的用户可以：
1. 访问整改中心查看所有待分派的工单
2. 点击工单的"分派"按钮
3. 选择整改责任人和期限
4. 提交分派

**注意**：分派人不能验证整改，除非被指定为该工单的验证人。

---

## 🔍 故障排查

### 问题 1：用户组初始化失败
**症状**：运行 `init_rectification_groups` 命令报错

**解决方案**：
```bash
# 检查 Django 环境
python manage.py shell
>>> from django.contrib.auth.models import Group
>>> Group.objects.all()

# 手动创建用户组
>>> Group.objects.create(name='整改分派人')
>>> Group.objects.create(name='安全员')
```

### 问题 2：授权后用户仍无法分派
**症状**：授予权限后，用户在整改中心看不到"分派"按钮

**解决方案**：
1. 确认用户已被添加到"整改分派人"组：
```bash
python manage.py shell
>>> from django.contrib.auth.models import User, Group
>>> user = User.objects.get(username='zhangsan')
>>> group = Group.objects.get(name='整改分派人')
>>> user.groups.filter(id=group.id).exists()
True
```

2. 确认用户状态为激活：
```bash
>>> user.is_active
True
```

3. 清除浏览器缓存并重新登录

### 问题 3：前端按钮不显示
**症状**：安全员看不到"分派人管理"按钮

**解决方案**：
1. 检查浏览器控制台是否有 JavaScript 错误
2. 确认当前用户是安全员：
   - 检查用户是否在"安全员"组中
   - 或者是超级用户
3. 清除浏览器缓存并刷新页面
4. 检查前端文件是否正确部署

### 问题 4：API 返回 403 错误
**症状**：调用分派人管理 API 返回 403 Forbidden

**解决方案**：
- 确认当前用户是超级用户或安全员
- 检查用户的 `is_active` 状态
- 查看服务器日志：`journalctl -u zs2 -f`

---

## 📊 数据库变更

### 新增用户组

| 组名 | 说明 | 权限 |
|------|------|------|
| 整改分派人 | 被授权的分派人 | 可分派所有整改工单 |
| 安全员 | 安全管理员 | 可分派、验证所有工单，可管理分派人 |

**注意**：这些是 Django 内置的 `auth_group` 表中的数据，不需要新增数据库表。

---

## 🔐 安全特性

1. **权限检查严格**：
   - 所有 API 端点都有权限验证
   - 只有超级用户和安全员可以管理分派人
   - 停用用户自动失去权限

2. **输入验证**：
   - `user_id` 类型验证，防止注入
   - 完善的错误处理

3. **审计日志**：
   - 所有授予/撤销操作都记录在服务器日志中
   - 日志格式：`用户 admin 授予 zhangsan 整改分派权限`
   - 日志位置：`journalctl -u zs2 | grep "整改分派"`

4. **数据库优化**：
   - 使用 `select_related` 避免 N+1 查询
   - 安全的 profile 访问，避免 `RelatedObjectDoesNotExist` 异常

---

## 📈 性能优化

1. **数据库查询优化**：
   - 使用 `select_related('profile')` 预加载用户资料
   - 候选用户查询使用 `distinct()` 去重

2. **前端性能**：
   - 对话框按需加载数据
   - 操作成功后只刷新必要的列表

---

## 🎯 后续优化建议

1. **批量操作**：
   - 支持批量授予权限
   - 支持批量撤销权限

2. **权限有效期**：
   - 添加权限过期时间
   - 自动撤销过期权限

3. **权限审计**：
   - 权限变更历史记录
   - 权限使用统计报表

4. **通知功能**：
   - 权限授予时通知用户
   - 权限撤销时通知用户

---

## 📞 技术支持

如遇到问题，请提供以下信息：
1. 错误截图或错误消息
2. 服务器日志：`journalctl -u zs2 -n 100`
3. 浏览器控制台日志
4. 操作步骤复现

---

**部署日期**：2026-04-24  
**版本**：v1.0.0  
**负责人**：开发团队

---

## 📦 附录 A：完整文件路径清单

### 后端文件（绝对路径）

#### 新增文件
```
E:\zngl-master\zngl\backend\apps\safety\management\commands\init_rectification_groups.py
```

#### 修改文件
```
E:\zngl-master\zngl\backend\apps\safety\rectification_views.py
E:\zngl-master\zngl\backend\apps\safety\urls.py
E:\zngl-master\zngl\backend\apps\users\views.py
```

### 前端文件（绝对路径）

#### 新增文件
```
E:\zngl-master\zngl\frontend\src\components\safety\AssignerManagementDialog.vue
```

#### 修改文件
```
E:\zngl-master\zngl\frontend\src\views\safety\RectificationCenterView.vue
E:\zngl-master\zngl\frontend\src\stores\user.ts
E:\zngl-master\zngl\frontend\src\views\safety\RectificationDetailView.vue
```

---

## 📦 附录 B：详细修改内容

### 后端修改详情

#### 1. rectification_views.py
**修改位置**：
- 第 37-43 行：新增 `_is_assigner()` 函数
- 第 45-58 行：修改 `_can_assign_or_verify()` 函数，添加分派人权限检查
- 第 439-548 行：新增 4 个 API 端点
  - `list_assigners()` - 查询已授权分派人
  - `grant_assigner()` - 授予分派权限
  - `revoke_assigner()` - 撤销分派权限
  - `list_assigner_candidates()` - 获取候选用户

**关键代码片段**：
```python
def _is_assigner(user) -> bool:
    """被授权的分派人"""
    return (
        user.is_authenticated
        and user.is_active
        and user.groups.filter(name='整改分派人').exists()
    )
```

#### 2. urls.py
**修改位置**：
- 第 79-83 行：新增 4 个路由

**新增路由**：
```python
path('rectifications/assigners/', views.list_assigners),
path('rectifications/assigners/grant/', views.grant_assigner),
path('rectifications/assigners/revoke/', views.revoke_assigner),
path('rectifications/assigners/candidates/', views.list_assigner_candidates),
```

#### 3. users/views.py
**修改位置**：
- 在用户信息序列化中添加 `is_assigner` 字段

**关键代码片段**：
```python
'is_assigner': request.user.groups.filter(name='整改分派人').exists()
```

### 前端修改详情

#### 1. AssignerManagementDialog.vue（新增）
**功能**：
- 已授权用户列表展示
- 授予权限功能
- 撤销权限功能
- 候选用户下拉选择

**组件结构**：
```vue
<template>
  <el-dialog>
    <el-tabs>
      <el-tab-pane name="authorized">  <!-- 已授权用户 -->
      <el-tab-pane name="grant">       <!-- 授予权限 -->
    </el-tabs>
  </el-dialog>
</template>
```

#### 2. RectificationCenterView.vue
**修改位置**：
- 添加"分派人管理"按钮（仅安全员可见）
- 引入 AssignerManagementDialog 组件
- 添加对话框显示控制逻辑

**关键代码片段**：
```vue
<el-button
  v-if="userStore.isSafetyOfficer"
  @click="showAssignerDialog = true"
>
  分派人管理
</el-button>
```

#### 3. user.ts
**修改位置**：
- 添加 `isAssigner` 状态字段
- 在用户信息加载时设置该字段

**关键代码片段**：
```typescript
interface UserState {
  isAssigner: boolean
  // ... 其他字段
}
```

#### 4. RectificationDetailView.vue
**修改位置**：
- 根据 `isAssigner` 权限显示/隐藏分派按钮
- 根据权限显示/隐藏验证按钮

---

## 📦 附录 C：快速部署脚本

### Windows 本地到服务器部署脚本

创建文件 `deploy_assigner_feature.bat`：

```batch
@echo off
echo ========================================
echo 整改分派人授权功能部署脚本
echo ========================================
echo.

set SERVER=root@172.24.69.125
set BACKEND_PATH=/opt/zs2/backend
set FRONTEND_PATH=/opt/zs2/frontend
set LOCAL_ROOT=E:\zngl-master\zngl

echo [1/6] 备份服务器文件...
ssh %SERVER% "mkdir -p ~/backup_$(date +%%Y%%m%%d_%%H%%M%%S)"
ssh %SERVER% "cp %BACKEND_PATH%/apps/safety/rectification_views.py ~/backup_$(date +%%Y%%m%%d_%%H%%M%%S)/"
ssh %SERVER% "cp %BACKEND_PATH%/apps/safety/urls.py ~/backup_$(date +%%Y%%m%%d_%%H%%M%%S)/"
ssh %SERVER% "cp %BACKEND_PATH%/apps/users/views.py ~/backup_$(date +%%Y%%m%%d_%%H%%M%%S)/"
echo 备份完成！
echo.

echo [2/6] 上传后端文件...
scp %LOCAL_ROOT%\backend\apps\safety\management\commands\init_rectification_groups.py %SERVER%:%BACKEND_PATH%/apps/safety/management/commands/
scp %LOCAL_ROOT%\backend\apps\safety\rectification_views.py %SERVER%:%BACKEND_PATH%/apps/safety/
scp %LOCAL_ROOT%\backend\apps\safety\urls.py %SERVER%:%BACKEND_PATH%/apps/safety/
scp %LOCAL_ROOT%\backend\apps\users\views.py %SERVER%:%BACKEND_PATH%/apps/users/
echo 后端文件上传完成！
echo.

echo [3/6] 初始化用户组...
ssh %SERVER% "cd %BACKEND_PATH% && source venv/bin/activate && python manage.py init_rectification_groups"
echo 用户组初始化完成！
echo.

echo [4/6] 构建前端...
cd %LOCAL_ROOT%\frontend
call npm run build
echo 前端构建完成！
echo.

echo [5/6] 上传前端文件...
scp -r %LOCAL_ROOT%\frontend\dist\* %SERVER%:%FRONTEND_PATH%/dist/
echo 前端文件上传完成！
echo.

echo [6/6] 重启服务...
ssh %SERVER% "systemctl restart zs2"
echo 服务重启完成！
echo.

echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 请执行以下验证步骤：
echo 1. 访问整改中心页面
echo 2. 使用安全员账号登录
echo 3. 检查是否显示"分派人管理"按钮
echo 4. 测试授予/撤销权限功能
echo.
pause
```

### Linux/Mac 部署脚本

创建文件 `deploy_assigner_feature.sh`：

```bash
#!/bin/bash

echo "========================================"
echo "整改分派人授权功能部署脚本"
echo "========================================"
echo

SERVER="root@172.24.69.125"
BACKEND_PATH="/opt/zs2/backend"
FRONTEND_PATH="/opt/zs2/frontend"
LOCAL_ROOT="/e/zngl-master/zngl"

echo "[1/6] 备份服务器文件..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
ssh $SERVER "mkdir -p ~/$BACKUP_DIR"
ssh $SERVER "cp $BACKEND_PATH/apps/safety/rectification_views.py ~/$BACKUP_DIR/"
ssh $SERVER "cp $BACKEND_PATH/apps/safety/urls.py ~/$BACKUP_DIR/"
ssh $SERVER "cp $BACKEND_PATH/apps/users/views.py ~/$BACKUP_DIR/"
echo "备份完成！备份目录：~/$BACKUP_DIR"
echo

echo "[2/6] 上传后端文件..."
scp $LOCAL_ROOT/backend/apps/safety/management/commands/init_rectification_groups.py \
    $SERVER:$BACKEND_PATH/apps/safety/management/commands/
scp $LOCAL_ROOT/backend/apps/safety/rectification_views.py $SERVER:$BACKEND_PATH/apps/safety/
scp $LOCAL_ROOT/backend/apps/safety/urls.py $SERVER:$BACKEND_PATH/apps/safety/
scp $LOCAL_ROOT/backend/apps/users/views.py $SERVER:$BACKEND_PATH/apps/users/
echo "后端文件上传完成！"
echo

echo "[3/6] 初始化用户组..."
ssh $SERVER "cd $BACKEND_PATH && source venv/bin/activate && python manage.py init_rectification_groups"
echo "用户组初始化完成！"
echo

echo "[4/6] 构建前端..."
cd $LOCAL_ROOT/frontend
npm run build
echo "前端构建完成！"
echo

echo "[5/6] 上传前端文件..."
scp -r $LOCAL_ROOT/frontend/dist/* $SERVER:$FRONTEND_PATH/dist/
echo "前端文件上传完成！"
echo

echo "[6/6] 重启服务..."
ssh $SERVER "systemctl restart zs2"
echo "服务重启完成！"
echo

echo "========================================"
echo "部署完成！"
echo "========================================"
echo
echo "请执行以下验证步骤："
echo "1. 访问整改中心页面"
echo "2. 使用安全员账号登录"
echo "3. 检查是否显示'分派人管理'按钮"
echo "4. 测试授予/撤销权限功能"
echo
```

**使用方法**：
```bash
chmod +x deploy_assigner_feature.sh
./deploy_assigner_feature.sh
```

---

## 📦 附录 D：回滚脚本

### 快速回滚脚本

创建文件 `rollback_assigner_feature.sh`：

```bash
#!/bin/bash

echo "========================================"
echo "整改分派人授权功能回滚脚本"
echo "========================================"
echo

SERVER="root@172.24.69.125"
BACKEND_PATH="/opt/zs2/backend"
FRONTEND_PATH="/opt/zs2/frontend"

# 提示输入备份目录
read -p "请输入备份目录名称（例如：backup_20260424_100000）: " BACKUP_DIR

if [ -z "$BACKUP_DIR" ]; then
    echo "错误：备份目录不能为空"
    exit 1
fi

echo
echo "[1/4] 停止服务..."
ssh $SERVER "systemctl stop zs2"
echo "服务已停止"
echo

echo "[2/4] 恢复后端文件..."
ssh $SERVER "cp ~/$BACKUP_DIR/rectification_views.py $BACKEND_PATH/apps/safety/"
ssh $SERVER "cp ~/$BACKUP_DIR/urls.py $BACKEND_PATH/apps/safety/"
ssh $SERVER "cp ~/$BACKUP_DIR/views.py $BACKEND_PATH/apps/users/"
ssh $SERVER "rm -f $BACKEND_PATH/apps/safety/management/commands/init_rectification_groups.py"
echo "后端文件已恢复"
echo

echo "[3/4] 删除用户组（可选）..."
read -p "是否删除'整改分派人'用户组？(y/n): " DELETE_GROUP
if [ "$DELETE_GROUP" = "y" ]; then
    ssh $SERVER "cd $BACKEND_PATH && source venv/bin/activate && python manage.py shell -c \"from django.contrib.auth.models import Group; Group.objects.filter(name='整改分派人').delete()\""
    echo "用户组已删除"
else
    echo "保留用户组"
fi
echo

echo "[4/4] 重启服务..."
ssh $SERVER "systemctl start zs2"
echo "服务已重启"
echo

echo "========================================"
echo "回滚完成！"
echo "========================================"
echo
echo "注意："
echo "1. 前端文件需要重新构建和部署旧版本"
echo "2. 已授权的用户将失去分派权限"
echo "3. 建议验证系统功能是否正常"
echo
```

---

## 📦 附录 E：测试用例清单

### 自动化测试脚本

创建文件 `test_assigner_feature.py`：

```python
"""
整改分派人授权功能测试脚本
"""
import requests
import json

# 配置
BASE_URL = "http://172.24.69.125:9527/api"
ADMIN_TOKEN = "your_admin_token_here"
ASSIGNER_TOKEN = "your_assigner_token_here"
USER_TOKEN = "your_user_token_here"

def test_list_assigners():
    """测试：查询已授权分派人"""
    print("\n[测试] 查询已授权分派人...")
    response = requests.get(
        f"{BASE_URL}/safety/rectifications/assigners/",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    assert response.status_code == 200

def test_grant_assigner():
    """测试：授予分派权限"""
    print("\n[测试] 授予分派权限...")
    response = requests.post(
        f"{BASE_URL}/safety/rectifications/assigners/grant/",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"user_id": 123}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    assert response.status_code == 200

def test_revoke_assigner():
    """测试：撤销分派权限"""
    print("\n[测试] 撤销分派权限...")
    response = requests.post(
        f"{BASE_URL}/safety/rectifications/assigners/revoke/",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"user_id": 123}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    assert response.status_code == 200

def test_list_candidates():
    """测试：获取候选用户"""
    print("\n[测试] 获取候选用户...")
    response = requests.get(
        f"{BASE_URL}/safety/rectifications/assigners/candidates/",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    assert response.status_code == 200

def test_permission_denied():
    """测试：普通用户无权限"""
    print("\n[测试] 普通用户无权限...")
    response = requests.get(
        f"{BASE_URL}/safety/rectifications/assigners/",
        headers={"Authorization": f"Bearer {USER_TOKEN}"}
    )
    print(f"状态码: {response.status_code}")
    assert response.status_code == 403

if __name__ == "__main__":
    print("========================================")
    print("整改分派人授权功能测试")
    print("========================================")
    
    try:
        test_list_assigners()
        test_grant_assigner()
        test_list_candidates()
        test_revoke_assigner()
        test_permission_denied()
        
        print("\n========================================")
        print("所有测试通过！✅")
        print("========================================")
    except AssertionError as e:
        print(f"\n测试失败！❌")
        print(f"错误: {e}")
    except Exception as e:
        print(f"\n测试异常！❌")
        print(f"错误: {e}")
```

---

## 📦 附录 F：常见问题 FAQ

### Q1: 授权后用户需要重新登录吗？
**A**: 不需要。权限检查是实时的，授权后立即生效。但建议用户刷新页面以更新 UI 状态。

### Q2: 可以批量授予权限吗？
**A**: 当前版本不支持批量操作。如需批量授予，可以使用 Django shell：
```python
from django.contrib.auth.models import User, Group
group = Group.objects.get(name='整改分派人')
users = User.objects.filter(username__in=['user1', 'user2', 'user3'])
for user in users:
    user.groups.add(group)
```

### Q3: 分派人可以验证整改吗？
**A**: 不可以，除非该分派人同时被指定为该工单的验证人。这是为了保证验证的独立性。

### Q4: 如何查看所有分派人的操作记录？
**A**: 查看服务器日志：
```bash
journalctl -u zs2 | grep "整改分派"
```

### Q5: 用户离职后如何处理权限？
**A**: 
1. 方案一：撤销分派权限（保留用户账号）
2. 方案二：停用用户账号（自动失去所有权限）
3. 方案三：删除用户账号（不推荐，会影响历史记录）

### Q6: 权限有有效期吗？
**A**: 当前版本没有有效期限制。如需添加有效期功能，请参考"后续优化建议"章节。

### Q7: 如何监控权限使用情况？
**A**: 可以通过以下 SQL 查询：
```sql
-- 查询所有分派人
SELECT u.username, u.first_name, u.last_name, u.is_active
FROM auth_user u
JOIN auth_user_groups ug ON u.id = ug.user_id
JOIN auth_group g ON ug.group_id = g.id
WHERE g.name = '整改分派人';

-- 查询分派人的操作记录
SELECT ro.*, u.username as assigner
FROM safety_rectificationorder ro
JOIN auth_user u ON ro.assigned_by_id = u.id
JOIN auth_user_groups ug ON u.id = ug.user_id
JOIN auth_group g ON ug.group_id = g.id
WHERE g.name = '整改分派人'
ORDER BY ro.assigned_at DESC;
```

---

## 📦 附录 G：性能监控

### 监控指标

1. **API 响应时间**：
```bash
# 监控授权 API 响应时间
curl -w "@curl-format.txt" -o /dev/null -s \
  -X GET "http://localhost:9527/api/safety/rectifications/assigners/" \
  -H "Authorization: Bearer <token>"
```

创建 `curl-format.txt`：
```
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_appconnect:  %{time_appconnect}\n
time_pretransfer:  %{time_pretransfer}\n
time_redirect:  %{time_redirect}\n
time_starttransfer:  %{time_starttransfer}\n
----------\n
time_total:  %{time_total}\n
```

2. **数据库查询性能**：
```python
# 在 Django shell 中执行
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as queries:
    # 执行查询
    from apps.safety.rectification_views import list_assigners
    # ... 调用函数
    
print(f"查询次数: {len(queries)}")
for query in queries:
    print(f"耗时: {query['time']}s")
    print(f"SQL: {query['sql']}")
```

3. **内存使用**：
```bash
# 监控服务内存使用
ps aux | grep "python.*manage.py"
```

---

## 📦 附录 H：部署检查表

### 部署前检查
- [ ] 已阅读完整部署文档
- [ ] 已备份所有修改的文件
- [ ] 已确认服务器环境满足要求
- [ ] 已获得部署权限
- [ ] 已通知相关人员部署时间窗口

### 部署中检查
- [ ] 后端文件上传成功
- [ ] 前端文件上传成功
- [ ] 用户组初始化成功
- [ ] 服务重启成功
- [ ] 无错误日志

### 部署后检查
- [ ] API 端点可访问
- [ ] 前端页面正常显示
- [ ] 安全员可以看到管理按钮
- [ ] 授予权限功能正常
- [ ] 撤销权限功能正常
- [ ] 分派人可以分派工单
- [ ] 普通用户无权限访问
- [ ] 日志记录正常

### 验收检查
- [ ] 所有测试用例通过
- [ ] 性能指标符合要求
- [ ] 用户反馈良好
- [ ] 文档已更新
- [ ] 培训已完成

---

**最后更新**: 2026-04-24  
**文档版本**: v1.1.0  
**维护人**: 开发团队
