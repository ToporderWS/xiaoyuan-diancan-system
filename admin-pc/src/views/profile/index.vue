<template>
  <div class="co-page">
    <div class="co-profile">
      <!-- 资料卡 -->
      <div class="co-card co-profile__left">
        <div class="co-page-header">
          <div class="co-page-title">个人中心</div>
        </div>

        <div class="profile-avatar">
          <img class="profile-avatar__img" :src="avatarUrl" alt="avatar" />
          <input
            ref="fileInput"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            style="display: none"
            @change="onFileChange"
          />
          <el-button size="small" :loading="uploading" @click="pickFile">修改头像</el-button>
          <div class="co-muted" style="font-size: 12px; margin-top: 6px">
            支持 jpg / jpeg / png / webp，≤ 2MB
          </div>
        </div>

        <el-descriptions :column="1" border size="small" style="margin-top: 16px">
          <el-descriptions-item label="管理员账号">
            {{ info.admin_name || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="真实姓名">{{ info.real_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="头像文件">{{ info.avatar || '—' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ info.created_at || '—' }}</el-descriptions-item>
        </el-descriptions>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-top: 14px"
          title="管理员账号（admin_name）不提供修改入口"
          description="原需求未授权修改账号，如需变更请由数据库维护人员操作。"
        />

        <el-button style="margin-top: 16px; width: 100%" type="danger" plain @click="logout">
          退出登录
        </el-button>
      </div>

      <!-- 密码与说明 -->
      <div class="co-profile__right">
        <div class="co-card">
          <div class="co-page-header">
            <div class="co-page-title">修改密码</div>
          </div>
          <el-form
            ref="pwdFormRef"
            :model="pwdForm"
            :rules="pwdRules"
            label-width="100px"
            style="max-width: 460px"
          >
            <el-form-item label="原密码" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password
                        placeholder="请输入原密码" />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password
                        placeholder="不少于 6 位" />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirm">
              <el-input v-model="pwdForm.confirm" type="password" show-password
                        placeholder="请再次输入新密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="submitPwd">确认修改</el-button>
            </el-form-item>
          </el-form>
          <el-alert
            type="warning"
            :closable="false"
            show-icon
            title="修改密码后需要重新登录"
            description="V1.0 不提供服务端 JWT 黑名单，退出登录为客户端清除 Token 行为。"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { authApi } from '@/api'
import { clearToken } from '@/api/request'
import { imageUrl } from '@/config'
import { useAdminStore } from '@/stores/admin'

const MAX_SIZE = 2 * 1024 * 1024
const ALLOWED_EXT = ['jpg', 'jpeg', 'png', 'webp']

const router = useRouter()
const adminStore = useAdminStore()

const info = ref({})
const uploading = ref(false)
const saving = ref(false)
const fileInput = ref(null)
const pwdFormRef = ref(null)

const pwdForm = reactive({ old_password: '', new_password: '', confirm: '' })

const avatarUrl = computed(() => imageUrl(info.value.avatar || adminStore.avatar))

const pwdRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 64, message: '新密码长度 6-64 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, cb) => {
        if (value !== pwdForm.new_password) cb(new Error('两次输入的新密码不一致'))
        else cb()
      },
      trigger: 'blur'
    }
  ]
}

async function load() {
  try {
    info.value = await authApi.info()
    adminStore.persistProfile(info.value)
  } catch (e) {
    info.value = adminStore.profile || {}
  }
}

function pickFile() {
  if (fileInput.value) fileInput.value.click()
}

async function onFileChange(event) {
  const file = event.target.files && event.target.files[0]
  if (fileInput.value) fileInput.value.value = ''
  if (!file) return
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  if (!ALLOWED_EXT.includes(ext)) {
    ElMessage.error('仅支持 jpg / jpeg / png / webp 格式图片')
    return
  }
  if (file.size > MAX_SIZE) {
    ElMessage.error('图片大小不能超过 2MB')
    return
  }
  uploading.value = true
  try {
    const data = await authApi.uploadAvatar(file)
    ElMessage.success('头像已更新')
    info.value = Object.assign({}, info.value, { avatar: data.avatar })
    adminStore.persistProfile(Object.assign({}, adminStore.profile, { avatar: data.avatar }))
  } catch (e) {
    // 提示由拦截器处理
  } finally {
    uploading.value = false
  }
}

function submitPwd() {
  pwdFormRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await authApi.updatePwd({
        old_password: pwdForm.old_password,
        new_password: pwdForm.new_password
      })
      ElMessage.success('密码修改成功，请重新登录')
      setTimeout(() => {
        clearToken()
        adminStore.token = ''
        adminStore.persistProfile(null)
        router.replace('/login')
      }, 900)
    } catch (e) {
      // 提示由拦截器处理
    } finally {
      saving.value = false
    }
  })
}

function logout() {
  ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
    confirmButtonText: '确定退出',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(async () => {
      await adminStore.logout()
      ElMessage.success('已退出登录')
      router.replace('/login')
    })
    .catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.co-profile {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

@media (max-width: 1100px) {
  .co-profile {
    grid-template-columns: minmax(0, 1fr);
  }
}

.profile-avatar {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.profile-avatar__img {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid #fdeceb;
  background-color: #fff1f0;
}
</style>
