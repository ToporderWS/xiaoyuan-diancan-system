/**
 * 小程序工程静态自检脚本
 * 运行：npm run check       （node scripts/check-project.js）
 *
 * 检查项：
 *  1. pages.json / manifest.json 是否为合法 JSON
 *  2. pages.json 中每个页面路径是否存在对应 .vue 文件
 *  3. pages/ 目录下是否存在未注册的页面
 *  4. TabBar 是否 4 项、字段齐全、图标文件真实存在
 *  5. 接口地址是否只在 utils/config.js 中硬编码
 *  6. 是否绕过统一请求层直接使用 uni.request / uni.uploadFile
 *  7. 是否误用 admin_token（学生端与后台 Token Key 必须隔离）
 *  8. api/index.js 中出现的接口路径是否都在后端白名单内
 *  9. 源码中是否存在 TODO / FIXME / 占位实现
 * 10. 每个 .vue 文件是否同时包含 template 与 script 块
 */
const fs = require('fs')
const path = require('path')

const ROOT = path.resolve(__dirname, '..')
const errors = []
const warnings = []
const stats = { pages: 0, vueFiles: 0, jsFiles: 0, apiCalls: 0 }

// 工程根目录下不参与源码扫描的目录：
// unpackage 是 HBuilderX 的编译产物（含第三方库代码，天然带 TODO 字样且地址已被编译内联），
// 对它做「硬编码地址 / 未完成标记」检查只会产生假阳性，故整体跳过。
const SKIP_ROOT_DIRS = new Set([
  'unpackage', 'node_modules', 'dist', '.git', '.hbuilderx', '.hbuilderx_temp', '.idea'
])

// 后端实际提供的接口白名单（与 backend/routes 严格对应）
const API_WHITELIST = [
  '/user/register', '/user/login', '/user/info', '/user/update_info',
  '/user/update_pwd', '/user/upload_avatar', '/user/logout',
  '/food/category/list', '/food/list',
  '/cart/list', '/cart/save', '/cart/del',
  '/order/create', '/order/my_list', '/order/detail', '/order/cancel', '/order/pay',
  '/notice/list'
]

function readJSON(rel) {
  const file = path.join(ROOT, rel)
  if (!fs.existsSync(file)) {
    errors.push(`缺少文件：${rel}`)
    return null
  }
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'))
  } catch (e) {
    errors.push(`${rel} 不是合法 JSON：${e.message}`)
    return null
  }
}

function walk(dir, out = []) {
  const abs = path.join(ROOT, dir)
  if (!fs.existsSync(abs)) return out
  const atRoot = dir === '.'
  for (const name of fs.readdirSync(abs)) {
    // 只跳过工程根目录下的编译产物 / 依赖目录
    if (atRoot && SKIP_ROOT_DIRS.has(name)) continue
    const rel = path.join(dir, name)
    const stat = fs.statSync(path.join(ROOT, rel))
    if (stat.isDirectory()) walk(rel, out)
    else out.push(rel.split(path.sep).join('/'))
  }
  return out
}

// ---------- 1. JSON 合法性 ----------
const pagesJson = readJSON('pages.json')
const manifestJson = readJSON('manifest.json')
if (manifestJson && manifestJson.vueVersion !== '3') {
  errors.push('manifest.json 的 vueVersion 必须为 "3"')
}

// ---------- 2/3. 页面注册与实际文件一致 ----------
if (pagesJson) {
  const declared = pagesJson.pages.map((p) => p.path)
  stats.pages = declared.length
  declared.forEach((p) => {
    const file = p + '.vue'
    if (!fs.existsSync(path.join(ROOT, file))) errors.push(`pages.json 声明了不存在的页面：${file}`)
  })
  const actual = walk('pages').filter((f) => f.endsWith('.vue'))
  stats.vueFiles = actual.length
  actual.forEach((f) => {
    const p = f.replace(/\.vue$/, '')
    if (!declared.includes(p)) errors.push(`pages/${p}.vue 未在 pages.json 中注册`)
  })
  // 页面路径重复
  const dup = declared.filter((p, i) => declared.indexOf(p) !== i)
  if (dup.length) errors.push(`pages.json 存在重复页面路径：${dup.join(', ')}`)
}

// ---------- 4. TabBar ----------
const EXPECTED_TABS = [
  'pages/index/index',
  'pages/cart/cart',
  'pages/order/list',
  'pages/my/my'
]
if (pagesJson && pagesJson.tabBar) {
  const list = pagesJson.tabBar.list || []
  if (list.length !== 4) errors.push(`TabBar 必须为 4 项，当前 ${list.length} 项`)
  const paths = list.map((t) => t.pagePath)
  EXPECTED_TABS.forEach((p, i) => {
    if (paths[i] !== p) errors.push(`TabBar 第 ${i + 1} 项应为 ${p}，实际 ${paths[i]}`)
  })
  list.forEach((t) => {
    ;['text', 'iconPath', 'selectedIconPath'].forEach((k) => {
      if (!t[k]) errors.push(`TabBar「${t.pagePath}」缺少字段 ${k}`)
    })
    ;[t.iconPath, t.selectedIconPath].forEach((icon) => {
      if (icon && !fs.existsSync(path.join(ROOT, icon))) {
        errors.push(`TabBar 图标不存在：${icon}`)
      }
    })
  })
  const need = ['color', 'selectedColor', 'backgroundColor']
  need.forEach((k) => {
    if (!pagesJson.tabBar[k]) errors.push(`TabBar 缺少样式字段 ${k}`)
  })
} else if (pagesJson) {
  errors.push('pages.json 缺少 tabBar 配置')
}

