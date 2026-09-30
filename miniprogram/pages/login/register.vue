<template>
  <view class="co-page register">
    <view class="head">
      <text class="head__title">创建账号</text>
      <text class="head__sub">填写以下信息即可开始点餐</text>
    </view>

    <view class="co-card form">
      <view class="co-field">
        <image class="field__ico" src="/static/icons/edit.png" mode="aspectFit" />
        <input
          class="co-field__input"
          v-model="form.nickname"
          maxlength="50"
          placeholder="请输入昵称"
          placeholder-class="co-ph"
        />
      </view>
      <view class="co-field">
        <image class="field__ico" src="/static/icons/mobile.png" mode="aspectFit" />
        <input
          class="co-field__input"
          v-model="form.phone"
          type="number"
          maxlength="11"
          placeholder="11位手机号，用于登录"
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
          placeholder="不少于6位"
          placeholder-class="co-ph"
        />
        <text class="field__eye co-tap" @tap="showPwd = !showPwd">
          {{ showPwd ? '隐藏' : '显示' }}
        </text>
      </view>
      <view class="co-field">
        <image class="field__ico" src="/static/icons/lock.png" mode="aspectFit" />
        <input
          class="co-field__input"
          v-model="form.confirm"
          :password="!showPwd"
          maxlength="64"
          placeholder="请再次输入密码"
          placeholder-class="co-ph"
        />
      </view>
      <view class="co-field">
        <image class="field__ico" src="/static/icons/shield.png" mode="aspectFit" />
        <input
          class="co-field__input"
          v-model="form.student_no"
          maxlength="30"
          placeholder="请输入学号"
          placeholder-class="co-ph"
        />
      </view>
      <view class="co-field">
        <image class="field__ico" src="/static/icons/location.png" mode="aspectFit" />
        <input
          class="co-field__input"
          v-model="form.dormitory"
          maxlength="100"
          placeholder="如：宿舍楼3栋 502（默认收货地址）"
          placeholder-class="co-ph"
        />
      </view>
    </view>

    <view class="tips">
      <text>· 注册即表示同意由校园食堂统一管理账号信息</text>
      <text>· 密码仅以加密哈希形式存储，平台无法查看明文</text>
    </view>

    <view
      class="co-btn submit co-tap"
      :class="{ 'co-btn--disabled': submitting }"
      @tap="onSubmit"
    >
      {{ submitting ? '提交中...' : '注 册' }}
    </view>
    <view class="back co-tap" @tap="goLogin">
      <text>已有账号？返回登录</text>
    </view>
  </view>
</template>

<script>
import { userApi } from '../../api/index.js'

const PHONE_RE = /^1[3-9]\d{9}$/

export default {
  data() {
    return {
      form: { nickname: '', phone: '', password: '', confirm: '', student_no: '', dormitory: '' },
      showPwd: false,
      submitting: false
    }
  },
  methods: {
    validate() {
      const f = this.form
      if (!f.nickname || f.nickname.trim().length < 2) return '昵称不能少于 2 个字符'
      if (f.nickname.trim().length > 50) return '昵称不能超过 50 个字符'
      if (!PHONE_RE.test(f.phone)) return '请输入正确的手机号'
      if (!f.password || f.password.length < 6) return '密码不能少于 6 位'
      if (f.password.length > 64) return '密码不能超过 64 位'
      if (f.password !== f.confirm) return '两次输入的密码不一致'
      if (f.student_no && f.student_no.length > 30) return '学号不能超过 30 个字符'
      if (f.dormitory && f.dormitory.length > 100) return '宿舍不能超过 100 个字符'
      return ''
    },
    onSubmit() {
      if (this.submitting) return
      const err = this.validate()
      if (err) {
        uni.showToast({ title: err, icon: 'none' })
        return
      }
      this.submitting = true
      userApi
        .register({
          nickname: this.form.nickname.trim(),
          phone: this.form.phone,
          password: this.form.password,
          student_no: (this.form.student_no || '').trim(),
          dormitory: (this.form.dormitory || '').trim()
        })
        .then(() => {
          uni.showToast({ title: '注册成功，请登录', icon: 'success' })
          setTimeout(() => this.goLogin(), 900)
        })
        .catch(() => {})
        .then(() => {
          this.submitting = false
        })
    },
    goLogin() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.navigateTo({ url: '/pages/login/login' })
    }
  }
}
</script>

<style>
.register {
  padding-bottom: 60rpx;
}
.head {
  padding: 44rpx 40rpx 28rpx;
}
.head__title {
  display: block;
  font-size: 44rpx;
  font-weight: 700;
  color: var(--co-text);
}
.head__sub {
  display: block;
  margin-top: 10rpx;
  font-size: 26rpx;
  color: var(--co-text-3);
}

.form {
  margin: 0 40rpx;
  padding: 8rpx 32rpx;
}
.field__ico {
  width: 36rpx;
  height: 36rpx;
  flex-shrink: 0;
  margin-right: 20rpx;
}
.field__eye {
  flex-shrink: 0;
  padding-left: 16rpx;
  font-size: 24rpx;
  color: var(--co-text-2);
}

.tips {
  margin: 26rpx 40rpx 0;
  display: flex;
  flex-direction: column;
}
.tips text {
  font-size: 22rpx;
  color: var(--co-text-4);
  line-height: 1.8;
}

.submit {
  margin: 44rpx 40rpx 0;
  letter-spacing: 4rpx;
}
.back {
  margin-top: 32rpx;
  text-align: center;
  font-size: 26rpx;
  color: var(--co-primary);
}
</style>
