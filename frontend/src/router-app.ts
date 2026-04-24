import { createRouter, createWebHistory } from 'vue-router'
import { getRouterBase } from '@/utils/appBase'

const router = createRouter({
  history: createWebHistory(getRouterBase()),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login/LoginView.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/m/checkin',
      name: 'MobileCheckin',
      component: () => import('@/views/mobile/CheckinView.vue'),
      meta: { public: true, title: '入场登记' },
    },
    {
      path: '/m/checkout',
      name: 'MobileCheckout',
      component: () => import('@/views/mobile/CheckoutView.vue'),
      meta: { public: true, title: '离场签退' },
    },
    {
      path: '/m/mezzanine-board',
      name: 'MezzanineBoard',
      component: () => import('@/views/mobile/MezzanineBoardView.vue'),
      meta: { public: true, title: '夹层施工现场' },
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
          meta: { title: '成品水分' },
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
          path: 'safety/dustroom',
          name: 'DustRoom',
          component: () => import('@/views/safety/DustRoomView.vue'),
          meta: { title: '除尘房巡检' },
        },
        {
          path: 'safety/dustroom/inspect/:roomId',
          name: 'DustRoomInspect',
          component: () => import('@/views/safety/DustRoomInspectView.vue'),
          meta: { title: '执行巡检' },
        },
        {
          path: 'safety/dustroom/records',
          name: 'DustRoomRecords',
          component: () => import('@/views/safety/DustRoomRecordsView.vue'),
          meta: { title: '巡检记录' },
        },
        {
          path: 'safety/dustroom/records/:id',
          name: 'DustRoomRecordDetail',
          component: () => import('@/views/safety/DustRoomRecordDetailView.vue'),
          meta: { title: '巡检详情' },
        },
        {
          path: 'safety/dustroom/admin',
          name: 'DustRoomAdmin',
          component: () => import('@/views/safety/DustRoomAdminView.vue'),
          meta: { title: '除尘房管理' },
        },
        {
          path: 'safety/nightshift',
          name: 'NightShift',
          component: () => import('@/views/safety/NightShiftView.vue'),
          meta: { title: '夜班监护检查' },
        },
        {
          path: 'safety/nightshift/inspect',
          name: 'NightShiftInspect',
          component: () => import('@/views/safety/NightShiftInspectView.vue'),
          meta: { title: '执行夜班检查' },
        },
        {
          path: 'safety/nightshift/records',
          name: 'NightShiftRecords',
          component: () => import('@/views/safety/NightShiftRecordsView.vue'),
          meta: { title: '夜班检查记录' },
        },
        {
          path: 'safety/nightshift/records/:id',
          name: 'NightShiftRecordDetail',
          component: () => import('@/views/safety/NightShiftRecordDetailView.vue'),
          meta: { title: '检查详情' },
        },
        {
          path: 'safety/nightshift/admin',
          name: 'NightShiftAdmin',
          component: () => import('@/views/safety/NightShiftAdminView.vue'),
          meta: { title: '夜班检查配置' },
        },
        {
          path: 'safety/knowledge',
          name: 'SafetyKnowledge',
          component: () => import('@/views/safety/SafetyKnowledgeView.vue'),
          meta: { title: '安全知识库' },
        },
        {
          path: 'safety/mezzanine',
          name: 'MezzanineManage',
          component: () => import('@/views/safety/MezzanineManageView.vue'),
          meta: { title: '夹层施工' },
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
        {
          path: 'safety/rectification',
          name: 'RectificationCenter',
          component: () => import('@/views/safety/RectificationCenterView.vue'),
          meta: { title: '整改中心' },
        },
        {
          path: 'safety/rectification/:id',
          name: 'RectificationDetail',
          component: () => import('@/views/safety/RectificationDetailView.vue'),
          meta: { title: '整改详情' },
        },
        {
          path: 'settings/users',
          name: 'UserManage',
          component: () => import('@/views/settings/UserManageView.vue'),
          meta: { title: '用户管理' },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  document.title = `${to.meta.title || ''} - 制丝车间智能管理系统`

  const { useUserStore } = await import('@/stores/user')
  const userStore = useUserStore()

  if (to.path === '/login') {
    if (userStore.isLoggedIn) {
      return '/dashboard'
    }

    try {
      const { usersApi } = await import('@/api/users')
      const { data } = await usersApi.me()
      userStore.setUser(data)
      return '/dashboard'
    } catch {
      return true
    }
  }

  if (to.meta.public) return true

  if (!userStore.isLoggedIn) {
    try {
      const { usersApi } = await import('@/api/users')
      const { data } = await usersApi.me()
      userStore.setUser(data)
    } catch {
      return '/login'
    }
  }

  return true
})

export default router
