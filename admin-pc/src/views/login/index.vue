<template>
  <div class="login">
    <!-- ==================== 左：品牌 + 校园食堂场景 ==================== -->
    <section class="login__stage">
      <div class="login__content">
        <header class="login__brand">
          <img class="login__brand-logo" src="/brand-logo.svg" alt="校园点餐管理系统" />
          <div class="login__brand-text">
            <h1 class="login__brand-title">校园点餐<em>管理系统</em></h1>
            <p class="login__brand-sub">Campus Dining Management System</p>
          </div>
        </header>

        <p class="login__slogan">
          <span class="login__slogan-text">让校园点餐<em>更简单</em>，更高效</span>
          <svg class="login__slogan-underline" viewBox="0 0 300 12" preserveAspectRatio="none" aria-hidden="true">
            <path
              d="M3 9.1C58 3.6 132 1.4 300 3.4"
              stroke="#e8453c"
              stroke-width="2.4"
              stroke-linecap="round"
              fill="none"
              vector-effect="non-scaling-stroke"
            />
          </svg>
        </p>

        <ul class="login__features">
          <li class="login__feature">菜品管理</li>
          <li class="login__feature">订单调度</li>
          <li class="login__feature">数据统计</li>
          <li class="login__feature">系统配置</li>
        </ul>
      </div>

      <!-- 校园食堂场景主视觉：本地静态资源 + 等比裁切（不拉伸） -->
      <div class="login__hero">
        <img class="login__hero-img" src="/login/login-hero.jpg" alt="校园食堂用餐场景" />
        <span class="login__hero-veil" aria-hidden="true"></span>
      </div>
    </section>

    <!-- ==================== 右：管理员登录 ==================== -->
    <section class="login__panel">
      <div class="login__card">
        <div class="login__card-head">
          <img class="login__card-logo" src="/brand-logo.svg" alt="校园点餐管理系统" />
          <h2 class="login__card-title">校园点餐管理系统</h2>
          <p class="login__card-sub">管理员后台 · 数据可视化 · 订单调度 · 系统管理</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          @keyup.enter="onSubmit"
        >
          <el-form-item prop="admin_name">
            <template #label>
              <span class="login__label">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="8.4" r="3.6" />
                  <path d="M4.8 20c.9-3.6 3.7-5.6 7.2-5.6s6.3 2 7.2 5.6" />
                </svg>
                管理员账号
              </span>
            </template>
            <el-input
              v-model="form.admin_name"
              placeholder="请输入管理员账号"
              clearable
              autocomplete="username"
              :prefix-icon="User"
            />
          </el-form-item>
          <el-form-item prop="password">
            <template #label>
              <span class="login__label">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <rect x="4.6" y="10.2" width="14.8" height="9.6" rx="2.4" />
                  <path d="M8.4 10.2V7.6a3.6 3.6 0 0 1 7.2 0v2.6" />
                </svg>
                密码
              </span>
            </template>
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              show-password
              autocomplete="current-password"
              :prefix-icon="Lock"
            />
          </el-form-item>

          <div class="login__options">
            <el-checkbox v-model="remember">记住账号</el-checkbox>
            <button type="button" class="login__link" @click="onForget">忘记密码？</button>
          </div>

          <el-button
            class="login__submit"
            type="primary"
            :loading="loading"
            @click="onSubmit"
          >
            登录
            <el-icon class="login__submit-icon"><Right /></el-icon>
          </el-button>
        </el-form>

        <p class="login__foot">
          校园点餐管理系统 v1.0.0
          <span>© 2026 让校园餐饮管理更简单</span>
        </p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { Lock, Right, User } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAdminStore } from '@/stores/admin'

const router = useRouter()
const route = useRoute()
const adminStore = useAdminStore()

// 「记住账号」只保存登录名，绝不保存密码（纯前端体验项）
const REMEMBER_KEY = 'admin_remember_name'

const formRef = ref(null)
const loading = ref(false)
const remember = ref(false)
const form = reactive({ admin_name: '', password: '' })

const rules = {
  admin_name: [
    { required: true, message: '请输入管理员账号', trigger: 'blur' },
    { min: 3, max: 50, message: '账号长度 3-50 位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度 6-64 位', trigger: 'blur' }
  ]
}

onMounted(() => {
  try {
    const saved = localStorage.getItem(REMEMBER_KEY)
    if (saved) {
      form.admin_name = saved
      remember.value = true
    }
  } catch (e) {
    // 隐私模式下 localStorage 不可用时静默降级
  }
})

