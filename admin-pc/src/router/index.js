/**
 * 路由与访问控制。
 * 未登录访问后台页面 → 跳 /login；已登录访问 /login → 跳 /dashboard。
 */
import { createRouter, createWebHashHistory } from 'vue-router'

import { getToken } from '@/api/request'

const Layout = () => import('@/layout/index.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '管理员登录', public: true }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '控制台', icon: 'Odometer' }
      },
      {
        path: 'user',
        name: 'UserList',
        component: () => import('@/views/user/index.vue'),
        meta: { title: '学生用户', icon: 'User' }
      },
      {
        path: 'category',
        name: 'CategoryList',
        component: () => import('@/views/category/index.vue'),
        meta: { title: '菜品分类', icon: 'Menu' }
      },
      {
        path: 'food',
        name: 'FoodList',
        component: () => import('@/views/food/index.vue'),
        meta: { title: '菜品管理', icon: 'Food' }
      },
      {
        path: 'cart',
        name: 'CartList',
        component: () => import('@/views/cart/index.vue'),
        meta: { title: '购物车查看', icon: 'ShoppingCart' }
      },
      {
        path: 'order',
        name: 'OrderList',
        component: () => import('@/views/order/index.vue'),
        meta: { title: '订单管理', icon: 'List' }
      },
      {
        path: 'notice',
        name: 'NoticeList',
        component: () => import('@/views/notice/index.vue'),
        meta: { title: '公告管理', icon: 'Bell' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/index.vue'),
        meta: { title: '个人中心', icon: 'Setting' }
      }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach((to) => {
  const logged = !!getToken()
  if (to.meta.public) {
    // 已登录访问登录页 → 回到控制台
    if (logged && to.path === '/login') return { path: '/dashboard' }
    return true
  }
  if (!logged) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

router.afterEach((to) => {
  const title = to.meta && to.meta.title ? to.meta.title : ''
  document.title = title ? `${title} · 校园点餐管理系统` : '校园点餐管理系统'
})

export default router
