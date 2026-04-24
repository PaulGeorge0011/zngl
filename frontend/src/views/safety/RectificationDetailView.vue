<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header">
      <div>
        <h2 class="page-title">
          整改工单 #{{ id }}
          <el-tag v-if="order" :type="severityTagType(order.severity)" size="small" style="margin-left: 8px">
            {{ order.severity_display }}
          </el-tag>
          <span v-if="order?.overdue" class="overdue-badge">已逾期</span>
        </h2>
        <p class="page-subtitle" v-if="order">
          来源：{{ order.source_type_display }}
          <span class="dot">·</span>
          提交：{{ formatDateTime(order.created_at) }}
        </p>
      </div>
      <el-button @click="router.back()" plain>返回</el-button>
    </div>

    <div v-if="order" class="layout">
      <!-- 左：详情内容 -->
      <div class="main-col">
        <!-- 状态时间线 -->
        <div class="card">
          <div class="card-title">流转状态</div>
          <el-steps :active="statusStep" finish-status="success" align-center>
            <el-step title="待分派" />
            <el-step title="整改中" />
            <el-step title="待验证" />
            <el-step title="已闭环" />
          </el-steps>
        </div>

        <!-- 问题信息 -->
        <div class="card">
          <div class="card-title">问题信息</div>
          <div class="info-grid">
            <div><label>标题</label><div>{{ order.title }}</div></div>
            <div><label>位置</label><div>{{ order.location_text || '—' }}</div></div>
            <div><label>提交人</label><div>{{ order.submitter.display_name }}</div></div>
            <div><label>当前状态</label>
              <div><span class="status-tag" :class="`status-${order.status}`">{{ order.status_display }}</span></div>
            </div>
          </div>
          <div class="block">
            <label>问题描述</label>
            <div class="block-text">{{ order.description }}</div>
          </div>
          <div class="block" v-if="issueImages.length">
            <label>问题现场</label>
            <div class="image-row">
              <el-image
                v-for="img in issueImages" :key="img.id"
                :src="img.image_url" :preview-src-list="issueImages.map(i => i.image_url)"
                fit="cover" class="thumb"
              />
            </div>
          </div>
        </div>

        <!-- 验证人分派信息 -->
        <div class="card" v-if="order.verifier_assigned_at">
          <div class="card-title">验证人分派</div>
          <div class="info-grid">
            <div><label>验证人</label><div>{{ order.verifier?.display_name || '—' }}</div></div>
            <div><label>分派人</label><div>{{ order.verifier_assigner?.display_name || '—' }}</div></div>
            <div><label>分派时间</label><div>{{ formatDateTime(order.verifier_assigned_at) }}</div></div>
          </div>
        </div>

        <!-- 整改信息 -->
        <div class="card" v-if="order.assigned_at">
          <div class="card-title">整改进度</div>
          <div class="info-grid">
            <div><label>责任人</label><div>{{ order.assignee?.display_name || '—' }}</div></div>
            <div><label>分派人</label><div>{{ order.assigner?.display_name || '—' }}</div></div>
            <div><label>分派时间</label><div>{{ formatDateTime(order.assigned_at) }}</div></div>
            <div><label>整改期限</label>
              <div :class="{ 'overdue-text': order.overdue }">{{ formatDateTime(order.deadline) }}</div>
            </div>
            <div v-if="order.rectified_at"><label>整改提交</label><div>{{ formatDateTime(order.rectified_at) }}</div></div>
            <div v-if="order.reject_count > 0"><label>被驳回</label><div>{{ order.reject_count }} 次</div></div>
          </div>
          <div class="block" v-if="order.rectify_description">
            <label>整改说明</label>
            <div class="block-text">{{ order.rectify_description }}</div>
          </div>
          <div class="block" v-if="rectifyImages.length">
            <label>整改佐证</label>
            <div class="image-row">
              <el-image
                v-for="img in rectifyImages" :key="img.id"
                :src="img.image_url" :preview-src-list="rectifyImages.map(i => i.image_url)"
                fit="cover" class="thumb"
              />
            </div>
          </div>
        </div>

        <!-- 验证信息 -->
        <div class="card" v-if="order.verified_at">
          <div class="card-title">验证结果</div>
          <div class="info-grid">
            <div><label>验证人</label><div>{{ order.verifier?.display_name || '—' }}</div></div>
            <div><label>验证时间</label><div>{{ formatDateTime(order.verified_at) }}</div></div>
            <div><label>验证结果</label>
              <div>
                <el-tag :type="order.status === 'closed' ? 'success' : 'warning'" size="small">
                  {{ order.status === 'closed' ? '通过' : '驳回（已退回整改）' }}
                </el-tag>
              </div>
            </div>
          </div>
          <div class="block" v-if="order.verify_remark">
            <label>验证意见</label>
            <div class="block-text">{{ order.verify_remark }}</div>
          </div>
        </div>

        <!-- 操作日志 -->
        <div class="card">
          <div class="card-title">操作日志</div>
          <el-timeline>
            <el-timeline-item
              v-for="log in order.logs" :key="log.id"
              :timestamp="formatDateTime(log.created_at)"
              :type="logTimelineType(log.action)"
            >
              <div class="log-line">
                <strong>{{ log.action_display }}</strong>
                <span v-if="log.operator">· {{ log.operator.display_name }}</span>
              </div>
              <div class="log-remark" v-if="log.remark">{{ log.remark }}</div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>

      <!-- 右：操作面板 -->
      <div class="side-col">
        <div class="card">
          <div class="card-title">操作</div>

          <!-- 分派验证人（未闭环/未取消随时可指派） -->
          <div
            v-if="canAssignOrVerify && order.status !== 'closed' && order.status !== 'cancelled'"
            class="action-block"
          >
            <div class="action-label">{{ order.verifier ? '改派验证人' : '分派验证人' }}</div>
            <el-select
              v-model="verifierForm.verifierId" placeholder="选择验证人" filterable clearable
              style="width: 100%; margin-bottom: 8px"
            >
              <el-option
                v-for="u in users" :key="u.id"
                :label="`${u.display_name || u.username} (${u.username})`" :value="u.id"
              />
            </el-select>
            <el-input
              v-model="verifierForm.remark" type="textarea" :rows="2"
              placeholder="备注（选填）"
              style="margin-bottom: 8px"
            />
            <el-button
              type="primary" plain style="width: 100%"
              :disabled="!verifierForm.verifierId" @click="onAssignVerifier"
            >{{ order.verifier ? '确认改派' : '确认分派验证人' }}</el-button>
          </div>

          <!-- 分派责任人 -->
          <div v-if="order.status === 'pending' && canAssignOrVerify" class="action-block">
            <div class="action-label">分派整改责任人</div>
            <el-select
              v-model="assignForm.assigneeId" placeholder="选择责任人" filterable clearable
              style="width: 100%; margin-bottom: 8px"
            >
              <el-option
                v-for="u in users" :key="u.id"
                :label="`${u.display_name || u.username} (${u.username})`" :value="u.id"
              />
            </el-select>
            <el-date-picker
              v-model="assignForm.deadline" type="datetime"
              placeholder="整改期限（不填使用默认）"
              style="width: 100%; margin-bottom: 8px"
              format="YYYY-MM-DD HH:mm"
              value-format="YYYY-MM-DDTHH:mm:00"
            />
            <el-input
              v-model="assignForm.remark" type="textarea" :rows="2"
              placeholder="备注（选填）"
            />
            <el-button
              type="primary" style="width: 100%; margin-top: 8px"
              :disabled="!assignForm.assigneeId" @click="onAssign"
            >确认分派</el-button>
          </div>

          <!-- 提交整改 -->
          <div v-if="order.status === 'fixing' && isMyAssignment" class="action-block">
            <div class="action-label">提交整改</div>
            <el-input
              v-model="rectifyForm.description" type="textarea" :rows="3"
              placeholder="请描述整改情况"
              style="margin-bottom: 8px"
            />
            <el-upload
              v-model:file-list="rectifyForm.fileList"
              action="#" :auto-upload="false" :limit="3"
              list-type="picture-card"
              accept="image/*"
            >
              <el-icon><Plus /></el-icon>
            </el-upload>
            <el-button
              type="success" style="width: 100%; margin-top: 8px"
              :disabled="!rectifyForm.description.trim()" @click="onSubmitRectify"
            >提交整改</el-button>
          </div>

          <!-- 验证 -->
          <div v-if="order.status === 'verifying' && canAssignOrVerify && !isMyAssignment" class="action-block">
            <div class="action-label">验证整改</div>
            <el-input
              v-model="verifyForm.remark" type="textarea" :rows="2"
              placeholder="验证意见（选填）"
              style="margin-bottom: 8px"
            />
            <div style="display: flex; gap: 8px">
              <el-button type="success" style="flex: 1" @click="onVerify('approve')">通过</el-button>
              <el-button type="warning" style="flex: 1" @click="onVerify('reject')">驳回</el-button>
            </div>
          </div>

          <!-- 取消 — 仅安全员（重操作，保留正式权限） -->
          <div v-if="order.status !== 'closed' && order.status !== 'cancelled' && isOfficer" class="action-block">
            <div class="action-label">取消工单</div>
            <el-input
              v-model="cancelRemark" type="textarea" :rows="2"
              placeholder="必填：取消原因"
              style="margin-bottom: 8px"
            />
            <el-button
              type="danger" plain style="width: 100%"
              :disabled="!cancelRemark.trim()" @click="onCancel"
            >取消工单</el-button>
          </div>

          <div
            v-if="!hasAnyAction"
            class="muted"
          >当前状态下你没有可执行的操作</div>
        </div>

        <div class="card" v-if="order.source_snapshot && Object.keys(order.source_snapshot).length">
          <div class="card-title">来源信息</div>
          <pre class="snapshot">{{ JSON.stringify(order.source_snapshot, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { UploadUserFile } from 'element-plus'
import { rectificationApi } from '@/api/rectification'
import type { RectDetail } from '@/api/rectification'
import { usersApi } from '@/api/users'
import type { UserInfo } from '@/stores/user'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const id = Number(route.params.id)
const loading = ref(false)
const order = ref<RectDetail | null>(null)
const users = ref<UserInfo[]>([])

const assignForm = reactive({
  assigneeId: undefined as number | undefined,
  deadline: '',
  remark: '',
})

const verifierForm = reactive({
  verifierId: undefined as number | undefined,
  remark: '',
})

const rectifyForm = reactive({
  description: '',
  fileList: [] as UploadUserFile[],
})

const verifyForm = reactive({ remark: '' })
const cancelRemark = ref('')

const isOfficer = computed(() => userStore.user?.role === 'safety_officer')

const isMyAssignment = computed(() => {
  return order.value?.assignee?.id === userStore.user?.id
})

// 安全员 或 当前工单的指派验证人 都有分派/验证权限
const canAssignOrVerify = computed(() => {
  if (isOfficer.value) return true
  const uid = userStore.user?.id
  return !!uid && order.value?.verifier?.id === uid
})

// 右侧操作面板是否至少有一个可执行操作
const hasAnyAction = computed(() => {
  if (!order.value) return false
  const st = order.value.status
  if (st === 'closed' || st === 'cancelled') return false
  // 分派验证人 + 分派/改派责任人 + 验证 — 安全员或指派验证人可操作
  if (canAssignOrVerify.value) return true
  // 提交整改 — 仅当前责任人
  if (st === 'fixing' && isMyAssignment.value) return true
  return false
})

const issueImages = computed(() => order.value?.images.filter(i => i.phase === 'issue') ?? [])
const rectifyImages = computed(() => order.value?.images.filter(i => i.phase === 'rectify') ?? [])

const statusStep = computed(() => {
  if (!order.value) return 0
  switch (order.value.status) {
    case 'pending': return 0
    case 'fixing': return 1
    case 'verifying': return 2
    case 'closed': return 4
    case 'cancelled': return 0
    default: return 0
  }
})

onMounted(async () => {
  await Promise.allSettled([fetchOrder(), fetchUsers()])
})

async function fetchOrder() {
  loading.value = true
  try {
    const { data } = await rectificationApi.get(id)
    order.value = data
  } catch (e) {
    ElMessage.error('加载工单失败')
  } finally {
    loading.value = false
  }
}

async function fetchUsers() {
  try {
    const { data } = await usersApi.list()
    users.value = data
  } catch {
    users.value = []
  }
}

async function onAssign() {
  if (!assignForm.assigneeId) return
  try {
    const { data } = await rectificationApi.assign(id, {
      assignee_id: assignForm.assigneeId,
      deadline: assignForm.deadline || undefined,
      remark: assignForm.remark,
    })
    order.value = data
    ElMessage.success('已分派')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '分派失败')
  }
}

async function onAssignVerifier() {
  if (!verifierForm.verifierId) return
  try {
    const { data } = await rectificationApi.assignVerifier(id, {
      verifier_id: verifierForm.verifierId,
      remark: verifierForm.remark,
    })
    order.value = data
    verifierForm.verifierId = undefined
    verifierForm.remark = ''
    ElMessage.success('验证人已分派，短信通知已发送')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '分派验证人失败')
  }
}

async function onSubmitRectify() {
  if (!rectifyForm.description.trim()) return
  const fd = new FormData()
  fd.append('rectify_description', rectifyForm.description)
  for (const f of rectifyForm.fileList) {
    if (f.raw) fd.append('images', f.raw)
  }
  try {
    const { data } = await rectificationApi.submitRectify(id, fd)
    order.value = data
    rectifyForm.description = ''
    rectifyForm.fileList = []
    ElMessage.success('已提交，等待验证')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '提交失败')
  }
}

