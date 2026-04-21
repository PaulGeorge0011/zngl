<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ isEdit ? '编辑设备' : '新增设备' }}</h2>
        <p class="page-subtitle">{{ isEdit ? '修改设备基础信息' : '添加新的监控设备' }}</p>
      </div>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <div class="form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        label-position="left"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="form.name" placeholder="如：切丝机-01" />
        </el-form-item>
        <el-form-item label="设备编号" prop="code">
          <el-input v-model="form.code" placeholder="如：QSJ-001" />
        </el-form-item>
        <el-form-item label="安装地点" prop="location">
          <el-input v-model="form.location" placeholder="如：制丝车间A区" />
        </el-form-item>
        <el-form-item label="设备状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="运行中" value="running" />
            <el-option label="停机" value="stopped" />
            <el-option label="故障" value="fault" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="设备说明（选填）" />
        </el-form-item>

        <div class="form-actions">
          <el-button @click="$router.back()">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '创建设备' }}
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { equipmentApi } from '@/api/equipment'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const isEdit = computed(() => !!route.params.id)

const form = ref({
  name: '',
  code: '',
  location: '',
  status: 'stopped' as 'running' | 'stopped' | 'fault',
  description: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入设备编号', trigger: 'blur' }],
  location: [{ required: true, message: '请输入安装地点', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

async function loadEquipment() {
  if (!isEdit.value) return
  try {
    const { data } = await equipmentApi.get(Number(route.params.id))
    form.value = {
      name: data.name,
      code: data.code,
      location: data.location,
      status: data.status,
      description: data.description,
    }
  } catch {
    ElMessage.error('加载设备信息失败')
    router.back()
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      await equipmentApi.update(Number(route.params.id), form.value)
      ElMessage.success('设备信息已更新')
    } else {
      await equipmentApi.create(form.value)
      ElMessage.success('设备创建成功')
    }
    router.push('/equipment')
  } finally {
    submitting.value = false
  }
}

onMounted(loadEquipment)
</script>

<style scoped>
.form-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 32px;
  max-width: 640px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-subtle);
}

@media (max-width: 960px) {
  .form-card {
    max-width: none;
    padding: 20px 18px;
  }

  .form-card :deep(.el-form-item__label) {
    width: auto !important;
  }
}

@media (max-width: 640px) {
  .form-actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }
}
</style>
