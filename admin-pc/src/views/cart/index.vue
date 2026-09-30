<template>
  <div class="co-page">
    <div class="co-card">
      <div class="co-page-header">
        <div class="co-page-title">购物车查看</div>
        <el-text type="info" size="small">
          只读视图：管理员不得修改学生购物车（原需求未授权）
        </el-text>
      </div>

      <div class="co-toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索学生昵称 / 手机号 / 学号 / 菜品"
          clearable
          style="width: 340px"
          :prefix-icon="Search"
          @keyup.enter="search"
          @clear="search"
        />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </div>

      <el-table :data="list" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="72" align="center" />
        <el-table-column label="菜品图" width="82" align="center">
          <template #default="{ row }">
            <img class="co-thumb" :src="img(row.food_img)" alt="food" @error="onImgError" />
          </template>
        </el-table-column>
        <el-table-column prop="food_name" label="菜品" min-width="150" show-overflow-tooltip />
        <el-table-column prop="cat_name" label="分类" width="100">
          <template #default="{ row }">
            <span>{{ row.cat_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="单价" width="110" align="right">
          <template #default="{ row }">
            <span class="co-money">¥{{ Number(row.price).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="count" label="数量" width="90" align="center" />
        <el-table-column label="小计" width="120" align="right">
          <template #default="{ row }">
            <span class="co-money">¥{{ Number(row.subtotal).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="学生" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.nickname }}</div>
            <div class="co-muted" style="font-size: 12px">
              {{ row.phone }}<span v-if="row.student_no"> · {{ row.student_no }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.valid" type="success" size="small" effect="light">可结算</el-tag>
            <el-tooltip v-else :content="row.invalid_reason" placement="top">
              <el-tag type="warning" size="small" effect="light">不可结算</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="加入时间" width="180" />
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
  </div>
</template>

<script setup>
import { Refresh, Search } from '@element-plus/icons-vue'
import { onMounted, reactive, ref } from 'vue'

import { cartApi } from '@/api'
import { imageUrl, onImgError } from '@/config'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ keyword: '', page: 1, page_size: 10 })

function img(name) {
  return imageUrl(name, 'food-default.jpg')
}

async function load() {
  loading.value = true
  try {
    const data = await cartApi.list({
      keyword: query.keyword || undefined,
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
  query.page = 1
  query.page_size = 10
  load()
}

onMounted(load)
</script>
