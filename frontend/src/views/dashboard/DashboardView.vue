<template>
  <div class="page-container">
    <!-- Hero Header -->
    <div class="hero-header">
      <div class="hero-title-group">
        <h1 class="hero-title">制丝车间智能管理系统</h1>
        <p class="hero-subtitle">INTELLIGENT SILK PRODUCTION MANAGEMENT SYSTEM</p>
      </div>
      <div class="hero-status">
        <div class="status-indicator" :class="systemStatus"></div>
        <span class="status-text">{{ systemStatusText }}</span>
      </div>
    </div>

    <!-- Module Cards -->
    <div class="module-grid">
      <router-link to="/equipment" class="module-card equipment-card card-stagger">
        <div class="module-header">
          <div class="module-icon">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="14" cy="14" r="5"/>
              <path d="M14 2v4M14 22v4M2 14h4M22 14h4M5 5l3 3M20 20l3 3M5 23l3-3M20 8l3-3"/>
            </svg>
          </div>
          <div class="module-title-group">
            <h3 class="module-title">设备管理</h3>
            <p class="module-subtitle">Equipment Management</p>
          </div>
        </div>
        <div class="module-stats">
          <div class="module-stat">
            <span class="module-stat-value">{{ stats.equipment_total }}</span>
            <span class="module-stat-label">设备总数</span>
          </div>
          <div class="module-stat">
            <span class="module-stat-value">{{ stats.equipment_running }}</span>
            <span class="module-stat-label">运行中</span>
          </div>
          <div class="module-stat">
            <span class="module-stat-value">{{ stats.equipment_fault }}</span>
            <span class="module-stat-label">故障</span>
          </div>
        </div>
        <div class="module-footer">
          <span class="module-link">进入模块</span>
          <span class="module-arrow">→</span>
        </div>
      </router-link>

      <router-link to="/quality" class="module-card quality-card card-stagger" style="animation-delay: 80ms">
        <div class="module-header">
          <div class="module-icon">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2L4 7v8c0 6.5 4.5 11 10 12 5.5-1 10-5.5 10-12V7L14 2z"/>
              <polyline points="9,14 12,17 19,10"/>
            </svg>
          </div>
          <div class="module-title-group">
            <h3 class="module-title">质量管理</h3>
            <p class="module-subtitle">Quality Management</p>
          </div>
        </div>
        <div class="module-features">
          <div class="feature-tag">成品水分监控</div>
          <div class="feature-tag">Excel批量导入</div>
          <div class="feature-tag">趋势分析</div>
        </div>
        <div class="module-footer">
          <span class="module-link">进入模块</span>
          <span class="module-arrow">→</span>
        </div>
      </router-link>

      <router-link to="/safety" class="module-card safety-card card-stagger" style="animation-delay: 160ms">
        <div class="module-header">
          <div class="module-icon">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2L4 7v8c0 6.5 4.5 11 10 12 5.5-1 10-5.5 10-12V7L14 2z"/>
            </svg>
          </div>
          <div class="module-title-group">
            <h3 class="module-title">安全管理</h3>
            <p class="module-subtitle">Safety Management</p>
          </div>
        </div>
        <div class="module-features">
          <div class="feature-tag">安全巡检</div>
          <div class="feature-tag">隐患排查</div>
          <div class="feature-tag">知识库</div>
        </div>
        <div class="module-footer">
          <span class="module-link">进入模块</span>
          <span class="module-arrow">→</span>
        </div>
      </router-link>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div
        v-for="(stat, i) in statsCards"
        :key="stat.label"
        class="stat-card card-stagger"
        :class="stat.variant"
        :style="{ animationDelay: i * 60 + 'ms' }"
      >
        <div class="stat-icon" v-html="stat.icon"></div>
        <div class="stat-content">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
        <div class="stat-accent"></div>
      </div>
    </div>

    <!-- Quick Links -->
    <div class="quick-section">
      <h3 class="section-title">快速操作</h3>
      <div class="quick-grid">
        <router-link to="/monitoring" class="quick-card card-stagger">
          <div class="quick-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <polyline points="2,16 6,12 10,14 15,6 19,10 22,4"/>
              <line x1="2" y1="20" x2="22" y2="20"/>
            </svg>
          </div>
          <span class="quick-label">实时监控</span>
          <span class="quick-arrow">&rarr;</span>
        </router-link>
        <router-link to="/monitoring/alarms" class="quick-card card-stagger">
          <div class="quick-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 2L2 19h20L12 2z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <circle cx="12" cy="16" r="0.5" fill="currentColor"/>
            </svg>
          </div>
          <span class="quick-label">查看报警</span>
          <span class="quick-arrow">&rarr;</span>
        </router-link>
        <router-link to="/quality" class="quick-card card-stagger">
          <div class="quick-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18M9 3v18"/>
            </svg>
          </div>
          <span class="quick-label">质量数据</span>
          <span class="quick-arrow">&rarr;</span>
        </router-link>
        <router-link to="/safety/knowledge" class="quick-card card-stagger">
          <div class="quick-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
          </div>
          <span class="quick-label">安全知识库</span>
          <span class="quick-arrow">&rarr;</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { monitoringApi } from '@/api/monitoring'
