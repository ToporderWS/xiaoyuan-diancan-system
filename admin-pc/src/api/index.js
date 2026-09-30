/**
 * 接口定义 —— 与后端 /api/admin 路由严格一一对应。
 */
import request from './request'

/** 管理员认证与个人中心 */
export const authApi = {
  login: (data) => request.post('/admin/login', data),
  logout: () => request.post('/admin/logout', {}),
  info: () => request.get('/admin/info'),
  updatePwd: (data) => request.post('/admin/update_pwd', data),
  uploadAvatar: (file) => {
    const form = new FormData()
    form.append('avatar', file)
    return request.post('/admin/upload_avatar', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

/** 控制台 */
export const dashboardApi = {
  stats: () => request.get('/admin/dashboard')
}

/** 学生用户（只读） */
export const userApi = {
  list: (params) => request.get('/admin/user/list', { params })
}

/** 分类 */
export const categoryApi = {
  list: () => request.get('/admin/category/list'),
  save: (data) => request.post('/admin/category/save', data),
  del: (id) => request.post('/admin/category/del', { id })
}

/** 菜品 */
export const foodApi = {
  list: (params) => request.get('/admin/food/list', { params }),
  save: (data, file) => {
    if (file) {
      const form = new FormData()
      Object.keys(data).forEach((k) => {
        if (data[k] !== undefined && data[k] !== null) form.append(k, data[k])
      })
      form.append('food_img', file)
      return request.post('/admin/food/save', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }
    return request.post('/admin/food/save', data)
  },
  del: (id) => request.post('/admin/food/del', { id })
}

/** 购物车（只读） */
export const cartApi = {
  list: (params) => request.get('/admin/cart/list', { params })
}

/** 订单 */
export const orderApi = {
  list: (params) => request.get('/admin/order/list', { params }),
  detail: (orderId) => request.get('/admin/order/detail', { params: { order_id: orderId } }),
  receive: (orderId) => request.post('/admin/order/receive', { order_id: orderId }),
  finish: (orderId) => request.post('/admin/order/finish', { order_id: orderId })
}

/** 公告 */
export const noticeApi = {
  list: (params) => request.get('/admin/notice/list', { params }),
  save: (data) => request.post('/admin/notice/save', data),
  del: (id) => request.post('/admin/notice/del', { id })
}

export default { authApi, dashboardApi, userApi, categoryApi, foodApi, cartApi, orderApi, noticeApi }
