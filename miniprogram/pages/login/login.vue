<template>
  <view class="co-page login">
    <!-- 自定义导航（login 使用 navigationStyle: custom） -->
    <view class="navbar">
      <view class="navbar__back co-tap" @tap="back">
        <image class="navbar__back-ico" src="/static/icons/arrow.png" mode="aspectFit" />
      </view>
      <text class="navbar__title">登录</text>
      <view class="navbar__placeholder"></view>
    </view>

    <!-- 品牌区 -->
    <view class="brand">
      <image class="brand__logo" src="/static/logo.png" mode="aspectFit" />
      <text class="brand__title">欢迎回来</text>
      <text class="brand__sub">校园点餐 · 便捷就餐</text>
    </view>

    <!-- 表单 -->
    <view class="co-card form">
      <view class="co-field">
        <image class="field__ico" src="/static/icons/mobile.png" mode="aspectFit" />
        <input
          class="co-field__input"
          v-model="form.phone"
          type="number"
          maxlength="11"
          placeholder="请输入手机号"
          placeholder-class="co-ph"
        />
      </view>

      <view class="co-field">
        <image class="field__ico" src="/static/icons/lock.png" mode="aspectFit" />
        <input
          class="co-field__input"
          v-model="form.password"
          :password="!showPwd"
          maxlength="64"
          placeholder="请输入密码"
          placeholder-class="co-ph"
        />
        <text class="field__eye co-tap" @tap="showPwd = !showPwd">
          {{ showPwd ? '隐藏' : '显示' }}
        </text>
      </view>

      <view class="form__row">
        <view class="form__remember co-tap" @tap="remember = !remember">
          <view class="co-check" :class="{ 'co-check--on': remember }">
            <image
              v-if="remember"
              class="co-ico"
              src="/static/icons/check-white.png"
              mode="aspectFit"
            />
          </view>
          <text class="form__remember-text">记住手机号</text>
        </view>
        <text class="form__link co-tap" @tap="onForget">忘记密码？</text>
      </view>

      <view class="co-btn form__submit co-tap" :class="{ 'co-btn--disabled': !canSubmit }" @tap="onLogin">
        {{ submitting ? '登录中...' : '登 录' }}
      </view>

      <view class="form__foot">
        <text class="form__foot-tip">还没有账号？</text>
        <text class="form__link form__foot-link co-tap" @tap="goRegister">立即注册</text>
      </view>
    </view>

    <view class="co-page__tip">
      <text>登录即表示同意由校园食堂统一管理账号信息</text>
    </view>
  </view>
</template>

<script>
import { userApi } from '../../api/index.js'
import { setToken, setUser, getUser, clearToken } from '../../utils/request.js'

const PHONE_RE = /^1[3-9]\d{9}$/
const REMEMBER_KEY = 'student_remember_phone'

export default {
  data() {
    return {
      form: { phone: '', password: '' },
      showPwd: false,
      remember: true,
      submitting: false
    }
  },
  computed: {
    canSubmit() {
      return PHONE_RE.test(this.form.phone) && this.form.password.length >= 6 && !this.submitting
    }
  },
  onLoad() {
    const saved = uni.getStorageSync(REMEMBER_KEY)
    if (saved) this.form.phone = saved
    // 已登录则直接返回上一页，避免重复登录
    const u = getUser()
    if (u && u.phone && this.form.phone === '') this.form.phone = u.phone
  },
  methods: {
    back() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.switchTab({ url: '/pages/index/index' })
    },
    goRegister() {
      uni.navigateTo({ url: '/pages/login/register' })
    },
    onForget() {
      uni.showModal({
        title: '忘记密码',
        content: 'V1.0 暂不提供自助找回密码，请联系食堂管理员在后台协助重置。',
        showCancel: false,
        confirmText: '知道了'
      })
    },
    onLogin() {
      if (this.submitting) return
      const phone = (this.form.phone || '').trim()
      const password = this.form.password || ''
      if (!PHONE_RE.test(phone)) {
        uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
        return
      }
      if (password.length < 6) {
        uni.showToast({ title: '密码不能少于 6 位', icon: 'none' })
        return
      }
      this.submitting = true
      userApi
        .login({ phone, password })
        .then((d) => {
          // 前端只保存 Token 与公开资料，绝不保存密码
          clearToken()
          setToken(d.token)
          setUser({
            user_id: d.user_id,
            nickname: d.nickname,
            phone: d.phone,
            avatar: d.avatar,
            student_no: d.student_no,
            dormitory: d.dormitory
          })
          if (this.remember) uni.setStorageSync(REMEMBER_KEY, phone)
          else uni.removeStorageSync(REMEMBER_KEY)

          uni.showToast({ title: '登录成功', icon: 'success' })
          setTimeout(() => {
            const pages = getCurrentPages()
            if (pages.length > 1) uni.navigateBack()
            else uni.switchTab({ url: '/pages/index/index' })
          }, 700)
        })
        .catch(() => {})
        .then(() => {
          this.submitting = false
        })
    }
  }
}
</script>

<style>
.login {
  padding-bottom: 60rpx;
}

/* 自定义导航 */
.navbar {
  height: 88rpx;
  display: flex;
  align-items: center;
  padding: 0 24rpx;
  padding-top: var(--status-bar-height, 0);
}
.navbar__back {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
}
.navbar__back-ico {
  width: 34rpx;
  height: 34rpx;
  /* arrow 图标为右向箭头，翻转后作为返回箭头 */
  transform: scaleX(-1);
}
.navbar__title {
  flex: 1;
  text-align: center;
  font-size: 32rpx;
  font-weight: 600;
  color: var(--co-text);
}
.navbar__placeholder {
  width: 64rpx;
}

/* 品牌区 */
.brand {
  padding: 56rpx 0 44rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.brand__logo {
  width: 136rpx;
  height: 136rpx;
  border-radius: 34rpx;
  background-color: var(--co-card);
  box-shadow: 0 8rpx 24rpx rgba(31, 26, 22, 0.08);
}
.brand__title {
  margin-top: 26rpx;
  font-size: 44rpx;
  font-weight: 700;
  color: var(--co-text);
  letter-spacing: 1rpx;
}
.brand__sub {
  margin-top: 10rpx;
  font-size: 26rpx;
  color: var(--co-text-3);
}

/* 表单 */
.form {
  margin: 0 40rpx;
  padding: 8rpx 32rpx 40rpx;
}
.field__ico {
  width: 36rpx;
  height: 36rpx;
  flex-shrink: 0;
  margin-right: 20rpx;
}
.field__eye {
  flex-shrink: 0;
  padding-left: 20rpx;
  font-size: 24rpx;
  color: var(--co-text-2);
}
.form__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 30rpx;
}
.form__remember {
  display: flex;
  align-items: center;
}
.form__remember-text {
  margin-left: 12rpx;
  font-size: 24rpx;
  color: var(--co-text-2);
}
.form__link {
  font-size: 24rpx;
  color: var(--co-primary);
}
.form__submit {
  margin-top: 44rpx;
  letter-spacing: 4rpx;
}
.form__foot {
  margin-top: 32rpx;
  text-align: center;
}
.form__foot-tip {
  font-size: 26rpx;
  color: var(--co-text-3);
}
.form__foot-link {
  font-size: 26rpx;
  font-weight: 600;
  margin-left: 6rpx;
}
.co-page__tip {
  margin-top: 48rpx;
  text-align: center;
  font-size: 22rpx;
  color: var(--co-text-4);
}
</style>