import type { DashboardStats } from '@/types'

const stats = ref<DashboardStats>({
  equipment_total: 0,
  equipment_running: 0,
  equipment_fault: 0,
  alarms_active: 0,
  alarms_today: 0,
  readings_today: 0,
})

const systemStatus = computed(() => {
  if (stats.value.equipment_fault > 0) return 'fault'
  if (stats.value.alarms_active > 0) return 'warning'
  return 'normal'
})

const systemStatusText = computed(() => {
  if (stats.value.equipment_fault > 0) return '系统故障'
  if (stats.value.alarms_active > 0) return '系统警告'
  return '系统正常'
})

const statsCards = computed(() => [
  {
    label: '设备总数',
    value: stats.value.equipment_total,
    variant: 'info',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="4"/><path d="M11 1v3M11 18v3M1 11h3M18 11h3M3.9 3.9l2.1 2.1M15.9 15.9l2.1 2.1M3.9 18.1l2.1-2.1M15.9 6.1l2.1-2.1"/></svg>`,
  },
  {
    label: '运行中',
    value: stats.value.equipment_running,
    variant: 'healthy',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="4,12 9,17 18,5"/></svg>`,
  },
  {
    label: '故障设备',
    value: stats.value.equipment_fault,
    variant: stats.value.equipment_fault > 0 ? 'alarm' : 'neutral',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="9"/><line x1="11" y1="7" x2="11" y2="11"/><circle cx="11" cy="14.5" r="0.5" fill="currentColor"/></svg>`,
  },
  {
    label: '活跃报警',
    value: stats.value.alarms_active,
    variant: stats.value.alarms_active > 0 ? 'warning' : 'neutral',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M11 2L1 19h20L11 2z"/><line x1="11" y1="9" x2="11" y2="13"/><circle cx="11" cy="16" r="0.5" fill="currentColor"/></svg>`,
  },
  {
    label: '今日报警',
    value: stats.value.alarms_today,
    variant: 'neutral',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="16" height="15" rx="2"/><line x1="3" y1="9" x2="19" y2="9"/><line x1="8" y1="2" x2="8" y2="5"/><line x1="14" y1="2" x2="14" y2="5"/></svg>`,
  },
  {
    label: '今日采集量',
    value: stats.value.readings_today.toLocaleString(),
    variant: 'info',
    icon: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="12" width="3" height="7" rx="0.5"/><rect x="9.5" y="8" width="3" height="11" rx="0.5"/><rect x="16" y="3" width="3" height="16" rx="0.5"/></svg>`,
  },
])

async function fetchStats() {
  try {
    const { data } = await monitoringApi.dashboard()
    stats.value = data
  } catch {
    // API 可能未连接
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.hero-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
  padding: 32px;
  background: linear-gradient(135deg, rgba(0, 255, 163, 0.05), rgba(0, 163, 255, 0.05));
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  position: relative;
  overflow: hidden;
}

.hero-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--color-accent), var(--color-info), transparent);
}

.hero-title {
  font-family: var(--font-display);
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  letter-spacing: 0.02em;
}

.hero-subtitle {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
  letter-spacing: 0.1em;
  margin: 0;
}

.hero-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-indicator.normal {
  background: var(--color-healthy);
  box-shadow: 0 0 12px var(--color-healthy);
}

.status-indicator.warning {
  background: var(--color-warning);
  box-shadow: 0 0 12px var(--color-warning);
}

.status-indicator.fault {
  background: var(--color-alarm);
  box-shadow: 0 0 12px var(--color-alarm);
}

.status-text {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-secondary);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.module-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 28px;
  text-decoration: none;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  overflow: hidden;
  transition: all var(--transition-normal);
}

