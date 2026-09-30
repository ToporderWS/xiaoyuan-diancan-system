<template>
  <div class="co-page" v-loading="loading">
    <!-- 统计卡 -->
    <div class="co-stats">
      <div class="co-stat" v-for="c in cards" :key="c.label">
        <div class="co-stat__icon" :class="'co-stat__icon--' + c.color">
          <el-icon><component :is="c.icon" /></el-icon>
        </div>
        <div class="co-stat__body">
          <div class="co-stat__label">{{ c.label }}</div>
          <div class="co-stat__value">{{ c.value }}</div>
          <div class="co-stat__extra">{{ c.extra }}</div>
        </div>
      </div>
    </div>

    <!-- 图表 -->
    <div class="co-charts">
      <div class="co-chart-card co-chart-card--wide">
        <div class="co-chart-card__title">
          <span>最近 7 天订单数</span>
          <span class="co-muted" style="font-size: 12px; font-weight: 400">
            数据来源：orders.created_at
          </span>
        </div>
        <EChart :option="trendOption" height="320px" />
      </div>

      <div class="co-chart-card">
        <div class="co-chart-card__title">
          <span>分类销量统计</span>
          <span class="co-muted" style="font-size: 12px; font-weight: 400">
            已支付订单明细聚合
          </span>
        </div>
        <EChart :option="categoryOption" height="320px" />
      </div>

      <div class="co-chart-card">
        <div class="co-chart-card__title">
          <span>订单状态占比</span>
          <span class="co-muted" style="font-size: 12px; font-weight: 400">全部订单</span>
        </div>
        <EChart :option="statusOption" height="320px" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { dashboardApi } from '@/api'
import EChart from '@/components/EChart.vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()
const loading = ref(false)
const data = ref(null)

const cards = computed(() => {
  const c = data.value ? data.value.cards : null
  return [
    {
      label: '学生用户总数',
      value: c ? c.total_users : '-',
      extra: '注册学生账号',
      color: 'red',
      icon: 'User'
    },
    {
      label: '今日新增订单',
      value: c ? c.today_orders : '-',
      extra: c && c.pending_accept_orders ? `其中待接单 ${c.pending_accept_orders} 笔` : '今日 00:00 起',
      color: 'orange',
      icon: 'List'
    },
    {
      label: '今日成交金额',
      value: c ? '¥' + Number(c.today_amount).toFixed(2) : '-',
      extra: '已支付订单（含配送中/已完成）',
      color: 'blue',
      icon: 'Money'
    },
    {
      label: '在售菜品数',
      value: c ? c.on_sale_foods : '-',
      extra: '状态为上架的菜品',
      color: 'green',
      icon: 'Food'
    }
  ]
})

const trendOption = computed(() => {
  const trend = (data.value && data.value.order_trend) || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trend.map((t) => t.label),
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#909399' }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f0f2f5' } },
      axisLabel: { color: '#909399' }
    },
    series: [
      {
        name: '订单数',
        type: 'line',
        smooth: true,
        symbolSize: 8,
        data: trend.map((t) => t.count),
        itemStyle: { color: '#e53935' },
        lineStyle: { width: 3, color: '#e53935' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(229,57,53,0.28)' },
              { offset: 1, color: 'rgba(229,57,53,0.02)' }
            ]
          }
        }
      }
    ]
  }
})

const categoryOption = computed(() => {
  const list = (data.value && data.value.category_sales) || []
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: list.map((c) => c.cat_name),
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#909399', interval: 0 }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f0f2f5' } },
      axisLabel: { color: '#909399' }
    },
    series: [
      {
        name: '销量',
        type: 'bar',
        barMaxWidth: 40,
        data: list.map((c) => c.sales),
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#ff7043' },
              { offset: 1, color: '#e53935' }
            ]
          }
        }
      }
    ]
  }
})

const statusOption = computed(() => {
  const list = (data.value && data.value.status_pie) || []
  const colors = ['#e53935', '#fb8c00', '#1e88e5', '#43a047', '#9e9e9e']
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 笔 ({d}%)' },
    legend: { bottom: 0, icon: 'circle' },
    color: colors,
    series: [
      {
        name: '订单状态',
        type: 'pie',
        radius: ['42%', '66%'],
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}\n{d}%', color: '#606266', fontSize: 12 },
        data: list.map((p) => ({ name: p.name, value: p.value }))
      }
    ]
  }
})

async function load() {
  loading.value = true
  try {
    data.value = await dashboardApi.stats()
    adminStore.setPendingOrders(data.value.cards.pending_accept_orders)
  } catch (e) {
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
