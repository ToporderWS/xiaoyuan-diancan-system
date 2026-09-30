/**
 * 管理员状态（Pinia）。
 * 只保存 Token 与公开资料，绝不保存密码。
 */
import { defineStore } from 'pinia'

import { authApi } from '@/api'
import { clearToken, getToken, setToken } from '@/api/request'
import { STORAGE_KEY } from '@/config'

function readProfile() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY.PROFILE)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

export const useAdminStore = defineStore('admin', {
  state: () => ({
    token: getToken(),
    profile: readProfile(),
    // 待接单订单数，用于侧边栏角标
    pendingOrders: 0
  }),

  getters: {
    isLogin: (state) => !!state.token,
    adminName: (state) => (state.profile ? state.profile.admin_name : ''),
    realName: (state) => (state.profile ? state.profile.real_name : ''),
    avatar: (state) => (state.profile ? state.profile.avatar : '')
  },

  actions: {
    persistProfile(profile) {
      this.profile = profile || null
      if (profile) localStorage.setItem(STORAGE_KEY.PROFILE, JSON.stringify(profile))
      else localStorage.removeItem(STORAGE_KEY.PROFILE)
    },

    async login(form) {
      const data = await authApi.login({
        admin_name: (form.admin_name || '').trim(),
        password: form.password
      })
      setToken(data.token)
      this.token = data.token
      this.persistProfile({
        id: data.admin_id,
        admin_name: data.admin_name,
        real_name: data.real_name,
        avatar: data.avatar
      })
      return data
    },

    async fetchInfo() {
      const info = await authApi.info()
      this.persistProfile(info)
      return info
    },

    async logout() {
      try {
        await authApi.logout()
      } catch (e) {
        // V1.0 服务端不做 JWT 黑名单，登出失败也不影响前端清除本地凭证
      }
      clearToken()
      this.token = ''
      this.persistProfile(null)
      this.pendingOrders = 0
    },

    setPendingOrders(n) {
      this.pendingOrders = Number(n) || 0
    }
  }
})