function saveRemember(name) {
  try {
    if (remember.value && name) localStorage.setItem(REMEMBER_KEY, name)
    else localStorage.removeItem(REMEMBER_KEY)
  } catch (e) {
    // 同上
  }
}

function onForget() {
  ElMessageBox.alert(
    '管理员账号由系统初始化脚本创建，V1.0 不提供自助重置密码。\n\n' +
      '请联系食堂系统管理员，或在服务器执行以下命令重置：\n' +
      'python scripts/init_admin.py --admin-name <账号> --password <新密码> --force',
    '忘记密码',
    { confirmButtonText: '知道了', customClass: 'login-forget-box' }
  ).catch(() => {})
}

function onSubmit() {
  if (!formRef.value) return
  formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const name = (form.admin_name || '').trim()
      await adminStore.login({ admin_name: name, password: form.password })
      await adminStore.fetchInfo()
      saveRemember(name)
      ElMessage.success('登录成功')
      const redirect = route.query.redirect ? decodeURIComponent(route.query.redirect) : '/dashboard'
      router.replace(redirect)
    } catch (e) {
      // 错误提示由 Axios 拦截器统一处理
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
/* ========================= 布局骨架 =========================
   左右比例 60.6% / 39.4%，与参考图一致（实测参考图接缝在 60.6%）
   ========================================================== */
.login {
  display: flex;
  height: 100vh;
  min-width: 320px;
  overflow: hidden;
  background-color: #fffbf8;
}

/* ---------------- 左侧：品牌 + 场景 ---------------- */
.login__stage {
  position: relative;
  flex: 0 0 60.6%;
  max-width: 60.6%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #fffdfb 0%, #fff9f5 56%, #fff6f0 100%);
}

.login__content {
position: relative;
  z-index: 2;
  flex: 0 0 auto;
  padding: clamp(16px, 4.4vh, 48px) clamp(26px, 4.9vw, 96px) 0;
}

/* 品牌头 */
.login__brand {
  display: flex;
  align-items: center;
  gap: clamp(10px, 0.95vw, 18px);
}

.login__brand-logo {
width: clamp(40px, 3.4vw, 64px);
  height: clamp(40px, 3.4vw, 64px);
  border-radius: 26%;
  flex-shrink: 0;
}

.login__brand-title {
margin: 0;
  font-size: clamp(19px, 2.09vw, 38px);
  font-weight: 800;
  letter-spacing: clamp(1px, 0.26vw, 5px);
  color: #2b2521;
  line-height: 1.15;
}

.login__brand-title em {
  font-style: normal;
  color: #e8453c;
}

.login__brand-sub {
margin: clamp(2px, 0.35vh, 4px) 0 0;
  font-size: clamp(9px, 0.66vw, 12.5px);
  letter-spacing: 0.6px;
  color: #c8c0ba;
}

/* slogan + 红色手绘下划线 */
.login__slogan {
position: relative;
  display: inline-block;
  margin: clamp(7px, 1.5vh, 17px) 0 0;
  padding-bottom: clamp(5px, 0.8vh, 9px);
  font-size: clamp(14px, 1.25vw, 24px);
  font-weight: 600;
  letter-spacing: clamp(0.6px, 0.14vw, 2.2px);
  color: #6b625c;
}

.login__slogan-text em {
  font-style: normal;
  color: #e8453c;
}

.login__slogan-underline {
position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: clamp(4px, 0.42vw, 8px);
}


/* 能力标签：一行轻量文字（原四色圆形图标已移除，避免与主视觉图片争夺注意力） */
.login__features {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  margin: clamp(7px, 1.05vh, 13px) 0 0;
  padding: 0;
  list-style: none;
}

.login__feature {
  display: inline-flex;
  align-items: center;
  font-size: clamp(10px, 0.74vw, 13.5px);
  font-weight: 400;
  letter-spacing: 0.6px;
  color: #a69c94;
  white-space: nowrap;
}

/* 分隔点：纯 CSS 生成（不用胶囊、不用图标） */
.login__feature + .login__feature::before {
  content: '';
  width: 3px;
  height: 3px;
  margin: 0 clamp(9px, 0.8vw, 15px);
  border-radius: 50%;
  background-color: #d8cec6;
}


/* 场景图：占满剩余高度，object-fit 等比裁切（绝不拉伸） */
.login__hero {
position: relative;
  flex: 1 1 auto;
  min-height: 150px;
  margin-top: clamp(6px, 1.05vh, 13px);
  overflow: hidden;
}

.login__hero-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 50% 100%;
  display: block;
}

