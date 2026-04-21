# 部署脚本更新日志

## 2026-03-28 - 质量模块优化与迁移自动化

### 新增功能
1. **自动生成迁移文件**
   - 新增 `pack-with-migrations.ps1` 脚本
   - 打包前自动执行 `python manage.py makemigrations`
   - 确保数据库模型变更自动包含在部署包中

### 质量模块更新
1. **数据库模型调整**
   - `sampling_date` 字段改为允许空值（`null=True, blank=True`）
   - `rolling_moisture` 字段名称从"卷丝水分"改为"卷制水分"

2. **Excel 导入优化**
   - 改为按列位置读取数据，不依赖表头名称
   - G列（索引6）→ 成品水分
   - P列（索引15）→ 卷制水分
   - 无效采样日期保存为 NULL，不再跳过记录

3. **趋势图交互优化**
   - 隐藏所有趋势图横轴
   - 成品水分趋势图纵轴区间调整为 11.5-13.5
   - 新增详细悬停信息：取样日期、样品编号、机台、加丝机、批次号、班次、各类水分数据

### 使用方法

**打包（含迁移）：**
```powershell
.\deploy\pack-with-migrations.ps1
```

**打包（不生成迁移）：**
```powershell
.\deploy\pack.ps1
```

## 2026-03-27 - CentOS 7 部署适配

### 问题与解决方案

#### 1. Node.js 版本兼容性问题
**问题：** CentOS 7 的 glibc 2.17 无法运行 Node.js 18+，而 Vite 5 需要 Node.js 18+
**解决：**
- 前端在 Windows 本地构建（`npm run build`）
- 打包时直接包含 `dist/` 构建产物
- 服务器不再需要安装 Node.js

#### 2. PostgreSQL 官方源失效
**问题：** PostgreSQL 官方源停止支持 CentOS 7
**解决：** 使用 PostgreSQL 15 归档源
```bash
baseurl=https://yum-archive.postgresql.org/15/redhat/rhel-7-x86_64/
```

#### 3. Python 依赖下载问题
**问题：** `pip download --only-binary :all:` 找不到纯 Python 包（如 `exceptiongroup`）
**解决：** 三步下载策略
- 第一步：下载 C 扩展的 manylinux wheel（`--only-binary :all: --no-deps`）
- 第二步：下载 daphne 的 manylinux wheel
- 第三步：补充下载所有纯 Python 包（`--prefer-binary`，不限平台）

#### 4. PowerShell 编码问题
**问题：** `pack.ps1` 中的中文字符导致解析错误（字符串缺少终止符）
**解决：**
- 设置控制台编码为 UTF-8
- 优化字符串处理，避免混合中英文导致的编码问题

#### 5. SELinux 阻止 Nginx 连接后端
**问题：** CentOS 7 默认 SELinux Enforcing 模式阻止 Nginx 连接 Daphne（502 Bad Gateway）
**解决：**
```bash
setsebool -P httpd_can_network_connect 1
```
已集成到部署脚本中自动执行

#### 6. ALLOWED_HOSTS 配置错误
**问题：** `.env` 文件中 `ALLOWED_HOSTS` 配置重复且格式错误，导致 400 错误
**解决：**
- 统一使用 `ALLOWED_HOSTS=*`（生产环境建议改为具体 IP）
- 部署脚本自动生成正确的 `.env` 配置

#### 7. 初始化脚本未执行
**问题：** 演示数据初始化脚本在部署时可能因编码问题未成功执行
**解决：** 提供手动初始化命令
```bash
python manage.py shell -c "exec(open('scripts/init_demo_data.py', encoding='utf-8').read())"
python manage.py shell -c "exec(open('scripts/init_safety_data.py', encoding='utf-8').read())"
```

### 文件变更

#### 新增文件
- `deploy/pack.ps1` - Windows 打包脚本（构建前端 + 下载依赖）
- `deploy/install.sh` - CentOS 7 一键部署脚本
- `deploy/README.md` - 完整部署文档
- `deploy/QUICKSTART.md` - 快速上手指南
- `deploy/CHANGELOG.md` - 本文件

#### 修改文件
- `backend/config/settings/base.py`
  - 新增 `STATIC_ROOT = BASE_DIR / 'staticfiles'`（用于 `collectstatic`）

### 部署架构

```
Windows 本地
  ├── 前端构建（npm run build）
  ├── 下载 Python Linux 依赖包（pip download）
  └── 打包（tar.gz）
       ↓
CentOS 7 服务器
  ├── Python 3.10（源码编译）
  ├── PostgreSQL 15（归档源）
  ├── Nginx（反向代理）
  ├── Daphne（ASGI 服务器）
  └── 离线安装 Python 依赖
```

### 部署步骤（简化版）

**Windows 上：**
```powershell
cd "F:\zs2 Management System"
.\deploy\pack.ps1
scp deploy\zs2-deploy.tar.gz root@服务器IP:/root/
```

**CentOS 7 上：**
```bash
mkdir -p /opt/zs2
tar xzf /root/zs2-deploy.tar.gz -C /opt/zs2
cd /opt/zs2
bash install.sh
```

### 已知问题

1. **AI 功能网络隔离**
   - 如果 Ollama/RAGflow 部署在其他机器，需要确保防火墙开放相应端口
   - Windows 防火墙需要手动开放 80 端口（RAGflow）

2. **Python 编译耗时**
   - 首次部署时 Python 3.10 源码编译约需 15-20 分钟
   - 后续部署会跳过此步骤

3. **账号初始化**
   - 如果自动初始化失败，需要手动执行初始化脚本
   - 默认账号：safety/leader/worker，密码均为 password123

### 性能优化

- ✅ 前端在本地构建，服务器无需 Node.js
- ✅ Python 依赖离线安装，无需联网下载
- ✅ 使用 manylinux wheel，避免服务器编译 C 扩展
- ✅ SELinux 配置自动化，避免手动排查 502 错误

### 安全建议

生产环境部署后，建议修改以下配置：

1. **限制 ALLOWED_HOSTS**
   ```bash
   # /opt/zs2/backend/.env
   ALLOWED_HOSTS=10.10.10.128,yourdomain.com
   ```

2. **修改默认密码**
   ```bash
   python manage.py changepassword safety
   python manage.py changepassword leader
   python manage.py changepassword worker
   ```

3. **启用 HTTPS**（可选）
   - 配置 Nginx SSL 证书
   - 修改前端 WebSocket 连接为 `wss://`

4. **数据库备份**
   ```bash
   # 定期备份
   sudo -u postgres pg_dump zs2_db > backup_$(date +%Y%m%d).sql
   ```
