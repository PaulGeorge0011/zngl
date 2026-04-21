<template>
  <div class="page-container">
    <div class="page-header">
      <el-button text @click="router.back()">
        ← 返回列表
      </el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="6" animated />
    </div>

    <template v-else-if="hazard">
      <!-- 基本信息 -->
      <div class="info-card">
        <div class="info-header">
          <div class="info-title-row">
            <el-tag :type="hazard.level === 'major' ? 'danger' : 'info'" size="large">
              {{ hazard.level_display }}
            </el-tag>
            <h2 class="hazard-title">{{ hazard.title }}</h2>
            <span class="status-tag" :class="`status-${hazard.status}`">
              {{ hazard.status_display }}
            </span>
          </div>
          <p class="hazard-desc">{{ hazard.description }}</p>
        </div>
        <div class="info-meta-grid">
          <div class="meta-item"><span class="meta-label">区域</span><span>{{ hazard.location_name }}</span></div>
          <div v-if="hazard.location_detail" class="meta-item"><span class="meta-label">具体位置</span><span>{{ hazard.location_detail }}</span></div>
          <div class="meta-item"><span class="meta-label">上报人</span><span>{{ hazard.reporter.display_name }}</span></div>
          <div class="meta-item"><span class="meta-label">上报时间</span><span>{{ hazard.created_at }}</span></div>
          <div v-if="hazard.assignee" class="meta-item"><span class="meta-label">整改责任人</span><span>{{ hazard.assignee.display_name }}</span></div>
        </div>
      </div>

      <!-- 上报图片 -->
      <div v-if="reportImages.length" class="section-card">
        <h3 class="section-title">现场照片</h3>
        <div class="image-grid">
          <img
            v-for="img in reportImages"
            :key="img.id"
            :src="img.image_url"
            class="hazard-image"
            @click="previewImage(img.image_url)"
          />
        </div>
      </div>

      <!-- 流转时间线 -->
      <div class="section-card">
        <h3 class="section-title">处理进展</h3>
        <el-timeline>
          <el-timeline-item
            :timestamp="hazard.created_at"
            placement="top"
            type="primary"
          >
            <div class="timeline-content">
              <span class="tl-action">隐患上报</span>
              <span class="tl-actor">{{ hazard.reporter.display_name }}</span>
            </div>
          </el-timeline-item>
          <el-timeline-item
            v-if="hazard.assigned_at"
            :timestamp="hazard.assigned_at"
            placement="top"
            type="warning"
          >
            <div class="timeline-content">
              <span class="tl-action">分派整改</span>
              <span class="tl-actor">{{ hazard.assigned_by?.display_name }} → {{ hazard.assignee?.display_name }}</span>
            </div>
          </el-timeline-item>
          <el-timeline-item
            v-if="hazard.fixed_at"
            :timestamp="hazard.fixed_at"
            placement="top"
            type="warning"
          >
            <div class="timeline-content">
              <span class="tl-action">提交整改</span>
              <span class="tl-actor">{{ hazard.assignee?.display_name }}</span>
              <p class="tl-remark">{{ hazard.fix_description }}</p>
            </div>
          </el-timeline-item>
          <el-timeline-item
            v-if="hazard.verified_at"
            :timestamp="hazard.verified_at"
            placement="top"
            :type="hazard.status === 'closed' ? 'success' : 'danger'"
          >
            <div class="timeline-content">
              <span class="tl-action">{{ hazard.status === 'closed' ? '验证通过' : '驳回整改' }}</span>
              <span class="tl-actor">{{ hazard.verified_by?.display_name }}</span>
              <p v-if="hazard.verify_remark" class="tl-remark">{{ hazard.verify_remark }}</p>
            </div>
          </el-timeline-item>
          <!-- Rejected state node: shows after rejection, before re-fix -->
          <el-timeline-item
            v-if="hazard.status === 'rejected'"
            timestamp="待整改"
            placement="top"
            type="danger"
          >
            <div class="timeline-content">
              <span class="tl-action">已驳回，等待责任人重新整改</span>
              <span class="tl-actor">{{ hazard.assignee?.display_name }}</span>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>

      <!-- 整改图片 -->
      <div v-if="fixImages.length" class="section-card">
        <h3 class="section-title">整改照片</h3>
        <div class="image-grid">
          <img
            v-for="img in fixImages"
            :key="img.id"
            :src="img.image_url"
            class="hazard-image"
            @click="previewImage(img.image_url)"
          />
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-bar" v-if="showActionBar">
        <!-- 安全员分派 -->
        <el-button
          v-if="isSafetyOfficer && hazard.status === 'pending'"
          type="primary"
          @click="showAssignDialog = true"
        >
          分派责任人
        </el-button>

        <!-- 整改责任人提交整改（fixing 或 rejected 状态均可）
             NOTE: 'rejected' IS a distinct persistent status per STATUS_CHOICES.
             The flow is: verifying → rejected (via verify/reject action),
             then rejected → fixing (when assignee re-submits via hazard_fix). -->
        <el-button
          v-if="isAssignee && (hazard.status === 'fixing' || hazard.status === 'rejected')"
          type="warning"
          @click="showFixDialog = true"
        >
          提交整改
        </el-button>

        <!-- 安全员验证 -->
        <template v-if="isSafetyOfficer && hazard.status === 'verifying'">
          <el-button type="success" @click="handleVerify('approve')">验证通过</el-button>
          <el-button type="danger" @click="showRejectDialog = true">驳回整改</el-button>
        </template>
      </div>
    </template>

    <!-- 分派弹窗 -->
    <el-dialog v-model="showAssignDialog" title="分派整改责任人" width="400px">
      <el-select v-model="assigneeId" placeholder="选择责任人" style="width: 100%">
        <el-option
          v-for="u in teamLeaders"
          :key="u.id"
          :label="u.display_name"
          :value="u.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="showAssignDialog = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="handleAssign">确认分派</el-button>
      </template>
    </el-dialog>

    <!-- 整改弹窗 -->
    <el-dialog v-model="showFixDialog" title="提交整改" width="500px">
      <el-input
        v-model="fixDescription"
        type="textarea"
        :rows="4"
        placeholder="描述整改措施和结果"
      />
      <div class="fix-image-upload" style="margin-top: 12px;">
        <label class="upload-btn">
          <input type="file" accept="image/*" multiple style="display:none" @change="handleFixImages" />
          上传整改照片（可选，最多3张）
        </label>
        <div class="fix-previews">
          <img v-for="(p, i) in fixPreviews" :key="i" :src="p" class="fix-thumb" />
        </div>
      </div>
      <template #footer>
        <el-button @click="showFixDialog = false">取消</el-button>
        <el-button type="primary" :loading="actionLoading" @click="handleFix">提交整改</el-button>
      </template>
    </el-dialog>

    <!-- 驳回弹窗 -->
    <el-dialog v-model="showRejectDialog" title="驳回整改" width="400px">
      <el-input v-model="rejectRemark" type="textarea" :rows="3" placeholder="填写驳回原因（可选）" />
      <template #footer>
        <el-button @click="showRejectDialog = false">取消</el-button>
        <el-button type="danger" :loading="actionLoading" @click="handleVerify('reject')">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 图片预览 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="[previewUrl]"
      @close="previewVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { safetyApi } from '@/api/safety'
