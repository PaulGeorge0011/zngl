# 离线资源目录说明

这个目录中的内容会被 `pack.ps1` 原样打进 `zs2-deploy.tar.gz`，供 `CentOS 7` 离线部署使用。

请准备以下结构：

```text
offline-assets/
  python/
    Python-3.10.14.tgz
  rpms/
    base/
      *.rpm
    nginx/
      *.rpm
    postgresql15/
      *.rpm
```

建议原则：

- 所有 RPM 都提前在可联网机器下载好
- 版本尽量来自同一套 CentOS 7 / EL7 源，避免依赖冲突
- `base` 中至少要包含 `rsync`，因为安装脚本会用它同步到 `/opt/zs2`