async function onVerify(action: 'approve' | 'reject') {
  try {
    const { data } = await rectificationApi.verify(id, action, verifyForm.remark)
    order.value = data
    verifyForm.remark = ''
    ElMessage.success(action === 'approve' ? '验证通过，工单已闭环' : '已驳回，退回整改人')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '验证失败')
  }
}

async function onCancel() {
  if (!cancelRemark.value.trim()) return
  try {
    await ElMessageBox.confirm('确认取消该整改工单？此操作不可逆', '取消工单', { type: 'warning' })
  } catch {
    return
  }
  try {
    const { data } = await rectificationApi.cancel(id, cancelRemark.value)
    order.value = data
    cancelRemark.value = ''
    ElMessage.success('工单已取消')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '取消失败')
  }
}

function severityTagType(s: string): 'info' | 'warning' | 'danger' {
  if (s === 'critical') return 'danger'
  if (s === 'major') return 'warning'
  return 'info'
}

function formatDateTime(s: string | null): string {
  if (!s) return '—'
  return s.replace('T', ' ').slice(0, 16)
}

function logTimelineType(action: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  if (action === 'create') return 'info'
  if (action === 'assign' || action === 'reassign') return 'primary'
  if (action === 'submit_rectify') return 'warning'
  if (action === 'verify_pass') return 'success'
  if (action === 'verify_reject') return 'danger'
  if (action === 'auto_overdue') return 'danger'
  if (action === 'cancel') return 'info'
  return 'info'
}
</script>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
}

