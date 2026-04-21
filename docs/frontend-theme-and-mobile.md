# 前端主题与移动端说明

## 1. 主题切换

当前系统已支持全局 `light` / `dark` 双主题。

实现位置：

- `frontend/src/composables/useTheme.ts`
- `frontend/src/styles/global.scss`
- `frontend/src/components/layout/TopHeader.vue`
- `frontend/src/views/login/LoginView.vue`

规则：

- 主题状态写入 `localStorage`，键名为 `zs2-theme-mode`
- 初次进入时，若本地无记录，则跟随系统 `prefers-color-scheme`
- `html.dark` 控制 Element Plus 暗色变量
- 自定义界面颜色统一使用全局 CSS 变量，不直接写死颜色

开发要求：

- 新增页面必须优先使用 `var(--bg-*)`、`var(--text-*)`、`var(--color-*)`
- 不要只对暗色主题做样式，必须同时检查亮色主题
- 避免在组件里大量写行内颜色值，除非是业务态强调色

## 2. 移动端适配

当前主应用已完成一轮移动端适配，覆盖登录页、主框架、仪表盘、设备、监控、质量、安全、隐患、知识库和用户管理等核心页面。

实现位置：

- `frontend/src/composables/useShell.ts`
- `frontend/src/components/layout/AppLayout.vue`
- `frontend/src/components/layout/TopHeader.vue`
- `frontend/src/components/layout/SidebarNav.vue`
- `frontend/src/styles/global.scss`

规则：

- `960px` 作为平板/手机主断点
- `640px` 作为小屏手机断点
- 手机端导航改为抽屉式侧边栏
- 高信息密度表格优先保留桌面列结构，并通过横向滚动兼容手机
- 表单页和详情页优先改为单列布局

开发要求：

- 新页面至少补两档媒体查询：`@media (max-width: 960px)` 和 `@media (max-width: 640px)`
- 桌面页若包含表格，必须确认手机下是否需要 `min-width + overflow-x`
- 桌面页若包含并排卡片、图表或操作区，手机下应改为单列或换行
- 弹窗、抽屉、分页、按钮组都要在窄屏下检查是否拥挤

## 3. 后续建议

如果后续还要继续优化移动体验，建议按下面顺序推进：

1. 把高频表格页补成“表格 / 卡片”双视图切换
2. 针对图表页补真实手机尺寸下的高度和 tooltip 交互微调
3. 统一梳理各页面中文文案编码和断句表现
