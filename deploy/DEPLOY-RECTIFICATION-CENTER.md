# 安全管理 — 统一整改中心 部署指南

## 功能说明

把"安全隐患上报、除尘房巡检、夜班监护检查"三个模块发现的问题，统一汇入新的**整改中心**进行 **分派 → 整改 → 验证 → 闭环** 流程。

核心改动:

- 新增统一工单表 `RectificationOrder`（含图片表 `RectificationImage`、操作日志 `RectificationLog`）
- 隐患上报：每条隐患同步生成一条整改工单（流转保持双写）
- 除尘房巡检：异常项且填写了说明的，自动生成整改工单
- 夜班监护：每条问题（未标记"已整改"）自动生成整改工单
- 安全管理总览页 + 侧边栏 新增"整改中心"入口
- 新增定时任务：`mark_overdue_rectifications` 标记逾期工单

**仅修改安全模块（apps/safety）**，不影响 quality / equipment / monitoring / users / ai_analysis。

---

## 本次变更文件清单

### 后端（apps/safety）

| # | 路径 | 类型 | 说明 |
|---|---|---|---|
| 1 | `backend/apps/safety/models.py` | 修改 | 新增 RectificationOrder / RectificationImage / RectificationLog 三个模型 |
| 2 | `backend/apps/safety/migrations/0008_rectification.py` | 新增 | 建表 + 把存量 HazardReport 复制成整改工单 |
| 3 | `backend/apps/safety/rectification_service.py` | 新增 | 领域服务层（状态机唯一入口） |
| 4 | `backend/apps/safety/rectification_serializers.py` | 新增 | DRF 序列化器 |
| 5 | `backend/apps/safety/rectification_views.py` | 新增 | DRF 视图（list / detail / assign / submit / verify / cancel / my / stats） |
| 6 | `backend/apps/safety/urls.py` | 修改 | 新增 9 条 `/rectifications/*` 路由 |
| 7 | `backend/apps/safety/permissions.py` | 修改 | 新增 `IsRectificationAssignee` |
| 8 | `backend/apps/safety/admin.py` | 修改 | 注册三个新模型到 Django Admin |
| 9 | `backend/apps/safety/views.py` | 修改 | 隐患创建/分派/整改/验证 同步驱动整改工单 |
| 10 | `backend/apps/safety/dustroom_views.py` | 修改 | 巡检异常项自动建工单 |
| 11 | `backend/apps/safety/nightshift_views.py` | 修改 | 夜班问题自动建工单 |
| 12 | `backend/apps/safety/management/__init__.py` | 新增 | Django 管理命令包初始化 |
| 13 | `backend/apps/safety/management/commands/__init__.py` | 新增 | 命令包初始化 |
| 14 | `backend/apps/safety/management/commands/mark_overdue_rectifications.py` | 新增 | 逾期工单扫描命令 |

### 前端

| # | 路径 | 类型 | 说明 |
|---|---|---|---|
| 1 | `frontend/src/api/rectification.ts` | 新增 | 整改中心 API 封装 |
| 2 | `frontend/src/views/safety/RectificationCenterView.vue` | 新增 | 整改中心工作台（4 个 scope 页签 + 筛选 + 列表） |
| 3 | `frontend/src/views/safety/RectificationDetailView.vue` | 新增 | 工单详情页（流转时间线 + 操作面板） |
| 4 | `frontend/src/router/index.ts` | 修改 | 新增 `/safety/rectification` 与 `/safety/rectification/:id` |
| 5 | `frontend/src/views/safety/SafetyView.vue` | 修改 | 总览页新增"整改中心"卡片 |
| 6 | `frontend/src/components/layout/SidebarNav.vue` | 修改 | 侧边栏"安全管理"组下新增"整改中心" |

**数据库变更**：1 个 migration（`0008_rectification`），含数据回填，**必须执行 `migrate`**
**后端依赖变更**：无
**前端依赖变更**：无

---

## 一、本地预检（强烈建议）

```powershell
# 后端
cd backend
.\venv\Scripts\python.exe manage.py makemigrations --dry-run safety
# 期望输出: "No changes detected in app 'safety'"

.\venv\Scripts\python.exe manage.py migrate safety --plan | head -5
# 期望输出: 0008_rectification 在计划中

# 前端类型检查 + 构建
cd ..\frontend
npm run build
# 期望: ✓ built in ...，无 TS 错误
```

---

## 二、服务器端部署（按顺序）

### 1. 备份

```bash
cd /opt/zs2
BK=/opt/zs2/backups/$(date +%Y%m%d-%H%M%S)-rectification
mkdir -p "$BK"

# 备份数据库（迁移含数据回填，必须先备份！）
cp backend/db.sqlite3 "$BK/db.sqlite3"  # 若是 SQLite
# 或 PostgreSQL: pg_dump -U <user> <db> > "$BK/db.sql"

# 备份将被覆盖的文件
cp -r backend/apps/safety "$BK/safety-bak"
cp -r frontend/dist       "$BK/dist-bak"
```

### 2. 同步代码（从 GitHub 拉取最新）

```bash
cd /opt/zs2
git fetch origin
git status                     # 确认没有未提交的本地修改
git pull origin master         # 或 git checkout <commit-sha>
```

> 若服务器上是 detach HEAD 或独立部署（不含 .git），则使用 patch 包方式：
> 在本地 `git diff <旧 commit> HEAD -- backend/apps/safety frontend/src` 生成补丁，scp 上传后 `git apply`。

### 3. 应用数据库迁移（含存量隐患回填）

```bash
cd /opt/zs2/backend
source /opt/zs2/venv/bin/activate

# 先看一眼计划，确认只有 0008_rectification 这一条
python manage.py migrate --plan | head -10

# 执行
python manage.py migrate safety
# 期望: Applying safety.0008_rectification... OK
```

