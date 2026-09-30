<template>
  <div class="co-page">
    <div class="co-card">
      <div class="co-page-header">
        <div class="co-page-title">菜品管理</div>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增菜品</el-button>
      </div>

      <div class="co-toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索菜品名称 / 描述"
          clearable
          style="width: 260px"
          :prefix-icon="Search"
          @keyup.enter="search"
          @clear="search"
        />
        <el-select v-model="query.cat_id" placeholder="全部分类" clearable style="width: 170px" @change="search">
          <el-option v-for="c in categories" :key="c.id" :label="c.cat_name" :value="c.id" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </div>

      <el-table :data="list" v-loading="loading" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column label="图片" width="86" align="center">
          <template #default="{ row }">
            <el-image
              class="co-thumb"
              :src="img(row.food_img)"
              :preview-src-list="[img(row.food_img)]"
              preview-teleported
              fit="cover"
            >
              <template #error>
                <img class="co-thumb" :src="fallbackImg" alt="food" />
              </template>
            </el-image>
          </template>
        </el-table-column>
        <el-table-column prop="food_name" label="菜品名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="cat_name" label="分类" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.cat_name || '—' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="价格" width="110" align="right">
          <template #default="{ row }">
            <span class="co-money">¥{{ Number(row.price).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="库存" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.stock <= 3 ? '#fb8c00' : 'inherit', fontWeight: row.stock <= 3 ? 600 : 400 }">
              {{ row.stock }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="sales" label="销量" width="90" align="center" />
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_sale === 1"
              active-text=""
              @change="(val) => toggleSale(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="editStock(row)">改库存</el-button>
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

    <!-- 新增 / 编辑 -->
    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑菜品' : '新增菜品'"
      width="620px"
      @closed="onDialogClosed"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
        <el-form-item label="菜品名称" prop="food_name">
          <el-input v-model="form.food_name" maxlength="100" placeholder="请输入菜品名称" />
        </el-form-item>
        <el-form-item label="所属分类" prop="cat_id">
          <el-select v-model="form.cat_id" placeholder="请选择分类" style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.cat_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="单价（元）" prop="price">
          <el-input-number
            v-model="form.price"
            :min="0"
            :max="999999"
            :precision="2"
            :step="0.5"
            controls-position="right"
            style="width: 200px"
          />
          <span class="co-muted" style="margin-left: 10px; font-size: 12px">不得为负数</span>
        </el-form-item>
        <el-form-item label="库存" prop="stock">
          <el-input-number
            v-model="form.stock"
            :min="0"
            :max="999999"
            :precision="0"
            controls-position="right"
            style="width: 200px"
          />
          <span class="co-muted" style="margin-left: 10px; font-size: 12px">不得为负数</span>
        </el-form-item>
        <el-form-item label="菜品描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="2000"
            show-word-limit
            placeholder="请输入菜品描述"
          />
        </el-form-item>
        <el-form-item label="是否上架">
          <el-switch v-model="form.is_sale" :active-value="1" :inactive-value="0" />
          <span class="co-muted" style="margin-left: 10px; font-size: 12px">
            下架后小程序端不可见
          </span>
        </el-form-item>
        <el-form-item label="菜品图片">
          <div class="uploader">
            <el-image class="uploader__preview" :src="previewUrl" fit="cover">
              <template #error>
                <img class="uploader__preview" :src="fallbackImg" alt="food" />
              </template>
            </el-image>
            <div class="uploader__side">
              <input
                ref="fileInput"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                style="display: none"
                @change="onFileChange"
              />
              <el-button size="small" @click="pickFile">选择图片</el-button>
              <el-button v-if="pickedFile" size="small" text type="danger" @click="clearFile">
                撤销选择
              </el-button>
              <div class="co-muted uploader__tip">
                支持 jpg / jpeg / png / webp，单张不超过 2MB；<br />
                保存时与菜品信息一并提交（multipart/form-data）。
              </div>
            </div>
          </div>
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
import { computed, onMounted, reactive, ref } from 'vue'

import { categoryApi, foodApi } from '@/api'
import { FALLBACK_FOOD_IMAGE_URL, imageUrl } from '@/config'

const MAX_SIZE = 2 * 1024 * 1024
const ALLOWED_EXT = ['jpg', 'jpeg', 'png', 'webp']
const fallbackImg = FALLBACK_FOOD_IMAGE_URL

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const categories = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref(null)
const fileInput = ref(null)
const pickedFile = ref(null)
const pickedPreview = ref('')

const query = reactive({ keyword: '', cat_id: '', page: 1, page_size: 10 })

const form = reactive({
  id: null,
  cat_id: '',
  food_name: '',
  price: 0,
  stock: 0,
  description: '',
  is_sale: 1,
  food_img: ''
})

const rules = {
  food_name: [
    { required: true, message: '请输入菜品名称', trigger: 'blur' },
    { max: 100, message: '菜品名称不能超过 100 个字符', trigger: 'blur' }
  ],
  cat_id: [{ required: true, message: '请选择所属分类', trigger: 'change' }],
  price: [
    { required: true, message: '请输入单价', trigger: 'blur' },
    {
      validator: (rule, value, cb) => {
        if (value === null || value === undefined || Number(value) < 0) {
          cb(new Error('单价不能为负数'))
        } else cb()
      },
      trigger: 'blur'
    }
  ],
  stock: [
    { required: true, message: '请输入库存', trigger: 'blur' },
    {
      validator: (rule, value, cb) => {
        if (value === null || value === undefined || Number(value) < 0) {
          cb(new Error('库存不能为负数'))
        } else cb()
      },
      trigger: 'blur'
    }
  ]
}

const previewUrl = computed(() => pickedPreview.value || img(form.food_img))

function img(name) {
  return imageUrl(name, 'food-default.jpg')
}

async function loadCategories() {
  try {
    const data = await categoryApi.list()
    categories.value = data.list || []
  } catch (e) {
    categories.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const data = await foodApi.list({
      keyword: query.keyword || undefined,
      cat_id: query.cat_id || undefined,
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
  query.cat_id = ''
  query.page = 1
  query.page_size = 10
  load()
}

function resetForm() {
  form.id = null
  form.cat_id = categories.value.length ? categories.value[0].id : ''
  form.food_name = ''
  form.price = 0
  form.stock = 0
  form.description = ''
  form.is_sale = 1
  form.food_img = ''
  pickedFile.value = null
  pickedPreview.value = ''
  if (formRef.value) formRef.value.clearValidate()
}

function onDialogClosed() {
  resetForm()
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  resetForm()
  form.id = row.id
  form.cat_id = row.cat_id
  form.food_name = row.food_name
  form.price = Number(row.price)
  form.stock = Number(row.stock)
  form.description = row.description || ''
  form.is_sale = row.is_sale
  form.food_img = row.food_img
  dialogVisible.value = true
}

function pickFile() {
  if (fileInput.value) fileInput.value.click()
}

function clearFile() {
  pickedFile.value = null
  pickedPreview.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function onFileChange(event) {
  const file = event.target.files && event.target.files[0]
  if (!file) return
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  if (!ALLOWED_EXT.includes(ext)) {
    ElMessage.error('仅支持 jpg / jpeg / png / webp 格式图片')
    clearFile()
    return
  }
  if (file.size > MAX_SIZE) {
    ElMessage.error('图片大小不能超过 2MB')
    clearFile()
    return
  }
  pickedFile.value = file
  pickedPreview.value = URL.createObjectURL(file)
}

function submit() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    if (Number(form.price) < 0) {
      ElMessage.error('价格不能为负数')
      return
    }
    if (Number(form.stock) < 0) {
      ElMessage.error('库存不能为负数')
      return
    }
    saving.value = true
    try {
      await foodApi.save(
        {
          id: form.id || undefined,
          cat_id: form.cat_id,
          food_name: form.food_name.trim(),
          price: Number(form.price).toFixed(2),
          stock: Number(form.stock),
          description: form.description || '',
          is_sale: form.is_sale
        },
        pickedFile.value
      )
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

async function toggleSale(row, val) {
  try {
    await foodApi.save({
      id: row.id,
      cat_id: row.cat_id,
      food_name: row.food_name,
      price: Number(row.price).toFixed(2),
      stock: Number(row.stock),
      description: row.description || '',
      is_sale: val ? 1 : 0
    })
    ElMessage.success(val ? '已上架' : '已下架')
    load()
  } catch (e) {
    load()
  }
}

function editStock(row) {
  ElMessageBox.prompt('请输入新的库存数量（不能为负数）', `调整库存 · ${row.food_name}`, {
    confirmButtonText: '保存',
    cancelButtonText: '取消',
    inputValue: String(row.stock),
    inputPattern: /^\d{1,6}$/,
    inputErrorMessage: '库存必须为 0 - 999999 的整数'
  })
    .then(async ({ value }) => {
      await foodApi.save({
        id: row.id,
        cat_id: row.cat_id,
        food_name: row.food_name,
        price: Number(row.price).toFixed(2),
        stock: Number(value),
        description: row.description || '',
        is_sale: row.is_sale
      })
      ElMessage.success('库存已更新')
      load()
    })
    .catch(() => {})
}

function remove(row) {
  ElMessageBox.confirm(
    `确定要删除菜品「${row.food_name}」吗？历史订单明细为快照数据，不受影响。`,
    '删除菜品',
    { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      await foodApi.del(row.id)
      ElMessage.success('删除成功')
      load()
    })
    .catch(() => {})
}

onMounted(async () => {
  await loadCategories()
  await load()
})
</script>

<style scoped>
.uploader {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.uploader__preview {
  width: 92px;
  height: 92px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  background-color: #fff1f0;
  flex-shrink: 0;
}

.uploader__side {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.uploader__tip {
  font-size: 12px;
  line-height: 1.7;
}
</style>
