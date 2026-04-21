<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">上报隐患</h2>
        <p class="page-subtitle">拍照或上传图片记录安全隐患</p>
      </div>
    </div>

    <div class="form-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">

        <el-form-item label="隐患标题" prop="title">
          <el-input v-model="form.title" placeholder="简要描述隐患内容" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="详细描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="详细描述隐患的具体情况"
          />
        </el-form-item>

        <div class="form-row">
          <el-form-item label="隐患等级" prop="level" class="form-col">
            <el-radio-group v-model="form.level">
              <el-radio-button value="general">一般隐患</el-radio-button>
              <el-radio-button value="major">
                <span style="color: var(--color-alarm)">重大隐患</span>
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="所在区域" prop="location" class="form-col">
            <el-select v-model="form.location" placeholder="选择区域" style="width: 100%">
              <el-option
                v-for="loc in locations"
                :key="loc.id"
                :label="loc.name"
                :value="loc.id"
              />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="具体位置（补充）">
          <el-input v-model="form.location_detail" placeholder="如：3号烘丝机东侧" maxlength="200" />
        </el-form-item>

        <el-form-item label="现场照片（最多3张）">
          <div class="image-upload-area">
            <div v-for="(preview, idx) in previews" :key="idx" class="image-preview">
              <img :src="preview" alt="预览" />
              <button class="remove-btn" @click="removeImage(idx)">✕</button>
            </div>
            <label v-if="previews.length < 3" class="upload-trigger">
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                multiple
                capture="environment"
                style="display: none"
                @change="handleFileChange"
              />
              <div class="upload-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
              </div>
              <span>拍照 / 上传</span>
            </label>
          </div>
        </el-form-item>

        <div class="form-actions">
          <el-button @click="router.back()">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">提交上报</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { safetyApi } from '@/api/safety'
import type { Location } from '@/api/safety'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const locations = ref<Location[]>([])
const files = ref<File[]>([])
const previews = ref<string[]>([])

const form = reactive({
  title: '',
  description: '',
  level: 'general',
  location: null as number | null,
  location_detail: '',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入隐患标题', trigger: 'blur' }],
  description: [{ required: true, message: '请输入详细描述', trigger: 'blur' }],
  level: [{ required: true }],
  location: [{ required: true, message: '请选择所在区域', trigger: 'change' }],
}

onMounted(async () => {
  try {
    const { data } = await safetyApi.getLocations()
    locations.value = data
  } catch {
    ElMessage.error('加载区域列表失败')
  }
})

function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const newFiles = Array.from(input.files)
  const remaining = 3 - files.value.length
  const toAdd = newFiles.slice(0, remaining)
  toAdd.forEach((f) => {
    files.value.push(f)
    previews.value.push(URL.createObjectURL(f))
  })
  input.value = ''
}

function removeImage(idx: number) {
  URL.revokeObjectURL(previews.value[idx])
  files.value.splice(idx, 1)
  previews.value.splice(idx, 1)
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.title)
    fd.append('description', form.description)
    fd.append('level', form.level)
    fd.append('location', String(form.location))
    fd.append('location_detail', form.location_detail)
    files.value.forEach((f) => fd.append('images', f))

    await safetyApi.createHazard(fd)
    ElMessage.success('隐患上报成功')
    router.push('/safety/hazard')
  } catch {
    // Error shown by interceptor
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 28px 32px;
  max-width: 760px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-col { margin-bottom: 0; }

.image-upload-area {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.image-preview {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border-default);
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0,0,0,0.6);
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 0.65rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-trigger {
  width: 100px;
  height: 100px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 0.75rem;
  transition: border-color var(--transition-fast);
}

.upload-trigger:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
  padding-top: 20px;
  border-top: 1px solid var(--border-subtle);
}

@media (max-width: 960px) {
  .form-card {
    padding: 18px;
    max-width: none;
  }

  .form-row {
    grid-template-columns: 1fr;
    gap: 0;
  }
}

@media (max-width: 640px) {
  .image-preview,
  .upload-trigger {
    width: 88px;
    height: 88px;
  }

  .form-actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }
}
</style>
