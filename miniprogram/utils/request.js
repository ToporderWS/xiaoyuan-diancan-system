/**
 * 统一请求层。
 *
 * 职责：
 * 1. 拼接 BASE_URL，统一携带 Authorization: Bearer {student_token}
 * 2. 统一解包后端 { code, msg, data } 结构
 * 3. 统一 loading / 错误提示
 * 4. 401 统一清除 student_token 并跳转登录页
 *
 * 页面中禁止重复编写请求逻辑，一律走本模块。
 */
import { BASE_URL, STORAGE_KEY, TIMEOUT } from './config.js'

let redirecting = false

export function getToken() {
  try {
    return uni.getStorageSync(STORAGE_KEY.TOKEN) || ''
  } catch (e) {
    return ''
  }
}

export function setToken(token) {
  uni.setStorageSync(STORAGE_KEY.TOKEN, token || '')
}

export function clearToken() {
  uni.removeStorageSync(STORAGE_KEY.TOKEN)
  uni.removeStorageSync(STORAGE_KEY.USER)
}

export function getUser() {
  try {
    return uni.getStorageSync(STORAGE_KEY.USER) || null
  } catch (e) {
    return null
  }
}

export function setUser(user) {
  uni.setStorageSync(STORAGE_KEY.USER, user || {})
}

export function isLogin() {
  return !!getToken()
}

/**
 * 401 统一处理：清 Token → 跳登录页。
 * 使用 redirecting 闸门，避免并发请求触发多次跳转。
 */
function handleUnauthorized(msg) {
  clearToken()
  if (redirecting) return
  redirecting = true
  uni.showToast({ title: msg || '登录已失效，请重新登录', icon: 'none' })
  setTimeout(() => {
    redirecting = false
    const pages = getCurrentPages()
    const current = pages.length ? pages[pages.length - 1].route : ''
    if (current && current.indexOf('pages/login/login') === 0) return
    uni.navigateTo({ url: '/pages/login/login' })
  }, 600)
}

/**
 * 基础请求。
 * @param {Object} options
 *   url      {String}  以 / 开头的接口路径，如 '/food/list'
 *   method   {String}  GET / POST
 *   data     {Object}  请求数据
 *   auth     {Boolean} 是否需要登录态（默认 true）
 *   loading  {Boolean|String} 是否显示 loading
 *   silent   {Boolean} 是否静默（不弹错误提示）
 */
export function request(options = {}) {
  const {
    url = '',
    method = 'GET',
    data = {},
    auth = true,
    loading = false,
    silent = false,
    header = {}
  } = options

  const token = getToken()
  const finalHeader = Object.assign({ 'Content-Type': 'application/json' }, header)
  if (token) {
    finalHeader.Authorization = 'Bearer ' + token
  }

  if (loading) {
    uni.showLoading({ title: typeof loading === 'string' ? loading : '加载中...', mask: true })
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header: finalHeader,
      timeout: TIMEOUT,
      success(res) {
        const body = res.data
        if (!body || typeof body !== 'object') {
          if (!silent) uni.showToast({ title: '服务响应异常', icon: 'none' })
          reject(new Error('响应格式异常'))
          return
        }
        if (body.code === 200) {
          resolve(body.data === undefined ? {} : body.data)
          return
        }
        if (body.code === 401) {
          handleUnauthorized(body.msg)
          reject(Object.assign(new Error(body.msg || '未登录'), { code: 401 }))
          return
        }
        if (!silent) {
          uni.showToast({ title: body.msg || '操作失败', icon: 'none' })
        }
        reject(Object.assign(new Error(body.msg || '操作失败'), { code: body.code || 400 }))
      },
      fail(err) {
        if (!silent) {
          uni.showToast({ title: '网络异常，请检查后端服务是否已启动', icon: 'none' })
        }
        reject(err)
      },
      complete() {
        if (loading) uni.hideLoading()
      }
    })
  })
}

/**
 * 上传文件（multipart/form-data）。
 */
export function upload(options = {}) {
  const { url = '', filePath, name = 'file', formData = {}, loading = true } = options
  const token = getToken()
  const header = {}
  if (token) header.Authorization = 'Bearer ' + token

  if (loading) uni.showLoading({ title: '上传中...', mask: true })

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + url,
      filePath,
      name,
      formData,
      header,
      success(res) {
        let body = null
        try {
          body = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
        } catch (e) {
          body = null
        }
        if (!body) {
          uni.showToast({ title: '上传响应异常', icon: 'none' })
          reject(new Error('上传响应异常'))
          return
        }
        if (body.code === 200) {
          resolve(body.data || {})
        } else if (body.code === 401) {
          handleUnauthorized(body.msg)
          reject(Object.assign(new Error(body.msg), { code: 401 }))
        } else {
          uni.showToast({ title: body.msg || '上传失败', icon: 'none' })
          reject(Object.assign(new Error(body.msg || '上传失败'), { code: body.code }))
        }
      },
      fail(err) {
        uni.showToast({ title: '上传失败', icon: 'none' })
        reject(err)
      },
      complete() {
        if (loading) uni.hideLoading()
      }
    })
  })
}

export const http = {
  get: (url, data, opt = {}) => request(Object.assign({ url, method: 'GET', data }, opt)),
  post: (url, data, opt = {}) => request(Object.assign({ url, method: 'POST', data }, opt))
}

export default http
