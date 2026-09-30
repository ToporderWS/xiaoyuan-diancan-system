/**
 * 接口定义 —— 与后端路由严格一一对应。
 * 页面只调用本文件暴露的方法，不直接拼 URL。
 */
import { http, upload } from '../utils/request.js'

/** 学生账号 1~7 */
export const userApi = {
  register: (data) => http.post('/user/register', data, { auth: false }),
  login: (data) => http.post('/user/login', data, { auth: false }),
  info: () => http.get('/user/info'),
  updateInfo: (data) => http.post('/user/update_info', data),
  updatePwd: (data) => http.post('/user/update_pwd', data),
  uploadAvatar: (filePath) => upload({ url: '/user/upload_avatar', filePath, name: 'avatar' }),
  logout: () => http.post('/user/logout', {})
}

/** 菜品 / 分类 8~9（无需 Token） */
export const foodApi = {
  categories: () => http.get('/food/category/list', {}, { auth: false }),
  list: (params) => http.get('/food/list', params || {}, { auth: false })
}

/** 购物车 10~12 */
export const cartApi = {
  list: (opt) => http.get('/cart/list', {}, opt),
  save: (foodId, count, opt) => http.post('/cart/save', { food_id: foodId, count }, opt),
  del: (cartId) => http.post('/cart/del', { cart_id: cartId })
}

/** 订单 13~17、17A */
export const orderApi = {
  create: (data) => http.post('/order/create', data),
  myList: (params) => http.get('/order/my_list', params || {}),
  detail: (orderId) => http.get('/order/detail', { order_id: orderId }),
  cancel: (orderId) => http.post('/order/cancel', { order_id: orderId }),
  // 模拟支付：仅 0 → 1，不接入真实微信支付
  pay: (orderId) => http.post('/order/pay', { order_id: orderId })
}

/** 公告 17（无需 Token） */
export const noticeApi = {
  list: () => http.get('/notice/list', {}, { auth: false })
}

export default { userApi, foodApi, cartApi, orderApi, noticeApi }
