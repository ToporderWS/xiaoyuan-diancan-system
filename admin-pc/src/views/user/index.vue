<template>
  <div class="co-page">
    <div class="co-card">
      <div class="co-page-header">
        <div class="co-page-title">学生用户</div>
        <el-text type="info" size="small">本页为只读视图，不提供修改学生资料的入口</el-text>
      </div>

      <div class="co-toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索昵称 / 手机号 / 学号 / 宿舍"
          clearable
          style="width: 320px"
          :prefix-icon="Search"
          @keyup.enter="search"
          @clear="search"
        />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </div>

      <el-table :data="list" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="72" align="center" />
        <el-table-column label="头像" width="78" align="center">
          <template #default="{ row }">
            <img class="co-avatar" :src="avatar(row.avatar)" alt="avatar" />
          </template>
        </el-table-column>
        <el-table-column prop="nickname" label="昵称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="student_no" label="学号" width="150">
          <template #default="{ row }">
            <span>{{ row.student_no || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="dormitory" label="宿舍" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.dormitory || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180" />
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

import { userApi } from '@/api'
import { DEFAULT_AVATAR, imageUrl } from '@/config'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ keyword: '', page: 1, page_size: 10 })

function avatar(name) {
  return imageUrl(name || DEFAULT_AVATAR)
}

async function load() {
  loading.value = true
  try {
    const data = await userApi.list({
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