import { usersApi } from '@/api/users'
import { useUserStore } from '@/stores/user'
import type { HazardDetail } from '@/api/safety'
import type { UserInfo } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const hazard = ref<HazardDetail | null>(null)
const loading = ref(true)
const teamLeaders = ref<UserInfo[]>([])

// Action state
const showAssignDialog = ref(false)
const showFixDialog = ref(false)
const showRejectDialog = ref(false)
const actionLoading = ref(false)
const assigneeId = ref<number | null>(null)
const fixDescription = ref('')
const fixFiles = ref<File[]>([])
const fixPreviews = ref<string[]>([])
const rejectRemark = ref('')

// Image preview
const previewVisible = ref(false)
const previewUrl = ref('')

const isSafetyOfficer = computed(() => userStore.isSafetyOfficer)
const isAssignee = computed(() =>
  hazard.value?.assignee?.id === userStore.user?.id
)
const showActionBar = computed(() =>
  (isSafetyOfficer.value && ['pending', 'verifying'].includes(hazard.value?.status || '')) ||
  (isAssignee.value && ['fixing', 'rejected'].includes(hazard.value?.status || ''))
)

const reportImages = computed(() => hazard.value?.images.filter(i => i.phase === 'report') || [])
const fixImages = computed(() => hazard.value?.images.filter(i => i.phase === 'fix') || [])