// ---------- 5~7. 源码扫描 ----------
const jsFiles = walk('.').filter(
  (f) => (f.endsWith('.js') || f.endsWith('.vue')) && !f.startsWith('scripts/')
)
stats.jsFiles = jsFiles.length

jsFiles.forEach((f) => {
  const src = fs.readFileSync(path.join(ROOT, f), 'utf8')

  // 5. 硬编码后端地址
  if (f !== 'utils/config.js') {
    if (/https?:\/\/\d{1,3}(\.\d{1,3}){3}(:\d+)?/.test(src)) {
      errors.push(`${f} 中出现硬编码后端地址，应统一使用 utils/config.js`)
    }
  } else {
    if (!/BASE_URL/.test(src) || !/STATIC_BASE/.test(src)) {
      errors.push('utils/config.js 必须导出 BASE_URL 与 STATIC_BASE')
    }
  }

  // 6. 绕过统一请求层
  if (f !== 'utils/request.js' && f !== 'scripts/check-project.js') {
    if (/\buni\.request\s*\(/.test(src)) errors.push(`${f} 直接调用 uni.request，应使用 utils/request.js`)
    if (/\buni\.uploadFile\s*\(/.test(src)) {
      errors.push(`${f} 直接调用 uni.uploadFile，应使用 utils/request.js 的 upload()`)
    }
  }

  // 7. Token Key 隔离
  if (/admin_token/.test(src)) errors.push(`${f} 出现 admin_token，学生端必须使用 student_token`)

  // 9. 占位/未完成标记
  const marks = src.match(/\b(TODO|FIXME|XXX|HACK)\b|此处省略|其他类似|请自行实现|示例代码/g)
  if (marks) errors.push(`${f} 包含未完成标记：${[...new Set(marks)].join(', ')}`)

  // 10. .vue 结构（App.vue 为 uni-app 应用根组件，按规范不含 template）
  if (f.endsWith('.vue')) {
    if (f !== 'App.vue' && !/<template>[\s\S]*<\/template>/.test(src)) {
      errors.push(`${f} 缺少 <template> 块`)
    }
    if (!/<script>[\s\S]*<\/script>/.test(src)) errors.push(`${f} 缺少 <script> 块`)
    if (!/<style>[\s\S]*<\/style>/.test(src)) warnings.push(`${f} 未包含 <style> 块`)
  }

  // 8. 接口路径白名单（仅扫描 api/index.js 中的 http.get/http.post/upload 调用）
  if (f === 'api/index.js') {
    const re = /(?:http\.(?:get|post)|upload)\s*\(\s*(?:\{[^}]*url:\s*)?['"]([^'"]+)['"]/g
    let m
    while ((m = re.exec(src)) !== null) {
      stats.apiCalls += 1
      if (!API_WHITELIST.includes(m[1])) {
        errors.push(`api/index.js 使用了后端未提供的接口：${m[1]}`)
      }
    }
  }
})

// 统一请求层必须存在且实现 401 处理
const reqPath = path.join(ROOT, 'utils/request.js')
if (!fs.existsSync(reqPath)) {
  errors.push('缺少 utils/request.js')
} else {
  const reqSrc = fs.readFileSync(reqPath, 'utf8')
  ;['BASE_URL', 'Authorization', 'student_token', '401', 'handleUnauthorized'].forEach((k) => {
    if (!reqSrc.includes(k)) errors.push(`utils/request.js 缺少关键实现：${k}`)
  })
}

// ---------- 输出 ----------
console.log('='.repeat(64))
console.log('  校园点餐小程序 · 工程静态自检')
console.log('='.repeat(64))
console.log(`  已注册页面 : ${stats.pages}`)
console.log(`  .vue 文件  : ${stats.vueFiles}`)
console.log(`  扫描源码   : ${stats.jsFiles}`)
console.log(`  接口调用   : ${stats.apiCalls}（均在后端白名单内）`)
console.log(`  TabBar     : ${pagesJson && pagesJson.tabBar ? pagesJson.tabBar.list.length : 0} 项`)
console.log('-'.repeat(64))

if (warnings.length) {
  console.log(`  [警告] ${warnings.length} 条`)
  warnings.forEach((w) => console.log('    - ' + w))
}
if (errors.length) {
  console.log(`  [错误] ${errors.length} 条`)
  errors.forEach((e) => console.log('    x ' + e))
  console.log('-'.repeat(64))
  console.log('  结果：FAILED')
  process.exit(1)
}
console.log('  结果：PASSED —— 页面注册、TabBar、请求层、接口白名单、占位标记全部通过')
process.exit(0)
