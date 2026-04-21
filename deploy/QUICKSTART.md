# 部署快速指南

## Windows 本地打包

```powershell
# 1. 打包（包含迁移文件）
cd "F:\zs2 Management System"

# 如果外网通过 /zszngl/ 子路径发布，请在打包前设置：
$env:ZS2_VITE_APP_BASE="/zszngl/"
$env:ZS2_VITE_API_BASE="/zszngl"
$env:ZS2_VITE_WS_BASE=""

.\deploy\pack-with-migrations.ps1

# 2. 上传（替换目标 IP）
# scp deploy\zs2-deploy.tar.gz root@172.24.69.125:/root/
```

## CentOS 7 服务器部署

```bash
# 1. 解压
mkdir -p /opt/zs2
 tar xzf /root/zs2-deploy.tar.gz -C /opt/zs2

# 2. 一键部署
cd /opt/zs2
bash install.sh

# 3. 访问
# 内网： http://服务器IP:9527
# 外网： https://yxcf-yzyy.ynzy-tobacco.com/zszngl/
# 默认账号: safety / password123
```

## 服务管理

```bash
systemctl status zs2
systemctl restart zs2
journalctl -u zs2 -f
```

## 注意事项

1. 部署时间通常 20-30 分钟，取决于服务器性能。
2. 需要 root 权限执行安装脚本。
3. 离线部署依赖打包产物，不依赖外网。
4. 防火墙会自动开放 9527 端口。
5. 外网场景必须在 HTTPS 域名下访问，并在代理层传递 `X-Forwarded-Proto: https`。

## 云南中烟 SSO 登录配置

在服务器上编辑 `/opt/zs2/backend/.env`，补齐以下配置：

```dotenv
APP_EXTERNAL_BASE_URL=https://yxcf-yzyy.ynzy-tobacco.com/zszngl
SSO_ENABLED=True
SSO_CLIENT_ID=zszngl
SSO_CLIENT_SECRET=<向信息管理科获取>
SSO_BASE_URL=<指南中的 base_url>
SSO_AUTHORIZE_URL=<base_url>/realms/yxcf/protocol/openid-connect/auth
SSO_TOKEN_URL=<base_url>/realms/yxcf/protocol/openid-connect/token
SSO_USERINFO_URL=<base_url>/realms/yxcf/protocol/openid-connect/userinfo
SSO_INTROSPECT_URL=<base_url>/realms/yxcf/protocol/openid-connect/token/introspect
SSO_REDIRECT_URI=https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/
SSO_SCOPE=openid email profile custom_scope
SSO_KC_IDP_HINT=wechat-work
CSRF_TRUSTED_ORIGINS=https://yxcf-yzyy.ynzy-tobacco.com
CORS_ALLOWED_ORIGINS=https://yxcf-yzyy.ynzy-tobacco.com
```

修改完成后重启服务：

```bash
systemctl restart zs2
```

SSO 回调地址：

```
https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/
```

外网访问地址：

```
https://yxcf-yzyy.ynzy-tobacco.com/zszngl/
```

安全提示：`SSO_CLIENT_SECRET` 仅保存在服务器 `.env` 中，不要提交到仓库。

## 外网代理/Nginx 配置（必须）

外网场景必须把 `/zszngl/` 反代到本机 9527 端口，并传递 HTTPS 标识：

```nginx
location /zszngl/ {
    proxy_pass http://172.24.69.125:9527;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## 前端环境变量建议

```dotenv
VITE_APP_BASE=/zszngl/
VITE_API_BASE=/zszngl
VITE_WS_BASE=
```

## 常见问题排查

- 资源 404（/assets/...）：通常是前端 base 未设置或外网代理未正确转发到本机。
- SSO 报 `origin_untrusted`：外网代理未传 `X-Forwarded-Proto: https`，或仍在用 http/IP 访问。