onMounted(async () => {
  const id = Number(route.params.id)
  try {
    const { data } = await safetyApi.getHazard(id)
    hazard.value = data
  } catch {
    ElMessage.error('加载隐患详情失败')
  } finally {
    loading.value = false
  }

  if (userStore.isSafetyOfficer) {
    try {
      const { data } = await usersApi.list('班组长')
      teamLeaders.value = data
    } catch {}
  }
})

onUnmounted(() => {
  fixPreviews.value.forEach(url => URL.revokeObjectURL(url))
})

function previewImage(url: string) {
  previewUrl.value = url
  previewVisible.value = true
}

async function handleAssign() {
  if (!assigneeId.value) { ElMessage.warning('请选择责任人'); return }
  actionLoading.value = true
  try {
    const { data } = await safetyApi.assignHazard(hazard.value!.id, assigneeId.value)
    hazard.value = data
    showAssignDialog.value = false
    ElMessage.success('分派成功')
  } finally {
    actionLoading.value = false
  }
}

function handleFixImages(e: Event) {
  // Revoke previous object URLs before replacing
  fixPreviews.value.forEach(url => URL.revokeObjectURL(url))
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const newFiles = Array.from(input.files).slice(0, 3)
  fixFiles.value = newFiles
  fixPreviews.value = newFiles.map(f => URL.createObjectURL(f))
}

async function handleFix() {
  if (!fixDescription.value.trim()) { ElMessage.warning('请填写整改说明'); return }
  actionLoading.value = true
  try {
    const fd = new FormData()
    fd.append('fix_description', fixDescription.value.trim())
    fixFiles.value.forEach(f => fd.append('images', f))
    const { data } = await safetyApi.fixHazard(hazard.value!.id, fd)
    hazard.value = data
    showFixDialog.value = false
    ElMessage.success('整改提交成功')
  } finally {
    actionLoading.value = false
  }
}

async function handleVerify(action: 'approve' | 'reject') {
  actionLoading.value = true
  try {
    const remark = action === 'reject' ? rejectRemark.value : undefined
    const { data } = await safetyApi.verifyHazard(hazard.value!.id, action, remark)
    hazard.value = data
    showRejectDialog.value = false
    ElMessage.success(action === 'approve' ? '验证通过' : '已驳回')
  } finally {
    actionLoading.value = false
  }
}
</script>

<style scoped>
.info-card, .section-card, .action-bar {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  margin-bottom: 16px;
}

.info-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.hazard-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
}

.hazard-desc {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.7;
  margin: 0 0 16px;
}

.info-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px 24px;
}

.meta-item {
  display: flex;
  gap: 8px;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.meta-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 16px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.image-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hazard-image {
  width: 120px;
  height: 120px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  cursor: pointer;
  border: 1px solid var(--border-default);
  transition: opacity var(--transition-fast);
}

.hazard-image:hover { opacity: 0.85; }

.timeline-content {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.tl-action {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.tl-actor {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.tl-remark {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 6px 0 0;
  white-space: pre-wrap;
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.status-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 3px;
}

.status-pending   { background: var(--color-info-dim); color: var(--color-accent); }
.status-fixing    { background: var(--color-warning-dim); color: var(--color-warning); }
.status-verifying { background: rgba(160, 100, 255, 0.15); color: #a064ff; }
.status-closed    { background: var(--color-healthy-dim); color: var(--color-healthy); }
.status-rejected  { background: var(--color-alarm-dim); color: var(--color-alarm); }

.upload-btn {
  display: inline-block;
  padding: 6px 14px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.fix-previews { display: flex; gap: 8px; margin-top: 8px; }
.fix-thumb { width: 64px; height: 64px; object-fit: cover; border-radius: 4px; }

.loading-state { padding: 40px; }

@media (max-width: 960px) {
  .info-card,
  .section-card,
  .action-bar {
    padding: 16px;
  }

  .info-title-row,
  .timeline-content,
  .action-bar {
    flex-wrap: wrap;
  }

  .info-meta-grid {
    grid-template-columns: 1fr 1fr;
  }

  .hazard-image {
    width: calc(50% - 6px);
    height: 140px;
  }
}

@media (max-width: 640px) {
  .info-title-row,
  .meta-item,
  .timeline-content,
  .action-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .info-meta-grid {
    grid-template-columns: 1fr;
  }

  .hazard-image {
    width: 100%;
    height: 180px;
  }

  .fix-previews {
    flex-wrap: wrap;
  }

  .loading-state {
    padding: 24px 0;
  }
}
</style>
