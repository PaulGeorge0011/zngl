<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">除尘房巡检</h2>
        <p class="page-subtitle">日常巡检任务与状态</p>
      </div>
      <div class="header-actions">
        <router-link to="/safety/dustroom/records" class="action-btn">巡检记录</router-link>
        <router-link v-if="userStore.isSafetyOfficer" to="/safety/dustroom/admin" class="action-btn primary">管理配置</router-link>
      </div>
    </div>

    <!-- 角色标识 -->
    <div v-if="myRoles.length" class="role-badges">
      <span class="role-label">我的巡检角色：</span>
      <span v-for="r in myRoles" :key="r.role" class="role-badge">{{ r.role_display }}</span>
    </div>
    <div v-else-if="!loading" class="no-role-hint">
      <p>您暂未被分配除尘房巡检角色。</p>
      <p v-if="userStore.isSafetyOfficer">作为安全员，您可以前往 <router-link to="/safety/dustroom/admin">管理配置</router-link> 分配巡检人员。</p>
    </div>

    <!-- 今日任务概览 -->
    <div v-if="myRoles.length" class="section">
      <h3 class="section-title">今日巡检任务</h3>
      <div class="task-grid">
        <div v-for="task in tasks" :key="`${task.dust_room.id}-${task.role}`" class="task-card" :class="{ completed: task.completed, abnormal: task.has_abnormal }">
          <div class="task-room">{{ task.dust_room.name }}</div>
          <div class="task-role">{{ task.role_display }}</div>
          <div class="task-status">
            <template v-if="task.completed && task.has_abnormal">
              <span class="status-icon abnormal">⚠</span> 有异常
            </template>
            <template v-else-if="task.completed">
              <span class="status-icon done">✓</span> 已完成
            </template>
            <template v-else>
              <span class="status-icon pending">○</span> 待巡检
            </template>
          </div>
          <div class="task-action">
            <router-link
              v-if="!task.completed"
              :to="`/safety/dustroom/inspect/${task.dust_room.id}?template=${task.template_id}`"
              class="inspect-btn"
            >开始巡检</router-link>
            <router-link
              v-else-if="task.record_id"
              :to="`/safety/dustroom/records/${task.record_id}`"
              class="view-btn"
            >查看详情</router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- 全局概览 -->
    <div v-if="overview" class="section">
      <h3 class="section-title">今日整体进度</h3>
      <div class="overview-grid">
        <div v-for="c in overview.completion_by_role" :key="c.role" class="progress-card">
          <div class="progress-label">{{ c.role_display }}</div>
          <div class="progress-bar-wrap">
            <div class="progress-bar" :style="{ width: (c.expected ? c.completed / c.expected * 100 : 0) + '%' }" :class="c.completed >= c.expected ? 'full' : ''"></div>
          </div>
          <div class="progress-text">{{ c.completed }} / {{ c.expected }}</div>
        </div>
      </div>
      <div v-if="overview.abnormal_count > 0" class="abnormal-section">
        <h4 class="abnormal-title">今日异常项 ({{ overview.abnormal_count }})</h4>
        <div v-for="(a, i) in overview.recent_abnormals" :key="i" class="abnormal-item">
          <span class="abnormal-room">{{ a.room_name }}</span>
          <span class="abnormal-name">{{ a.item_name }}</span>
          <span class="abnormal-who">{{ a.inspector }} {{ a.time }}</span>
          <span v-if="a.remark" class="abnormal-remark">{{ a.remark }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-hint">加载中...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { dustroomApi } from '@/api/dustroom'
import type { TaskItem, OverviewData } from '@/api/dustroom'

const userStore = useUserStore()
const loading = ref(true)
const myRoles = ref<{ role: string; role_display: string }[]>([])
const tasks = ref<TaskItem[]>([])
const overview = ref<OverviewData | null>(null)

async function load() {
  loading.value = true
  try {
    const [tasksRes, overviewRes] = await Promise.all([
      dustroomApi.getMyTasks(),
      dustroomApi.getOverview(),
    ])
    myRoles.value = tasksRes.data.roles
    tasks.value = tasksRes.data.tasks
    overview.value = overviewRes.data
  } finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
.header-actions { display: flex; gap: 8px; }
.action-btn {
  padding: 7px 16px; border-radius: var(--radius-md); border: 1px solid var(--border-default);
  color: var(--text-secondary); text-decoration: none; font-size: 0.85rem;
}
.action-btn:hover { background: var(--bg-card); }
.action-btn.primary { background: var(--color-accent); color: #fff; border-color: var(--color-accent); }
.action-btn.primary:hover { opacity: 0.9; }

.role-badges { display: flex; align-items: center; gap: 8px; margin: 16px 0; flex-wrap: wrap; }
.role-label { font-size: 0.85rem; color: var(--text-muted); }
.role-badge {
  padding: 3px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;
  background: rgba(74, 158, 255, 0.12); color: var(--color-accent);
}
.no-role-hint {
  padding: 32px; text-align: center; color: var(--text-muted); font-size: 0.9rem;
  background: var(--bg-card); border-radius: var(--radius-md); margin: 16px 0;
}
.no-role-hint a { color: var(--color-accent); }

.section { margin-top: 24px; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; }

.task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.task-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 16px; display: flex; flex-direction: column; gap: 6px; transition: border-color 0.2s;
}
.task-card.completed { border-color: var(--color-healthy); }
.task-card.abnormal { border-color: var(--color-warning); }
.task-room { font-weight: 600; font-size: 0.95rem; color: var(--text-primary); }
.task-role { font-size: 0.8rem; color: var(--text-muted); }
.task-status { font-size: 0.85rem; margin-top: 4px; }
.status-icon.done { color: var(--color-healthy); }
.status-icon.abnormal { color: var(--color-warning); }
.status-icon.pending { color: var(--text-muted); }
.task-action { margin-top: 8px; }
.inspect-btn, .view-btn {
  display: inline-block; padding: 5px 14px; border-radius: var(--radius-md);
  font-size: 0.8rem; text-decoration: none;
}
.inspect-btn { background: var(--color-accent); color: #fff; }
.inspect-btn:hover { opacity: 0.9; }
.view-btn { border: 1px solid var(--border-default); color: var(--text-secondary); }
.view-btn:hover { background: var(--bg-card); }

.overview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.progress-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 14px;
}
.progress-label { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 8px; }
.progress-bar-wrap {
  height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden;
}
.progress-bar { height: 100%; background: var(--color-accent); border-radius: 3px; transition: width 0.3s; }
.progress-bar.full { background: var(--color-healthy); }
.progress-text { font-size: 0.8rem; color: var(--text-muted); margin-top: 6px; text-align: right; font-family: var(--font-mono); }

.abnormal-section { margin-top: 16px; }
.abnormal-title { font-size: 0.9rem; color: var(--color-warning); margin-bottom: 8px; }
.abnormal-item {
  display: flex; gap: 12px; align-items: center; padding: 8px 12px;
  background: var(--bg-card); border-radius: var(--radius-md); margin-bottom: 6px;
  font-size: 0.85rem; border-left: 3px solid var(--color-warning);
}
.abnormal-room { font-weight: 600; color: var(--text-primary); min-width: 80px; }
.abnormal-name { color: var(--text-secondary); flex: 1; }
.abnormal-who { color: var(--text-muted); font-size: 0.8rem; }
.abnormal-remark { color: var(--text-muted); font-size: 0.8rem; font-style: italic; }

.loading-hint { text-align: center; padding: 48px 0; color: var(--text-muted); }

@media (max-width: 640px) {
  .task-grid { grid-template-columns: 1fr; }
  .overview-grid { grid-template-columns: 1fr 1fr; }
}
</style>
