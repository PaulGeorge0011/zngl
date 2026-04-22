# 夜班监护 - 排班日历 增量部署指南

## 功能说明

在夜班监护检查模块首页新增**排班日历**：

- **日历视图**：月度日历展示每日值班人员（所有人可见）
- **排班管理**：安全员点击日期可添加/修改/删除值班人员
- **监护统计**：当月/全部历史维度，按人员统计排班次数、完成数、问题数并排名
- **复用**：沿用 `NightShiftDuty` 模型与现有排班接口；新增 1 个统计接口

## 本次修改文件清单

| # | 路径 | 类型 | 说明 |
|---|------|------|------|
| 1 | `backend/apps/safety/nightshift_views.py` | 修改 | 新增 `inspector_stats` 视图 + 导入 `Count, Q` |
| 2 | `backend/apps/safety/urls.py` | 修改 | 新增 `nightshift/inspector-stats/` 路由 |
| 3 | `frontend/src/api/nightshift.ts` | 修改 | 新增 `InspectorStatRow / InspectorStatsResponse` 类型 + `getInspectorStats()` 方法（已编入 dist） |
| 4 | `frontend/src/views/safety/NightShiftView.vue` | 重写 | 首页从列表改为日历 + 统计表（已编入 dist） |

**数据库变更**：无。不需要执行 `migrate`。
**后端依赖变更**：无。不需要 `pip install`。
**新文件**：无。全部是对现有文件的修改。

---

## 一、本地打包

在项目根目录 `E:\zngl-master\zngl` 运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\pack-nightshift-schedule.ps1
```

执行流程：

1. 收集 2 个后端 `.py` 文件到 `deploy\patch-nightshift-schedule\backend\apps\safety\`
2. 在 `frontend\` 下运行 `npm run build`（含 `vue-tsc` 类型检查）
3. 复制 `frontend\dist\` 到 `deploy\patch-nightshift-schedule\frontend\dist\`
4. 打包为 `deploy\patch-nightshift-schedule.zip`（约 860 KB）

成功后输出：

```
patch zip generated:
  E:\zngl-master\zngl\deploy\patch-nightshift-schedule.zip
```

---

## 二、本地验证（可选，建议）

在上传前本地起两端快速自测：

```powershell
# 终端 1：后端
cd backend
.\venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8000

# 终端 2：前端
cd frontend
npm run dev
```

浏览器打开 `http://localhost:3001/` → 登录安全员账号 → 进入**夜班监护检查**：

- [ ] 首页显示月度日历，已有排班的日期显示检查人姓名
- [ ] 点击空白日期 → 弹出排班对话框 → 选择人员 → 保存成功
- [ ] 再次点击该日期 → 可修改/删除
- [ ] 日历下方出现**监护次数统计**表，切换"本月 / 全部历史"正常
- [ ] 非安全员账号登录：日历只读，点击日期不弹框
- [ ] 今日概览卡、今日检查情况、问题列表（原有功能）均正常

---

## 三、上传补丁到服务器

假设工厂服务器参数（来自 `deploy\` 下原有脚本）：

- SSH 地址：`10.46.1.11`（或工厂内网实际 IP）
- 用户：`root`
- 项目路径：`/opt/zs2/`
- 服务名：`zs2.service`

使用 WinSCP / scp / 共享盘等任一方式上传：

```powershell
scp deploy\patch-nightshift-schedule.zip root@10.46.1.11:/tmp/
```

---

## 四、服务器端部署

登录服务器执行（建议**先备份、再替换、最后重启**）：

```bash
cd /opt/zs2

# 1) 备份本次将被覆盖的 4 类产物
BK=/opt/zs2/backups/$(date +%Y%m%d-%H%M%S)-nightshift-schedule
mkdir -p "$BK"
cp backend/apps/safety/nightshift_views.py "$BK/"
cp backend/apps/safety/urls.py             "$BK/"
cp -r frontend/dist "$BK/dist"

# 2) 解压补丁（直接覆盖当前目录）
cd /tmp
rm -rf patch-nightshift-schedule
mkdir  patch-nightshift-schedule
cd     patch-nightshift-schedule
unzip -o /tmp/patch-nightshift-schedule.zip

# 3) 替换后端文件
cp backend/apps/safety/nightshift_views.py /opt/zs2/backend/apps/safety/
cp backend/apps/safety/urls.py             /opt/zs2/backend/apps/safety/

# 4) 替换前端产物（整体替换 dist 目录）
rm -rf /opt/zs2/frontend/dist
cp -r frontend/dist /opt/zs2/frontend/dist

# 5) 确认无数据库迁移（应显示 No migrations to apply）
cd /opt/zs2/backend
source /opt/zs2/venv/bin/activate
python manage.py showmigrations safety | tail -20
python manage.py migrate --plan | head -5

# 6) 重启后端服务
systemctl restart zs2

# 7) 查看状态
systemctl status zs2 --no-pager -l | head -30
journalctl -u zs2 -n 50 --no-pager
```

Nginx 无需 reload（仅静态文件更新，路径未变）。如果浏览器看到旧页面，强制刷新 `Ctrl+F5`。

---

## 五、线上验证

浏览器访问 `http://<服务器地址>/zszngl/` → 登录 → 进入**夜班监护检查**：

- [ ] 日历正常加载，历史排班数据正确显示
- [ ] 安全员添加/修改/删除排班生效
- [ ] 监护次数统计可切换"本月 / 全部历史"
- [ ] 普通工人登录只能查看，不能编辑
- [ ] 底部今日概览、检查情况、问题列表照常

浏览器 DevTools Network：
- `GET /api/safety/nightshift/duties/?month=YYYY-MM` → 200
- `GET /api/safety/nightshift/inspector-stats/?month=YYYY-MM` → 200（**新接口**）

---

## 六、回滚

如果线上出现异常，从第四步备份目录回滚：

```bash
BK=/opt/zs2/backups/<刚才的时间戳>-nightshift-schedule

cp "$BK/nightshift_views.py" /opt/zs2/backend/apps/safety/
cp "$BK/urls.py"             /opt/zs2/backend/apps/safety/

rm -rf /opt/zs2/frontend/dist
cp -r "$BK/dist" /opt/zs2/frontend/dist

systemctl restart zs2
```

因无数据库变更，回滚**无需处理数据**。

---

## 附：关键变更速览

### 后端新增接口

`GET /api/safety/nightshift/inspector-stats/?month=YYYY-MM`（month 可选）

```json
{
  "month": "2026-04",
  "results": [
    {
      "inspector_id": 3,
      "username": "zhang",
      "display_name": "张三",
      "total": 12,
      "completed": 10,
      "pending": 2,
      "with_issues": 3
    }
  ]
}
```

### 复用的已有接口

- `GET /api/safety/nightshift/duties/?month=YYYY-MM` —— 日历加载当月排班
- `POST /api/safety/nightshift/duties/` —— 新增排班（`dates: [YYYY-MM-DD], inspector`）
- `PUT /api/safety/nightshift/duties/{id}/` —— 修改排班
- `DELETE /api/safety/nightshift/duties/{id}/` —— 删除排班
- `GET /api/users/list/` —— 排班人员下拉（已存在）