/* 顶部融入底色，消除图片与品牌区的硬边 */
.login__hero-veil {
position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: clamp(30px, 2.8vw, 56px);
  background: linear-gradient(
    180deg,
    #fffbf8 0%,
    rgba(255, 251, 248, 0.86) 14%,
    rgba(255, 251, 248, 0.42) 46%,
    rgba(255, 251, 248, 0.12) 74%,
    rgba(255, 251, 248, 0) 100%
  );
  pointer-events: none;
}

/* ---------------- 右侧：登录面板 ---------------- */
.login__panel {
  flex: 1 1 39.4%;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(20px, 2.6vh, 32px) clamp(18px, 2.8vw, 56px);
  background:
    radial-gradient(70% 54% at 18% 6%, rgba(255, 255, 255, 0.72) 0%, rgba(255, 255, 255, 0) 70%),
    linear-gradient(162deg, #fdeae7 0%, #fbe1de 52%, #f8d5d1 100%);
}

/* 卡片宽度 = 视口宽 33.6%（参考图实测），内部留白同步等比 */
.login__card {
width: min(33.6vw, 660px);
  min-width: 336px;
  padding: clamp(26px, 3.6vh, 42px) clamp(26px, 4vw, 78px) clamp(18px, 2.4vh, 26px);
  background-color: #ffffff;
  border-radius: clamp(14px, 1.15vw, 22px);
  box-shadow: 0 14px 38px rgba(168, 106, 88, 0.12);
}

.login__card-head {
display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: clamp(14px, 2.6vh, 30px);
}

.login__card-logo {
width: clamp(42px, 2.9vw, 56px);
  height: clamp(42px, 2.9vw, 56px);
  border-radius: 26%;
}

.login__card-title {
margin: clamp(10px, 1.8vh, 20px) 0 0;
  font-size: clamp(20px, 2vw, 36px);
  font-weight: 800;
  letter-spacing: clamp(0.5px, 0.12vw, 2px);
  color: #2b2521;
  line-height: 1.15;
}

.login__card-sub {
margin: clamp(6px, 1vh, 12px) 0 0;
  font-size: clamp(10.5px, 0.83vw, 16px);
  letter-spacing: 0.3px;
  color: #a9a09a;
}

/* ---------------- 表单视觉 ---------------- */
.login__label {
  display: inline-flex;
  align-items: center;
  gap: clamp(4px, 0.4vw, 8px);
  font-size: clamp(12px, 0.88vw, 17px);
  font-weight: 600;
  color: #4a423c;
}

.login__label svg {
  width: clamp(12px, 0.86vw, 16px);
  height: clamp(12px, 0.86vw, 16px);
  color: #b1a8a2;
}

/* 与参考图一致：标签前不显示必填星号（表单校验规则完全不受影响） */
.login :deep(.el-form-item__label::before) {
  display: none;
}

.login :deep(.el-form-item) {
margin-bottom: clamp(12px, 2.2vh, 22px);
}

.login :deep(.el-form-item__label) {
padding-bottom: clamp(4px, 0.6vh, 7px);
  line-height: 1.4;
}

.login :deep(.el-input__wrapper) {
height: clamp(40px, 2.4vw, 50px);
  border-radius: clamp(8px, 0.62vw, 12px);
  background-color: #f9f6f4;
  box-shadow: 0 0 0 1px #efe8e3 inset;
  transition: box-shadow 0.15s, background-color 0.15s;
}

.login :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #e2d8d1 inset;
}

.login :deep(.el-input__wrapper.is-focus) {
  background-color: #ffffff;
  box-shadow: 0 0 0 1px #e8453c inset, 0 0 0 3px rgba(232, 69, 60, 0.1);
}

.login :deep(.el-input__inner) {
  font-size: clamp(13px, 0.92vw, 17px);
}

.login :deep(.el-input__prefix),
.login :deep(.el-input__suffix) {
  color: #b8afa9;
}

