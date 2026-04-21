# 部署步骤速查

## Windows 本地操作

```powershell
# 1. 打包（包含迁移文件）
cd "F:\zs2 Management System"
.\deploy\pack-with-migrations.ps1

# 2. 上传（替换目标 IP）
scp deploy\zs2-deploy.tar.gz root@192.168.1.100:/root/
```

## CentOS 7 服务器操作

```bash
# 1. 解压
mkdir -p /opt/zs2
tar xzf /root/zs2-deploy.tar.gz -C /opt/zs2

# 2. 一键部署
cd /opt/zs2
bash install.sh

# 3. 访问
# http://服务器IP:9527
# 默认账号: safety / password123
```

## 服务管理

```bash
systemctl status zs2
systemctl restart zs2
journalctl -u zs2 -f
```

## 注意事项

1. 部署时间通常 20-30 分钟，取决于服务器性能和网络环境。
2. 需要 `root` 权限执行安装脚本。
3. 离线部署场景下，依赖包由打包产物提供。
4. 防火墙会自动开放 `9527` 端口。
5. 内网访问地址通常为 `http://服务器IP:9527`。

## 云南中烟 SSO 登录配置

启用单点登录前，需要在服务器上手动编辑 `/opt/zs2/backend/.env`，补充以下配置：

```dotenv
APP_EXTERNAL_BASE_URL=https://yxcf-yzyy.ynzy-tobacco.com/zszngl
SSO_ENABLED=True
SSO_CLIENT_ID=zszngl
SSO_CLIENT_SECRET=<向信息管理科获取的密钥>
SSO_BASE_URL=<SSO 指南中的 base_url>
SSO_AUTHORIZE_URL=<base_url>/realms/yxcf/protocol/openid-connect/auth
SSO_TOKEN_URL=<base_url>/realms/yxcf/protocol/openid-connect/token
SSO_USERINFO_URL=<base_url>/realms/yxcf/protocol/openid-connect/userinfo
SSO_INTROSPECT_URL=<base_url>/realms/yxcf/protocol/openid-connect/token/introspect
SSO_REDIRECT_URI=https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/
SSO_SCOPE=openid email profile custom_scope
SSO_KC_IDP_HINT=wechat-work
CSRF_TRUSTED_ORIGINS=https://yxcf-yzyy.ynzy-tobacco.com
```

修改完成后重启服务：

```bash
systemctl restart zs2
```

SSO 回调地址：

```text
https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/
```

外网访问地址：

```text
https://yxcf-yzyy.ynzy-tobacco.com/zszngl/
```

安全提示：`SSO_CLIENT_SECRET` 只保存在服务器 `.env` 中，不要提交到仓库。

## 前端显示说明

- 登录页支持本地登录和“云南中烟登录”双入口
- 系统右上角支持 `Light / Dark` 主题切换
- 主题偏好保存在浏览器本地，刷新后仍会保留
- 当前主要业务页面已完成手机端适配，可直接在移动浏览器访问
- 手机端通过顶部菜单按钮展开导航
- 窄屏下表格页支持横向滑动查看完整列

## 前端环境变量建议

如果通过 `/zszngl/` 子路径对外发布，前端构建时建议显式配置：

```dotenv
VITE_APP_BASE=/zszngl/
VITE_API_BASE=/zszngl
```

这样登录页、路由跳转和 SSO 发起地址都会统一走子路径前缀。
