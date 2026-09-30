<template>
  <el-container class="layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="layout__aside">
      <div class="co-sidebar">
        <div class="co-sidebar__logo">
          <img class="co-sidebar__logo-img" :src="logoUrl" alt="logo" />
          <span v-show="!collapsed" class="co-sidebar__logo-text">校园点餐管理系统</span>
        </div>

        <el-menu
          class="co-sidebar__menu"
          :default-active="activeMenu"
          :collapse="collapsed"
          :collapse-transition="false"
          background-color="#1f2028"
          text-color="#b9bac4"
          active-text-color="#ffffff"
          router
        >
          <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>
              <span>{{ item.title }}</span>
              <span
                v-if="item.path === '/order' && adminStore.pendingOrders > 0"
                class="co-badge-dot"
              >
                {{ adminStore.pendingOrders > 99 ? '99+' : adminStore.pendingOrders }}
              </span>
            </template>
          </el-menu-item>
        </el-menu>
      </div>
    </el-aside>

    <el-container>
      <el-header height="64px" class="layout__header">
        <div class="co-header">
          <div class="co-header__left">
            <span class="co-header__collapse" @click="collapsed = !collapsed">
              <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
            </span>
            <span class="co-header__title">{{ currentTitle }}</span>
            <el-tag v-if="pendingLabel" type="danger" effect="light" size="small">
              {{ pendingLabel }}
            </el-tag>
          </div>

          <div class="co-header__right">
            <el-tooltip content="刷新当前页" placement="bottom">
              <el-icon class="co-header__collapse" @click="refresh"><Refresh /></el-icon>
            </el-tooltip>

            <el-dropdown trigger="click" @command="onCommand">
              <span class="co-header__user">
                <img class="co-avatar" :src="avatarUrl" alt="avatar" />
                <span class="co-header__name">
                  {{ adminStore.realName || adminStore.adminName || '管理员' }}
                </span>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><Setting /></el-icon> 个人中心
                  </el-dropdown-item>
                  <el-dropdown-item command="logout" divided>
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-header>

      <el-main class="co-main layout__main">
        <router-view v-slot="{ Component }">
          <component :is="Component" :key="viewKey" />
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { dashboardApi } from '@/api'
import { imageUrl } from '@/config'
import { useAdminStore } from '@/stores/admin'

const route = useRoute()
const router = useRouter()
const adminStore = useAdminStore()

const collapsed = ref(false)
const viewKey = ref(0)

const menus = [
  { path: '/dashboard', title: '控制台', icon: 'Odometer' },
  { path: '/user', title: '学生用户', icon: 'User' },
  { path: '/category', title: '菜品分类', icon: 'Menu' },
  { path: '/food', title: '菜品管理', icon: 'Food' },
  { path: '/cart', title: '购物车查看', icon: 'ShoppingCart' },
  { path: '/order', title: '订单管理', icon: 'List' },
  { path: '/notice', title: '公告管理', icon: 'Bell' },
  { path: '/profile', title: '个人中心', icon: 'Setting' }
]

// 品牌图形统一使用 public/brand-logo.svg（与登录页、favicon 同一套品牌语言）
const logoUrl = '/brand-logo.svg'
const avatarUrl = computed(() => imageUrl(adminStore.avatar))
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => (route.meta && route.meta.title) || '控制台')

async function loadPending() {
  try {
    const data = await dashboardApi.stats()
    adminStore.setPendingOrders(data.cards.pending_accept_orders)
  } catch (e) {
    adminStore.setPendingOrders(0)
  }
}

function refresh() {
  viewKey.value += 1
  loadPending()
  ElMessage.success('已刷新')
}

function onCommand(command) {
  if (command === 'profile') {
    router.push('/profile')
    return
  }
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
      confirmButtonText: '确定退出',
      cancelButtonText: '取消',
      type: 'warning'
    })
      .then(async () => {
        await adminStore.logout()
        ElMessage.success('已退出登录')
        router.replace('/login')
      })
      .catch(() => {})
  }
}

onMounted(loadPending)
</script>

<style scoped>
.layout {
  height: 100%;
}

.layout__aside {
  transition: width 0.22s ease;
  overflow: hidden;
}

.layout__header {
  padding: 0;
}

.layout__main {
  height: calc(100vh - 64px);
}
</style>
