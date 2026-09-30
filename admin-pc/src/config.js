/**
 * 全局配置 —— 后端地址、静态资源地址、Token Key 全部集中在此。
 * 业务代码中禁止出现硬编码 IP 或完整 URL。
 *
 * ★ 环境切换（二选一，页面代码均无需改动）：
 *   A) 开发/局域网：使用下面的 LAN 兜底地址，与 miniprogram/utils/config.js
 *      的 dev 档位、backend/config.py 的 PUBLIC_API_BASE 保持三处一致
 *      （一致性由 backend/scripts/check_config_sync.py 自动校验）。
 *   B) 正式/HTTPS：在 admin-pc/.env.production 中填写
 *          VITE_API_BASE=https://<你的域名>/api
 *          VITE_STATIC_BASE=https://<你的域名>/static/upload/
 *      构建时自动覆盖（见 admin-pc/.env.example）。本项目不预置虚构域名。
 */

// 局域网兜底地址（未提供 VITE_* 时使用）
const LAN_API_BASE = 'http://127.0.0.1:5000/api'
const LAN_STATIC_BASE = 'http://127.0.0.1:5000/static/upload/'

// Vite 环境变量（import.meta.env 在非 Vite 环境下可能不存在，故加兜底）
const VITE_ENV = (typeof import.meta !== 'undefined' && import.meta.env) ? import.meta.env : {}

// API 基础地址
export const BASE_URL = VITE_ENV.VITE_API_BASE || LAN_API_BASE

// 图片静态资源基础地址（数据库只保存文件名，结尾必须带 /）
export const STATIC_BASE = VITE_ENV.VITE_STATIC_BASE || LAN_STATIC_BASE

// 菜品图片兜底占位图文件名（与后端 Config 保持一致的静态目录文件）
export const FALLBACK_FOOD_IMAGE = 'food-default.jpg'

// 默认头像文件名（与后端 Config.DEFAULT_AVATAR 一致）
export const DEFAULT_AVATAR = 'default_user.jpg'

// 请求超时（毫秒）
export const TIMEOUT = 20000

// 本地存储 Key —— PC 后台固定使用 admin_token，与学生端 student_token 严格区分
export const STORAGE_KEY = {
  TOKEN: 'admin_token',
  PROFILE: 'admin_profile'
}

// 订单状态（与后端 order_service.STATUS_TEXT 一致）
export const ORDER_STATUS = {
  PENDING_PAY: 0,
  PENDING_ACCEPT: 1,
  DELIVERING: 2,
  FINISHED: 3,
  CANCELED: 4
}

export const ORDER_STATUS_TEXT = {
  0: '待支付',
  1: '待接单',
  2: '配送中',
  3: '已完成',
  4: '已取消'
}

// Element Plus Tag 类型（与餐饮暖红主题搭配）
export const ORDER_STATUS_TAG = {
  0: 'danger',
  1: 'warning',
  2: 'primary',
  3: 'success',
  4: 'info'
}

export const ORDER_STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '待支付', value: 0 },
  { label: '待接单', value: 1 },
  { label: '配送中', value: 2 },
  { label: '已完成', value: 3 },
  { label: '已取消', value: 4 }
]

/**
 * 图片文件名 → 完整 URL；空值回退到默认头像。
 */
export function imageUrl(filename, fallback = DEFAULT_AVATAR) {
  if (!filename) return STATIC_BASE + fallback
  if (/^https?:\/\//.test(filename)) return filename
  return STATIC_BASE + filename
}

// 菜品兜底占位图的完整地址（el-image 的 #error 插槽 / img 的 @error 使用）
export const FALLBACK_FOOD_IMAGE_URL = STATIC_BASE + FALLBACK_FOOD_IMAGE

/**
 * 原生 <img> 的 @error 处理器：图片加载失败时切到兜底占位图。
 * 用 === 判断避免兜底图本身加载失败时产生无限循环。
 */
export function onImgError(event) {
  const el = event && event.target
  if (el && el.src !== FALLBACK_FOOD_IMAGE_URL) {
    el.src = FALLBACK_FOOD_IMAGE_URL
  }
}

export default {
  BASE_URL,
  STATIC_BASE,
  DEFAULT_AVATAR,
  FALLBACK_FOOD_IMAGE,
  FALLBACK_FOOD_IMAGE_URL,
  TIMEOUT,
  STORAGE_KEY,
  ORDER_STATUS,
  ORDER_STATUS_TEXT,
  ORDER_STATUS_TAG,
  ORDER_STATUS_OPTIONS,
  imageUrl,
  onImgError
}