.module-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  transition: all var(--transition-normal);
}

.equipment-card::before { background: linear-gradient(90deg, var(--color-info), transparent); }
.quality-card::before { background: linear-gradient(90deg, var(--color-healthy), transparent); }
.safety-card::before { background: linear-gradient(90deg, var(--color-warning), transparent); }

.module-card:hover {
  border-color: var(--border-default);
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.module-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.module-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.equipment-card .module-icon {
  background: var(--color-info-dim);
  color: var(--color-info);
}

.quality-card .module-icon {
  background: var(--color-healthy-dim);
  color: var(--color-healthy);
}

.safety-card .module-icon {
  background: var(--color-warning-dim);
  color: var(--color-warning);
}

.module-title {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.module-subtitle {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  margin: 0;
}

.module-stats {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--radius-md);
}

.module-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.module-stat-value {
  font-family: var(--font-mono);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
}

.module-stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.module-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feature-tag {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.module-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.module-link {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.module-arrow {
  font-size: 1.2rem;
  color: var(--color-accent);
  opacity: 0;
  transform: translateX(-8px);
  transition: all var(--transition-fast);
}

.module-card:hover .module-arrow {
  opacity: 1;
  transform: translateX(0);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  position: relative;
  overflow: hidden;
  transition: all var(--transition-normal);
}

.stat-card:hover {
  border-color: var(--border-default);
  transform: translateY(-2px);
}

.stat-accent {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
}

.stat-card.info .stat-accent { background: linear-gradient(90deg, var(--color-info), transparent); }
.stat-card.healthy .stat-accent { background: linear-gradient(90deg, var(--color-healthy), transparent); }
.stat-card.warning .stat-accent { background: linear-gradient(90deg, var(--color-warning), transparent); }
.stat-card.alarm .stat-accent { background: linear-gradient(90deg, var(--color-alarm), transparent); }
.stat-card.neutral .stat-accent { background: linear-gradient(90deg, var(--text-muted), transparent); opacity: 0.3; }

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card.info .stat-icon { background: var(--color-info-dim); color: var(--color-info); }
.stat-card.healthy .stat-icon { background: var(--color-healthy-dim); color: var(--color-healthy); }
.stat-card.warning .stat-icon { background: var(--color-warning-dim); color: var(--color-warning); }
.stat-card.alarm .stat-icon { background: var(--color-alarm-dim); color: var(--color-alarm); }
.stat-card.neutral .stat-icon { background: rgba(255,255,255,0.04); color: var(--text-muted); }

.stat-content {
  flex: 1;
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--text-primary);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 16px;
  letter-spacing: 0.02em;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.quick-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  text-decoration: none;
  color: var(--text-secondary);
  transition: all var(--transition-normal);
}

.quick-card:hover {
  border-color: var(--color-accent);
  color: var(--text-primary);
  transform: translateX(4px);
}

.quick-icon {
  color: var(--color-accent);
  opacity: 0.7;
}

.quick-card:hover .quick-icon {
  opacity: 1;
}

.quick-label {
  flex: 1;
  font-weight: 500;
  font-size: 0.9rem;
}

.quick-arrow {
  font-size: 1.1rem;
  opacity: 0;
  transform: translateX(-4px);
  transition: all var(--transition-fast);
}

.quick-card:hover .quick-arrow {
  opacity: 1;
  transform: translateX(0);
}

@media (max-width: 960px) {
  .hero-header {
    margin-bottom: 24px;
    padding: 22px 18px;
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
  }

  .hero-title {
    font-size: 1.7rem;
  }

  .module-grid {
    grid-template-columns: 1fr;
    gap: 14px;
    margin-bottom: 24px;
  }

  .module-card {
    padding: 20px;
  }

  .module-stats {
    gap: 16px;
    flex-wrap: wrap;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }

  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .hero-title {
    font-size: 1.42rem;
    line-height: 1.2;
  }

  .hero-subtitle {
    font-size: 0.68rem;
    letter-spacing: 0.06em;
  }

  .hero-status {
    width: 100%;
    justify-content: center;
  }

  .module-header {
    gap: 12px;
  }

  .module-icon {
    width: 48px;
    height: 48px;
  }

  .module-title {
    font-size: 1.15rem;
  }

  .stats-grid,
  .quick-grid {
    grid-template-columns: 1fr;
  }

  .stat-card,
  .quick-card {
    padding: 16px;
  }
}
</style>