/* 关键：屏蔽浏览器自动填充的蓝色底，未聚焦态保持自然的暖浅灰 */
.login :deep(.el-input__inner:-webkit-autofill),
.login :deep(.el-input__inner:-webkit-autofill:hover),
.login :deep(.el-input__inner:-webkit-autofill:focus) {
  -webkit-box-shadow: 0 0 0 1000px #f9f6f4 inset !important;
  -webkit-text-fill-color: #2b2521 !important;
  caret-color: #2b2521;
  transition: background-color 9999s ease-in-out 0s;
}

.login :deep(.el-input__inner::selection) {
  background: rgba(232, 69, 60, 0.16);
}

.login__options {
display: flex;
  align-items: center;
  justify-content: space-between;
  margin: clamp(2px, 0.5vh, 6px) 0 clamp(10px, 2vh, 20px);
}

.login__options :deep(.el-checkbox__label) {
  font-size: clamp(11.5px, 0.85vw, 16px);
  color: #6b625c;
}

.login__link {
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
  font-size: clamp(11.5px, 0.85vw, 16px);
  color: #e8453c;
  font-family: inherit;
}

.login__link:hover {
  text-decoration: underline;
}

.login__submit {
width: 100%;
  height: clamp(42px, 2.6vw, 52px);
  font-size: clamp(14px, 1vw, 18px);
  font-weight: 600;
  letter-spacing: clamp(1px, 0.16vw, 3px);
  border: 0;
  border-radius: clamp(8px, 0.68vw, 13px);
  background: linear-gradient(96deg, #f0524a 0%, #e0352c 100%);
}

.login__submit:hover,
.login__submit:focus {
  background: linear-gradient(96deg, #e8453c 0%, #cf2d25 100%);
}

.login__submit-icon {
  margin-left: 6px;
  letter-spacing: 0;
  vertical-align: middle;
}

.login__foot {
margin: clamp(14px, 2.4vh, 26px) 0 0;
  text-align: center;
  font-size: clamp(9.5px, 0.66vw, 12px);
  color: #c6beb8;
  letter-spacing: 0.3px;
}

.login__foot span {
display: block;
  margin-top: clamp(3px, 0.5vh, 5px);
  color: #d2cac4;
}

/* ========================= 分辨率适配 =========================
   1920×1080 / 1600×900 / 1366×768 首屏完整，无横纵向滚动
   ============================================================ */
@media (max-height: 820px) {
  .login__content {
    padding-top: 3.4vh;
  }
  .login__slogan {
    margin-top: 9px;
  }
  .login__features {
    margin-top: 8px;
  }
  .login__card-head {
    margin-bottom: 16px;
  }
}

@media (max-height: 700px) {
  .login__card-sub {
    display: none;
  }
  .login__foot span {
    display: none;
  }
}

@media (max-width: 1280px) and (min-width: 1025px) {
  .login__stage {
    flex-basis: 58%;
    max-width: 58%;
  }
  .login__card {
    width: min(38vw, 520px);
  }
}

/* 窄屏 / 平板：上下排布 */
@media (max-width: 1024px) {
  .login {
    flex-direction: column;
    height: auto;
    min-height: 100vh;
    overflow: auto;
  }
  .login__stage {
    flex: 0 0 auto;
    max-width: 100%;
  }
  .login__content {
    padding: 24px 24px 0;
  }
  .login__brand-logo {
    width: 56px;
    height: 56px;
  }
  .login__brand-title {
    font-size: 26px;
    letter-spacing: 1px;
  }
  .login__brand-sub {
    font-size: 11px;
  }
  .login__slogan {
    font-size: 19px;
  }
  .login__features {
    margin-top: 10px;
  }
  .login__feature {
    font-size: 12px;
  }
  .login__hero {
    height: 200px;
    flex: 0 0 auto;
  }
  .login__panel {
    padding: 26px 24px 40px;
  }
  .login__card {
    width: 100%;
    max-width: 460px;
  }
  .login__card-logo {
    width: 52px;
    height: 52px;
  }
  .login__card-title {
    margin-top: 14px;
    font-size: 20px;
  }
  .login__card-sub {
    margin-top: 7px;
    font-size: 12px;
  }
  .login__card-head {
    margin-bottom: 20px;
  }
  .login :deep(.el-input__wrapper) {
    height: 44px;
  }
  .login__submit {
    height: 46px;
    font-size: 15px;
  }
}

@media (max-width: 560px) {
  .login__features {
    display: none;
  }
  .login__slogan {
    font-size: 17px;
  }
}
</style>
