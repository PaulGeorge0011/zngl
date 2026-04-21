<template>
  <el-drawer
    v-model="visible"
    :title="isEdit ? '编辑用户' : '新建用户'"
    size="480px"
    :before-close="handleClose"
    direction="rtl"
  >
    <el-tabs v-model="activeTab">
      <!-- 标签页一：基本信息 -->
      <el-tab-pane label="基本信息" name="basic">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="姓名" prop="name">
            <el-input v-model="form.name" placeholder="请输入姓名" />
          </el-form-item>

          <el-form-item label="用户名（登录账号）" prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              :disabled="isEdit"
            />
          </el-form-item>

          <el-form-item label="工号" prop="employee_id">
            <el-input v-model="form.employee_id" placeholder="如：EMP001（可选）" />
          </el-form-item>

          <el-form-item label="联系电话" prop="phone">
            <el-input v-model="form.phone" placeholder="如：13800138000（可选）" />
          </el-form-item>

          <el-form-item v-if="!isEdit" label="初始密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="至少6位"
              show-password
            />
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 标签页二：角色与权限 -->
      <el-tab-pane label="角色与权限" name="role">
        <el-form label-position="top">
          <el-form-item label="角色">
            <el-radio-group v-model="form.role" style="flex-direction: column; gap: 12px; align-items: flex-start">
              <el-radio value="safety_officer">安全员 — 可分派隐患、验证整改、管理用户</el-radio>
              <el-radio value="team_leader">班组长 — 可提交整改</el-radio>
              <el-radio value="worker">员工 — 可上报隐患</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 重置密码（仅编辑模式） -->
          <template v-if="isEdit">
            <el-divider>重置密码</el-divider>
            <el-form-item label="新密码">
              <el-input
                v-model="newPassword"
                type="password"
                placeholder="至少6位"
                show-password
                style="width: 240px"
              />
            </el-form-item>
            <el-button
              :loading="resetting"
              :disabled="newPassword.length < 6"
              @click="handleResetPassword"
            >
              重置密码
            </el-button>
          </template>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { userManageApi, type ManagedUser } from '@/api/users'

const props = defineProps<{
  modelValue: boolean
  user?: ManagedUser | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.user)
const activeTab = ref('basic')
const formRef = ref<FormInstance>()
const saving = ref(false)
const resetting = ref(false)
const newPassword = ref('')

const form = reactive({
  name: '',
  username: '',
  employee_id: '',
  phone: '',
  password: '',
  role: 'worker' as string,
})

const rules = computed<FormRules>(() => ({
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  ...(isEdit.value ? {} : {
    password: [
      { required: true, message: '请输入初始密码', trigger: 'blur' },
      { min: 6, message: '密码至少6位', trigger: 'blur' },
    ],
  }),
}))

// 打开抽屉时初始化表单
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      activeTab.value = 'basic'
      newPassword.value = ''
      if (props.user) {
        form.name = props.user.name
        form.username = props.user.username
        form.employee_id = props.user.employee_id
        form.phone = props.user.phone
        form.password = ''
        form.role = props.user.role
      } else {
        Object.assign(form, { name: '', username: '', employee_id: '', phone: '', password: '', role: 'worker' })
      }
    }
  }
)

function handleClose() {
  visible.value = false
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    activeTab.value = 'basic'
    return
  }

  saving.value = true
  try {
    if (isEdit.value && props.user) {
      await userManageApi.update(props.user.id, {
        name: form.name,
        role: form.role,
        employee_id: form.employee_id,
        phone: form.phone,
      })
      ElMessage.success('用户信息已更新')
    } else {
      await userManageApi.create({
        username: form.username,
        name: form.name,
        password: form.password,
        role: form.role,
        employee_id: form.employee_id,
        phone: form.phone,
      })
      ElMessage.success('用户创建成功')
    }
    visible.value = false
    emit('saved')
  } catch {
    // 错误由 http 拦截器展示
  } finally {
    saving.value = false
  }
}

async function handleResetPassword() {
  if (!props.user) return
  resetting.value = true
  try {
    await userManageApi.resetPassword(props.user.id, newPassword.value)
    ElMessage.success('密码已重置')
    newPassword.value = ''
  } catch {
    // 错误由 http 拦截器展示
  } finally {
    resetting.value = false
  }
}
</script>
