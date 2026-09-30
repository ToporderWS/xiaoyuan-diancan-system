<template>
  <div class="co-page">
    <div class="co-card">
      <div class="co-page-header">
        <div class="co-page-title">菜品分类</div>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增分类</el-button>
      </div>

      <div class="co-toolbar">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="分类下存在菜品时无法删除，系统会返回业务错误并阻止产生脏数据"
        />
      </div>

      <el-table :data="list" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="72" align="center" />
        <el-table-column prop="cat_name" label="分类名称" min-width="180" />
        <el-table-column prop="sort" label="排序" width="100" align="center" />
        <el-table-column label="是否启用" width="130" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_show === 1"
              @change="(val) => toggleShow(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_show === 1 ? 'success' : 'info'" size="small" effect="light">
              {{ row.is_show === 1 ? '启用中' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增 / 编辑 -->
    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑分类' : '新增分类'"
      width="440px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="分类名称" prop="cat_name">
          <el-input v-model="form.cat_name" maxlength="50" placeholder="如：快餐" show-word-limit />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="9999" controls-position="right" />
          <span class="co-muted" style="margin-left: 10px; font-size: 12px">数值升序排列</span>
        </el-form-item>
        <el-form-item label="是否启用" prop="is_show">
          <el-switch v-model="form.is_show" :active-value="1" :inactive-value="0" />
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
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { categoryApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const dialogVisible = ref(false)
const formRef = ref(null)

const form = reactive({ id: null, cat_name: '', sort: 0, is_show: 1 })

const rules = {
  cat_name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { max: 50, message: '分类名称不能超过 50 个字符', trigger: 'blur' }
  ]
}

async function load() {
  loading.value = true
  try {
    const data = await categoryApi.list()
    list.value = data.list || []
  } catch (e) {
    list.value = []
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.id = null
  form.cat_name = ''
  form.sort = 0
  form.is_show = 1
  if (formRef.value) formRef.value.clearValidate()
}

function openCreate() {
  resetForm()
  // 默认排序值取当前最大排序 +1
  const maxSort = list.value.reduce((m, i) => Math.max(m, Number(i.sort) || 0), 0)
  form.sort = maxSort + 1
  dialogVisible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.cat_name = row.cat_name
  form.sort = row.sort
  form.is_show = row.is_show
  dialogVisible.value = true
}

function submit() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await categoryApi.save({
        id: form.id || undefined,
        cat_name: form.cat_name.trim(),
        sort: form.sort,
        is_show: form.is_show
      })
      ElMessage.success('保存成功')
      dialogVisible.value = false
      load()
    } catch (e) {
      // 错误提示由拦截器处理
    } finally {
      saving.value = false
    }
  })
}

async function toggleShow(row, val) {
  try {
    await categoryApi.save({
      id: row.id,
      cat_name: row.cat_name,
      sort: row.sort,
      is_show: val ? 1 : 0
    })
    ElMessage.success(val ? '已启用' : '已禁用')
    load()
  } catch (e) {
    load()
  }
}

function remove(row) {
  ElMessageBox.confirm(
    `确定要删除分类「${row.cat_name}」吗？若该分类下仍有菜品，删除将被系统拒绝。`,
    '删除分类',
    { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      await categoryApi.del(row.id)
      ElMessage.success('删除成功')
      load()
    })
    .catch(() => {})
}

onMounted(load)
</script>
