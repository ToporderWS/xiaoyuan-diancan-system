/**
 * 统一 Axios 封装。
 *
 * 职责：
 * 1. baseURL / timeout 集中配置
 * 2. 自动携带 Authorization: Bearer {admin_token}
 * 3. 统一解包后端 { code, msg, data }
 * 4. 401 统一清除 admin_token 并跳转 /login
 *
 * 页面中禁止直接使用 axios。
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

import { BASE_URL, STORAGE_KEY, TIMEOUT } from '@/config'

export function getToken() {
  return localStorage.getItem(STORAGE_KEY.TOKEN) || ''
}

export function setToken(token) {
  localStorage.setItem(STORAGE_KEY.TOKEN, token || '')
}

export function clearToken() {
  localStorage.removeItem(STORAGE_KEY.TOKEN)
  localStorage.removeItem(STORAGE_KEY.PROFILE)
}

let redirecting = false

export function redirectToLogin(message) {
  clearToken()
  if (redirecting) return
  redirecting = true
  if (message) ElMessage.error(message)
  const redirect = encodeURIComponent(window.location.hash.replace(/^#/, '') || '/dashboard')
  setTimeout(() => {
    redirecting = false
    window.location.hash = '#/login?redirect=' + redirect
  }, 500)
}

const instance = axios.create({
  baseURL: BASE_URL,
  timeout: TIMEOUT,
  headers: { 'Content-Type': 'application/json' }
})

// ---------------- 请求拦截 ----------------
instance.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) config.headers.Authorization = 'Bearer ' + token
    return config
  },
  (error) => Promise.reject(error)
)

// ---------------- 响应拦截 ----------------
instance.interceptors.response.use(
  (response) => {
    const body = response.data
    if (!body || typeof body !== 'object') {
      ElMessage.error('服务响应格式异常')
      return Promise.reject(new Error('响应格式异常'))
    }
    if (body.code === 200) return body.data === undefined ? {} : body.data
    if (body.code === 401) {
      redirectToLogin(body.msg || '登录已失效，请重新登录')
      return Promise.reject(Object.assign(new Error(body.msg || '未登录'), { code: 401 }))
    }
    // 400 / 500 统一提示
    ElMessage.error(body.msg || '操作失败')
    return Promise.reject(Object.assign(new Error(body.msg || '操作失败'), { code: body.code }))
  },
  (error) => {
    const status = error.response && error.response.status
    if (status === 401) {
      redirectToLogin('登录已失效，请重新登录')
      return Promise.reject(error)
    }
    let msg = '网络异常，请确认后端服务已启动'
    if (status === 404) msg = '接口不存在（404）'
    else if (status === 413) msg = '上传内容过大'
    else if (status >= 500) msg = '服务异常，请稍后再试'
    else if (error.code === 'ECONNABORTED') msg = '请求超时，请重试'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default instance
