/**
 * 小程序图片地址规则自测
 * 运行：node scripts/check-image-url.js
 *
 * 目的：把 utils/config.js 里的图片兜底规则做成可执行断言，
 *       保证「未设置图片 / 占位图名 / 加载失败 / 完整 URL / 正常文件名」
 *       五种输入都得到确定结果，避免以后再出现"所有菜品同一张图"的问题。
 *
 * 做法：读取 utils/config.js 源码，去掉 ESM 的 export 关键字后在沙箱里求值，
 *       直接调用真实的 imageUrl / avatarUrl / markImgFailed，不复制任何逻辑。
 */
const fs = require('fs')
const path = require('path')

const ROOT = path.resolve(__dirname, '..')
const CONFIG = path.join(ROOT, 'utils', 'config.js')

let src = fs.readFileSync(CONFIG, 'utf8')
src = src
  .replace(/^export\s+default\s+/m, 'const __default = ')
  .replace(/^export\s+(const|let|var|function)\s+/gm, '$1 ')
src +=
  '\nmodule.exports = { imageUrl, avatarUrl, markImgFailed, FALLBACK_FOOD_IMAGE, ' +
  'SERVER_FOOD_PLACEHOLDER, STATIC_BASE, DEFAULT_AVATAR };\n'

const mod = { exports: {} }
new Function('module', 'exports', src)(mod, mod.exports)
const C = mod.exports

const FALLBACK = C.FALLBACK_FOOD_IMAGE
const results = []
function eq(name, actual, expected) {
  const pass = actual === expected
  results.push({ name, pass, actual, expected })
}

eq('空字符串 → 本地兜底占位图', C.imageUrl(''), FALLBACK)
eq('null/undefined → 本地兜底占位图', C.imageUrl(undefined), FALLBACK)
eq('后端占位图名 → 本地兜底占位图', C.imageUrl(C.SERVER_FOOD_PLACEHOLDER), FALLBACK)
eq('加载失败标记 → 本地兜底占位图', C.imageUrl('abc123.png', true), FALLBACK)
eq('真实文件名 → STATIC_BASE + 文件名', C.imageUrl('abc123.png'), C.STATIC_BASE + 'abc123.png')
eq('完整 URL 原样返回', C.imageUrl('https://cdn.x.com/a.png'), 'https://cdn.x.com/a.png')
eq('头像空值 → 服务端 default_user.jpg',
  C.avatarUrl(''), C.STATIC_BASE + C.DEFAULT_AVATAR)

const item = { food_img: 'abc123.png' }
C.markImgFailed(item)
eq('markImgFailed 打标记', item.food_img_failed, true)
eq('打标记后 imageUrl 走兜底', C.imageUrl(item.food_img, item.food_img_failed), FALLBACK)
eq('markImgFailed 不破坏原字段', item.food_img, 'abc123.png')

const passed = results.filter((r) => r.pass).length
console.log('='.repeat(64))
console.log('  小程序 · 图片地址规则自测')
console.log('='.repeat(64))
console.log('  STATIC_BASE : ' + C.STATIC_BASE)
console.log('  兜底占位图  : ' + FALLBACK)
console.log('-'.repeat(64))
results.forEach((r) => {
  console.log(`  ${r.pass ? '[OK]  ' : '[FAIL]'} ${r.name}`)
  if (!r.pass) console.log(`         期望 ${r.expected}，实际 ${r.actual}`)
})
console.log('-'.repeat(64))
if (passed === results.length) {
  console.log(`  结果：${passed}/${results.length} 通过`)
  process.exit(0)
}
console.log(`  结果：${passed}/${results.length} 通过，存在失败项`)
process.exit(1)