**校验回填结果**：

```bash
python manage.py shell <<'PY'
from apps.safety.models import HazardReport, RectificationOrder
print("HazardReport:", HazardReport.objects.count())
print("RectificationOrder:", RectificationOrder.objects.count())
print("  来自 hazard_report:", RectificationOrder.objects.filter(source_type='hazard_report').count())
PY
```

两个数字应**相等**（每条 HazardReport 都被复制为一条整改工单）。

### 4. 重新构建并发布前端

如果你是在服务器上构建：

```bash
cd /opt/zs2/frontend
npm ci                  # 仅当 package-lock.json 变化时
npm run build
```

如果是本地构建后上传 dist:

```bash
# 本地
cd frontend && npm run build
scp -r dist/* root@<server>:/opt/zs2/frontend/dist/
```

### 5. 重启后端

```bash
systemctl restart zs2
systemctl status zs2 --no-pager -l | head -20
journalctl -u zs2 -n 100 --no-pager | grep -iE "error|rectif" | head -30
```

Nginx 不需要 reload（路径未变）。浏览器强制刷新（Ctrl+F5）。

### 6. 配置逾期工单定时任务

新增一个 crontab，每小时扫描一次逾期工单并打标记：

```bash
crontab -e
```

加入：

```cron
# 每小时第 5 分钟扫描整改工单逾期情况
5 * * * * cd /opt/zs2/backend && /opt/zs2/venv/bin/python manage.py mark_overdue_rectifications >> /var/log/zngl/overdue.log 2>&1
```

> 若日志目录不存在: `mkdir -p /var/log/zngl && chown <运行用户>:<运行用户> /var/log/zngl`

---

## 三、线上验证清单

浏览器访问 `http://<服务器地址>/zszngl/` → 登录安全员账号：

- [ ] 侧边栏"安全管理 → 整改中心"可见
- [ ] 安全管理总览页出现"整改中心"卡片，数字与历史隐患数一致
- [ ] 进入整改中心，4 个页签计数正确：全部 / 待我整改 / 待我验证 / 待我分派 / 我提交的
- [ ] 列表筛选（来源、状态、严重等级、逾期、日期、关键词）均能命中
- [ ] 点击一条已存在的工单 → 详情页加载正常，操作日志含 1 条"由存量隐患上报迁移"
- [ ] 新建一条隐患（隐患上报页）→ 在整改中心立刻看到对应工单（待分派）
- [ ] 进入除尘房做一次巡检，故意标一项异常并填写"现场说明"提交 → 整改中心出现新工单
- [ ] 进入夜班监护提交一条问题且不勾选"已整改" → 整改中心出现新工单
- [ ] 安全员对一条工单点击"分派"→ 选责任人 → 状态变更为"整改中"
- [ ] 责任人账号登录 → 在"待我整改"页签 → 进入工单 → 提交整改说明（带图）→ 状态变更为"待验证"
- [ ] 安全员账号 → "待我验证"页签 → 通过/驳回 → 状态正确流转 + 操作日志一条
- [ ] 普通工人账号登录：只看到自己提交/责任的工单，不能分派/验证

非安全员的可见范围：默认只看到 `submitter == 自己 OR assignee == 自己 OR verifier == 自己` 的工单。

---

## 四、回滚方案

如果发布后发现问题：

```bash
# 1) 立即停止服务
systemctl stop zs2

# 2) 还原后端代码
cp -r $BK/safety-bak/* /opt/zs2/backend/apps/safety/

# 3) 还原前端
rm -rf /opt/zs2/frontend/dist
cp -r $BK/dist-bak /opt/zs2/frontend/dist

# 4) 数据库回滚（关键！）
# 选项 A：只回退迁移（保留新表数据，但代码不再依赖时无害）
cd /opt/zs2/backend
source /opt/zs2/venv/bin/activate
python manage.py migrate safety 0007  # 回到上一个版本
#   反向迁移会自动 drop 三张新表，并删除回填的工单数据

# 选项 B：直接还原数据库备份（推荐，更彻底）
systemctl stop zs2
cp $BK/db.sqlite3 /opt/zs2/backend/db.sqlite3
# 或 PostgreSQL: psql -U <user> -d <db> < $BK/db.sql

# 5) 重启
systemctl start zs2
```

---

## 五、常见问题

**Q：迁移执行慢吗？**
A：回填会逐行处理 HazardReport，O(n)。系统目前只有少量隐患数据，迁移在数秒内完成。

**Q：旧的 `/api/safety/hazards/*` 接口还能用吗？**
A：能。旧接口保留，且会**双写**到整改中心（hazard 操作时同步驱动关联工单）。这意味着用户可以选择继续用旧的"随手拍"页面，或者用新整改中心。

**Q：用户没分配 `安全员` 用户组怎么办？**
A：分派/验证 API 会被 `IsSafetyOfficer` 拒绝。在 Django Admin 给对应用户加入"安全员"组即可。

**Q：除尘房巡检异常项每次都建工单会不会刷屏？**
A：只有 `is_normal=False` **且**填写了 `remark` 才建。空备注的异常项不会触发，避免噪声。

**Q：夜班问题里勾了"已整改"还会建工单吗？**
A：不会。前端检查人若已现场处理完就标"已整改"，整改中心不会重复建单。

---

## 六、扩展（二期再做）

- 站内/短信通知（分派、临期、逾期、验证完成）
- 分派规则表（按区域/严重等级自动指派）
- 整改看板（按部门、责任人、逾期率、平均整改时长出多维报表）
- 隐患旧 UI 完全切换到整改中心后下线 `/api/safety/hazards/` 接口