.main-col, .side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 18px 20px;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 14px;
  color: var(--text-primary);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 24px;
  margin-bottom: 14px;
}

.info-grid > div { display: flex; flex-direction: column; gap: 4px; }
.info-grid label { font-size: 0.78rem; color: var(--text-secondary); }
.info-grid > div > div { font-size: 0.92rem; color: var(--text-primary); }

.block { margin-top: 12px; }
.block label { font-size: 0.78rem; color: var(--text-secondary); display: block; margin-bottom: 6px; }
.block-text {
  font-size: 0.92rem;
  color: var(--text-primary);
  white-space: pre-wrap;
  background: var(--bg-card-elevated, #fafafa);
  padding: 10px 12px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
}

.image-row { display: flex; gap: 8px; flex-wrap: wrap; }
.thumb { width: 110px; height: 110px; border-radius: 4px; }

.action-block { margin-bottom: 20px; }
.action-block:last-child { margin-bottom: 0; }
.action-label { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 8px; font-weight: 500; }

.muted { color: var(--text-secondary); font-size: 0.85rem; text-align: center; padding: 12px 0; }

.status-tag { font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 3px; }
.status-pending  { background: var(--color-info-dim); color: var(--color-accent); }
.status-fixing   { background: var(--color-warning-dim); color: var(--color-warning); }
.status-verifying { background: rgba(160, 100, 255, 0.15); color: #a064ff; }
.status-closed   { background: var(--color-healthy-dim); color: var(--color-healthy); }
.status-cancelled { background: #f0f0f0; color: #999; }

.overdue-badge {
  margin-left: 10px;
  background: var(--color-alarm-dim);
  color: var(--color-alarm);
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: 600;
}

.overdue-text { color: var(--color-alarm); font-weight: 600; }

.dot { margin: 0 6px; color: var(--text-tertiary, #ccc); }

.log-line { font-size: 0.88rem; color: var(--text-primary); }
.log-remark { font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px; }

.snapshot {
  font-size: 0.78rem;
  background: var(--bg-card-elevated, #fafafa);
  padding: 10px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  overflow-x: auto;
  margin: 0;
}

@media (max-width: 960px) {
  .layout { grid-template-columns: 1fr; }
  .info-grid { grid-template-columns: 1fr; }
}
</style>
