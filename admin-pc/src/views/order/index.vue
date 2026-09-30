<template>
  <div class="co-page">
    <div class="co-card">
      <div class="co-page-header">
        <div class="co-page-title">订单管理</div>
        <el-text type="info" size="small">
          状态机：0 待支付 → 1 待接单 → 2 配送中 → 3 已完成；0/1 → 4 已取消
        </el-text>
      </div>

      <div class="co-toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索订单号 / 学生昵称 / 手机号"
          clearable
          style="width: 280px"
          :prefix-icon="Search"
          @keyup.enter="search"
          @clear="search"
        />
        <el-select v-model="query.order_status" placeholder="全部状态" style="width: 150px" @change="search">
          <el-option
            v-for="o in statusOptions"
            :key="String(o.value)"
            :label="o.label"
            :value="o.value"
          />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px"
          @change="search"
        />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </div>

      <el-table :data="list" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="order_no" label="订单号" width="200" show-overflow-tooltip />
        <el-table-column label="学生" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.nickname }}</div>
            <div class="co-muted" style="font-size: 12px">{{ row.phone }}</div>
          </template>
        </el-table-column>
        <el-table-column label="订单金额" width="120" align="right">
          <template #default="{ row }">
            <span class="co-money">¥{{ Number(row.total_price).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="receive_address" label="收货地址" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.order_status)" size="small" effect="light">
              {{ row.status_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" width="180">
          <template #default="{ row }">
            <div>{{ row.created_at }}</div>
            <div class="co-muted" style="font-size: 12px" v-if="row.pay_time">
              支付 {{ row.pay_time }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-if="row.order_status === 1"
              link
              type="success"
              @click="receive(row)"
            >
              接单
            </el-button>
            <el-button
              v-if="row.order_status === 2"
              link
              type="success"
              @click="finish(row)"
            >
              完成
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="co-pagination">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="load"
          @size-change="search"
        />
      </div>
    </div>

    <!-- 订单详情 -->
    <el-drawer v-model="detailVisible" title="订单详情" size="520px">
      <div v-if="detail" class="detail">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
          <el-descriptions-item label="订单状态">
            <el-tag :type="statusTag(detail.order_status)" size="small" effect="light">
              {{ detail.status_text }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="下单学生">
            {{ detail.nickname }}（{{ detail.phone }}）
            <span v-if="detail.student_no" class="co-muted"> · {{ detail.student_no }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="收货地址">{{ detail.receive_address }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ detail.remark || '无' }}</el-descriptions-item>
          <el-descriptions-item label="订单金额">
            <span class="co-money">¥{{ Number(detail.total_price).toFixed(2) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
          <el-descriptions-item label="支付时间">{{ detail.pay_time || '—' }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ detail.finish_time || '—' }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail__title">商品明细</div>
        <el-table :data="detail.items" size="small" border>
          <el-table-column prop="food_name" label="菜品" min-width="140" show-overflow-tooltip />
          <el-table-column label="单价" width="100" align="right">
            <template #default="{ row }">¥{{ Number(row.food_price).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="count" label="数量" width="70" align="center" />
          <el-table-column label="小计" width="100" align="right">
            <template #default="{ row }">
              <span class="co-money">¥{{ Number(row.subtotal).toFixed(2) }}</span>
            </template>
          </el-table-column>
        </el-table>

        <div class="detail__actions">
          <el-button
            v-if="detail.order_status === 1"
            type="success"
            @click="receive(detail, true)"
          >
            接单（1 → 2）
          </el-button>
          <el-button
            v-if="detail.order_status === 2"
            type="success"
            @click="finish(detail, true)"
          >
            完成（2 → 3）
          </el-button>
          <el-text v-if="detail.order_status === 0" type="info" size="small">
            订单尚未支付，暂无可执行操作
          </el-text>
          <el-text v-if="detail.order_status === 4" type="info" size="small">
            订单已取消，库存已恢复
          </el-text>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { orderApi } from '@/api'
import { ORDER_STATUS_OPTIONS, ORDER_STATUS_TAG } from '@/config'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const detail = ref(null)
const detailVisible = ref(false)
const dateRange = ref([])

const statusOptions = ORDER_STATUS_OPTIONS
const query = reactive({ keyword: '', order_status: '', page: 1, page_size: 10 })

function statusTag(status) {
  return ORDER_STATUS_TAG[status] || 'info'
}

async function load() {
  loading.value = true
  try {
    const data = await orderApi.list({
      keyword: query.keyword || undefined,
      order_status: query.order_status === '' ? undefined : query.order_status,
      start_date: dateRange.value && dateRange.value[0] ? dateRange.value[0] : undefined,
      end_date: dateRange.value && dateRange.value[1] ? dateRange.value[1] : undefined,
      page: query.page,
      page_size: query.page_size
    })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (e) {
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function search() {
  query.page = 1
  load()
}

function reset() {
  query.keyword = ''
  query.order_status = ''
  query.page = 1
  query.page_size = 10
  dateRange.value = []
  load()
}

async function openDetail(row) {
  try {
    detail.value = await orderApi.detail(row.id)
    detailVisible.value = true
  } catch (e) {
    // 提示由拦截器处理
  }
}

function receive(row, fromDrawer) {
  ElMessageBox.confirm(
    `确认接收订单 ${row.order_no} 吗？（状态 待接单 → 配送中）`,
    '接单确认',
    { confirmButtonText: '确认接单', cancelButtonText: '取消', type: 'info' }
  )
    .then(async () => {
      await orderApi.receive(row.id)
      ElMessage.success('接单成功')
      if (fromDrawer) {
        detail.value = await orderApi.detail(row.id)
      }
      load()
    })
    .catch(() => {})
}

function finish(row, fromDrawer) {
  ElMessageBox.confirm(
    `确认完成订单 ${row.order_no} 吗？（状态 配送中 → 已完成，并累加菜品销量）`,
    '完成订单',
    { confirmButtonText: '确认完成', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      await orderApi.finish(row.id)
      ElMessage.success('订单已完成')
      if (fromDrawer) {
        detail.value = await orderApi.detail(row.id)
      }
      load()
    })
    .catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.detail__title {
  margin: 18px 0 10px;
  font-size: 15px;
  font-weight: 600;
}

.detail__actions {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
