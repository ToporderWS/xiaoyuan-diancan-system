/**
 * 全局配置 —— 所有地址、Token Key 集中在此，禁止在各页面散落硬编码。
 *
 * ★ 环境切换：全项目只需改下面这一个 ENV 常量。
 *   'dev'  → 局域网 HTTP，用于微信开发者工具模拟器 / 本机联调（默认）
 *   'prod' → HTTPS 正式环境，用于真机体验版 / 正式版
 *
 * 为什么真机必须用 prod：微信小程序真机的 <image> / wx.request 对 http 与
 * IP 地址是内核级拦截（「不校验合法域名」只对开发者工具模拟器生效），
 * 因此真机图片与接口都必须走 HTTPS 合法域名。
 */
// ★ 当前档位：'prod' —— 本轮真机 HTTPS 验证使用。
//   真机验证结束后若要回到局域网联调，把 ENV 改回 'dev' 即可（dev 档位原样保留）。
const ENV = 'prod'

const PROFILES = {
  dev: {
    // 局域网开发地址：与 backend/config.py 的 PUBLIC_API_BASE / PUBLIC_STATIC_BASE
    // 以及 admin-pc/src/config.js 的 LAN 兜底地址保持三处一致
    // （一致性由 backend/scripts/check_config_sync.py 自动校验）
    API_BASE: 'http://192.168.0.103:5000/api',
    STATIC_BASE: 'http://192.168.0.103:5000/static/upload/'
  },
  prod: {
    // HTTPS 正式 / 真机环境（Cloudflare Tunnel 域名）。
    // 已加入微信公众平台「开发管理 → 服务器域名」的
    // request 合法域名 与 downloadFile 合法域名（图片走 downloadFile 校验）。
    API_BASE: 'https://mineral-antiques-airports-prerequisite.trycloudflare.com/api',
    STATIC_BASE: 'https://mineral-antiques-airports-prerequisite.trycloudflare.com/static/upload/'
  }
}

/**
 * 解析当前档位。prod 未填写时**显式抛错**而不是静默回退到局域网 HTTP ——
 * 静默回退会把"配置没填"伪装成"图片挂了"，属于最容易被误判的失败模式。
 */
function resolveProfile() {
  const p = PROFILES[ENV] || PROFILES.dev
  if (!p.API_BASE || !p.STATIC_BASE) {
    throw new Error('[config] ENV=' + ENV + ' 的 API_BASE / STATIC_BASE 尚未配置，'
      + '请在 miniprogram/utils/config.js 的 PROFILES.' + ENV + ' 中填入 HTTPS 域名')
  }
  if (ENV === 'prod' && !/^https:\/\//.test(p.API_BASE)) {
    throw new Error('[config] prod 档位必须使用 https:// 地址，当前为：' + p.API_BASE)
  }
  return p
}

const PROFILE = resolveProfile()

// 当前生效的环境档位名（dev / prod）
export const ENV_NAME = ENV

// 后端 API 基础地址
export const BASE_URL = PROFILE.API_BASE

// 图片静态资源基础地址（数据库只保存文件名，拼接由此常量完成；结尾必须带 /）
export const STATIC_BASE = PROFILE.STATIC_BASE

// 默认头像文件名（与后端 Config.DEFAULT_AVATAR 保持一致）
export const DEFAULT_AVATAR = 'default_user.jpg'

// 菜品兜底占位图（本地包内资源，不依赖网络，加载失败时也可显示）
export const FALLBACK_FOOD_IMAGE = '/static/food-default.png'

// 后端菜品占位图文件名：数据库若仍存该值，等价于「未设置真实图片」
export const SERVER_FOOD_PLACEHOLDER = 'food-default.jpg'

// 本地存储 Key —— 学生端只使用 student_token，与 PC 管理后台的 Token Key 严格区分
export const STORAGE_KEY = {
  TOKEN: 'student_token',
  USER: 'student_user'
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

// 订单状态筛选 Tab
export const ORDER_TABS = [
  { label: '全部', value: null },
  { label: '待支付', value: 0 },
  { label: '待接单', value: 1 },
  { label: '配送中', value: 2 },
  { label: '已完成', value: 3 },
  { label: '已取消', value: 4 }
]

// 请求超时时间（毫秒）
export const TIMEOUT = 15000

/**
 * 图片文件名 → 完整可访问 URL —— 全项目唯一的图片地址生成规则。
 *
 * 兜底顺序（三者任一成立都用本地占位图，保证不白屏、不报错）：
 *   1) failed 为真（<image> 的 @error 已触发，例如后端文件被删除 / 网络异常）
 *   2) filename 为空（菜品未设置图片）
 *   3) filename 等于后端占位图名（等价于未设置真实图片）
 * 若后端直接返回完整 URL（http/https），则原样使用。
 */
export function imageUrl(filename, failed) {
  if (failed) return FALLBACK_FOOD_IMAGE
  if (!filename) return FALLBACK_FOOD_IMAGE
  if (filename === SERVER_FOOD_PLACEHOLDER) return FALLBACK_FOOD_IMAGE
  if (/^https?:\/\//.test(filename)) return filename
  return STATIC_BASE + filename
}

/**
 * <image> 的 @error 处理器 —— 全项目统一调用。
 *
 * 用法：
 *   <image :src="imgUrl(f.food_img, f.food_img_failed)" @error="onImgError(f)" />
 *   methods: { onImgError: markImgFailed }
 *
 * 只在数据对象上打一个失败标记（不破坏原有 food_img），
 * imageUrl 收到该标记后返回本地占位图，从而做到：不白屏、不报致命错误。
 */
export function markImgFailed(item, key) {
  if (item && typeof item === 'object') {
    item[(key || 'food_img') + '_failed'] = true
  }
}

/**
 * 头像文件名 → 完整 URL。
 * 头像兜底与菜品不同：回退到服务端的 default_user.jpg，而不是菜品占位图。
 */
export function avatarUrl(filename, failed) {
  if (failed || !filename) return STATIC_BASE + DEFAULT_AVATAR
  if (/^https?:\/\//.test(filename)) return filename
  return STATIC_BASE + filename
}

export default {
  ENV_NAME,
  BASE_URL,
  STATIC_BASE,
  DEFAULT_AVATAR,
  FALLBACK_FOOD_IMAGE,
  SERVER_FOOD_PLACEHOLDER,
  STORAGE_KEY,
  ORDER_STATUS,
  ORDER_STATUS_TEXT,
  ORDER_TABS,
  TIMEOUT,
  imageUrl,
  markImgFailed,
  avatarUrl
}
