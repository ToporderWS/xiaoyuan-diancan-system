<template>
  <div class="co-page">
    <div class="co-card">
      <div class="co-page-header">
        <div class="co-page-title">公告管理</div>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增公告</el-button>
      </div>

      <div class="co-toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索公告标题 / 内容"
          clearable
          style="width: 300px"
          :prefix-icon="Search"
          @keyup.enter="search"
          @clear="search"
        />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
        <el-text type="info" size="small">小程序端仅展示「显示中」的公告，按发布时间倒序</el-text>
      </div>

      <el-table :data="list" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="72" align="center" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.content || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="publish_time" label="发布时间" width="180" />
        <el-table-column label="是否显示" width="120" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.is_show === 1" @change="(val) => toggleShow(row, val)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
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

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑公告' : '新增公告'"
      width="560px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="公告标题" prop="title">
          <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="请输入公告标题" />
        </el-form-item>
        <el-form-item label="公告内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            maxlength="5000"
            show-word-limit
            placeholder="请输入公告内容"
          />
        </el-form-item>
        <el-form-item label="是否显示">
          <el-switch v-model="form.is_show" :active-value="1" :inactive-value="0" />
          <span class="co-muted" style="margin-left: 10px; font-size: 12px">
            关闭后小程序端不可见
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { noticeApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref(null)
const query = reactive({ keyword: '', page: 1, page_size: 10 })
const form = reactive({ id: null, title: '', content: '', is_show: 1 })

const rules = {
  title: [
    { required: true, message: '请输入公告标题', trigger: 'blur' },
    { max: 200, message: '标题不能超过 200 个字符', trigger: 'blur' }
  ]
}

async function load() {
  loading.value = true
  try {
    const data = await noticeApi.list({
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

function resetForm() {
  form.id = null
  form.title = ''
  form.content = ''
  form.is_show = 1
  if (formRef.value) formRef.value.clearValidate()
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.title = row.title
  form.content = row.content || ''
  form.is_show = row.is_show
  dialogVisible.value = true
}

function submit() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await noticeApi.save({
        id: form.id || undefined,
        title: form.title.trim(),
        content: form.content || '',
        is_show: form.is_show
      })
      ElMessage.success('保存成功')
      dialogVisible.value = false
      load()
    } catch (e) {
      // 提示由拦截器处理
    } finally {
      saving.value = false
    }
  })
}

async function toggleShow(row, val) {
  try {
    await noticeApi.save({
      id: row.id,
      title: row.title,
      content: row.content || '',
      is_show: val ? 1 : 0
    })
    ElMessage.success(val ? '已显示' : '已隐藏')
    load()
  } catch (e) {
    load()
  }
}

function remove(row) {
  ElMessageBox.confirm(`确定要删除公告「${row.title}」吗？`, '删除公告', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(async () => {
      await noticeApi.del(row.id)
      ElMessage.success('删除成功')
      load()
    })
    .catch(() => {})
}

onMounted(load)
</script>
