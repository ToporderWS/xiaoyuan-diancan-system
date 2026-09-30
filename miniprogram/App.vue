<script>
import { STORAGE_KEY } from './utils/config.js'

export default {
  onLaunch() {
    // 学生端只读写 student_token，与 PC 后台的 Token Key 完全隔离
    if (!uni.getStorageSync(STORAGE_KEY.TOKEN)) {
      console.log('[校园点餐] 当前为未登录状态，可浏览菜品')
    }
  },
  onShow() {},
  onHide() {}
}
</script>

<style>
/* ============================================================
   校园点餐 · 全局设计系统
   品牌色只用于主按钮 / 选中态 / 价格 / 少量强调；
   页面主体以白色与暖灰白为主，避免大面积铺红。
   所有页面统一复用下方公共类，禁止各页面自行发明卡片与按钮。
   ============================================================ */

page {
  /* ---------- 色彩令牌（颜色用变量，尺寸用公共类，保证小程序端兼容） ---------- */
  --co-primary: #e53935;
  --co-primary-soft: #fff1ef;
  --co-primary-line: #fbd9d5;
  --co-text: #1f1d1b;
  --co-text-2: #6e6864;
  --co-text-3: #a29b96;
  --co-text-4: #b8b2ad;
  --co-line: #f0eeec;
  --co-line-soft: #f4f2f0;
  --co-line-strong: #cfcac6;
  --co-bg: #f7f6f4;
  --co-card: #ffffff;
  --co-media-bg: #f4f1ee;
  --co-success: #3f9159;
  --co-info: #3a7bb5;
  --co-warning: #d98324;
  --co-disable: #eae7e4;

  background-color: var(--co-bg);
  color: var(--co-text);
  font-size: 28rpx;
  line-height: 1.5;
  font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC',
    'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
}

view,
text,
image,
scroll-view,
input,
textarea,
button,
swiper,
swiper-item {
  box-sizing: border-box;
}

/* ============================ 页面容器 ============================ */
.co-page {
  min-height: 100vh;
  background-color: var(--co-bg);
}

/* 底部安全区（iPhone 刘海屏 / Home Indicator） */
.co-safe-bottom {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

/* ============================ 卡片 ============================ */
.co-card {
  background-color: var(--co-card);
  border-radius: 24rpx;
  padding: 28rpx;
  margin: 0 24rpx 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(31, 26, 22, 0.04);
}

.co-card--flush {
  padding: 0 28rpx;
}

.co-card__title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 30rpx;
  font-weight: 600;
  color: var(--co-text);
  margin-bottom: 8rpx;
}

.co-card__sub {
  font-size: 24rpx;
  font-weight: 400;
  color: var(--co-text-3);
}

/* 区块标题（页面级） */
.co-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30rpx 32rpx 16rpx;
}

.co-section__title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--co-text);
  letter-spacing: 0.5rpx;
}

.co-section__extra {
  font-size: 24rpx;
  color: var(--co-text-3);
}

/* ============================ 按钮 ============================ */
.co-btn {
  height: 88rpx;
  line-height: 88rpx;
  padding: 0 48rpx;
  border-radius: 44rpx;
  background-color: var(--co-primary);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 500;
  text-align: center;
}

.co-btn--ghost {
  background-color: var(--co-card);
  color: var(--co-primary);
  border: 2rpx solid var(--co-primary-line);
  line-height: 84rpx;
}

.co-btn--plain {
  background-color: var(--co-card);
  color: var(--co-text-2);
  border: 2rpx solid var(--co-line);
  line-height: 84rpx;
}

.co-btn--disabled,
.co-btn[disabled] {
  background-color: var(--co-disable);
  color: var(--co-text-3);
}

.co-btn--sm {
  height: 68rpx;
  line-height: 68rpx;
  padding: 0 32rpx;
  font-size: 26rpx;
  border-radius: 34rpx;
}

/* 点按反馈 */
.co-btn:active,
.co-tap:active {
  opacity: 0.82;
}

/* ============================ 价格 ============================ */
.co-price {
  color: var(--co-primary);
  font-weight: 700;
}

.co-price__symbol {
  font-size: 22rpx;
  font-weight: 600;
  margin-right: 2rpx;
}

/* ============================ 标签 ============================ */
.co-tag {
  display: inline-block;
  padding: 2rpx 14rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
  line-height: 1.6;
  background-color: var(--co-primary-soft);
  color: var(--co-primary);
}

.co-tag--gray {
  background-color: var(--co-line-soft);
  color: var(--co-text-3);
}

/* ============================ 列表行 ============================ */
.co-row {
  display: flex;
  align-items: center;
  min-height: 104rpx;
  border-bottom: 2rpx solid var(--co-line-soft);
}

.co-row:last-child {
  border-bottom: none;
}

.co-row__label {
  font-size: 29rpx;
  color: var(--co-text);
  flex-shrink: 0;
}

.co-row__value {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 27rpx;
  color: var(--co-text-2);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* ============================ 图标 ============================ */
.co-ico {
  width: 40rpx;
  height: 40rpx;
  flex-shrink: 0;
}

.co-ico--sm {
  width: 32rpx;
  height: 32rpx;
}

/* ============================ 统一空状态 ============================
   结构固定：插画 → 标题 → 说明 → 主按钮；整体在内容区水平居中、垂直居中偏上。
   各业务只换插画与文案，布局规则不再各写一份。
   ================================================================= */
.co-empty-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  /* 垂直居中偏上：扣掉可能的页面标题/TabBar 占位，避免整体贴顶或沉底 */
  min-height: calc(100vh - 260rpx);
  padding: 0 60rpx;
}

.co-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  width: 100%;
}

.co-empty__art {
  width: 232rpx;
  height: 232rpx;
  display: block;
}

.co-empty__title {
  margin-top: 30rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: var(--co-text);
}

.co-empty__desc {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: var(--co-text-3);
  line-height: 1.65;
}

.co-empty__btn {
  margin-top: 46rpx;
  min-width: 300rpx;
  height: 80rpx;
  line-height: 80rpx;
  padding: 0 56rpx;
  border-radius: 40rpx;
  background-color: var(--co-primary);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 500;
  text-align: center;
}

.co-empty__btn--ghost {
  background-color: var(--co-card);
  color: var(--co-primary);
  border: 2rpx solid var(--co-primary-line);
  line-height: 76rpx;
}

/* ============================ 加载 / 列表尾 ============================ */
.co-loading {
  padding: 40rpx 0;
  text-align: center;
  font-size: 24rpx;
  color: var(--co-text-3);
}

.co-loadmore {
  text-align: center;
  font-size: 24rpx;
  color: var(--co-text-4);
  padding: 16rpx 0 40rpx;
}

/* ============================ 底部操作栏 ============================ */
.co-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 30;
  background-color: var(--co-card);
  /* 与白色内容区明确分界（订单详情等信息密集页尤其需要） */
  border-top: 2rpx solid var(--co-line-soft);
  box-shadow: 0 -2rpx 16rpx rgba(31, 26, 22, 0.05);
  padding: 16rpx 24rpx;
  padding-bottom: calc(16rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
  display: flex;
  align-items: center;
}

/* tabBar 页面的底栏变体：原生 TabBar 已处理安全区，这里不再重复补偿 */
.co-bar--tabbar {
  padding-bottom: 16rpx;
}

/* ============================ 数量步进器 ============================ */
.co-stepper {
  display: flex;
  align-items: center;
}

.co-stepper__btn {
  width: 52rpx;
  height: 52rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid var(--co-disable);
  background-color: var(--co-card);
}

.co-stepper__btn--plus {
  background-color: var(--co-primary);
  border-color: var(--co-primary);
}

.co-stepper__btn--disabled {
  opacity: 0.4;
}

.co-stepper__btn .co-ico {
  width: 28rpx;
  height: 28rpx;
}

.co-stepper__num {
  min-width: 66rpx;
  text-align: center;
  font-size: 28rpx;
  color: var(--co-text);
}

/* ============================ 复选 ============================ */
.co-check {
  width: 34rpx;
  height: 34rpx;
  border-radius: 50%;
  border: 2rpx solid var(--co-line-strong);
  display: flex;
  align-items: center;
  justify-content: center;
}

.co-check--on {
  background-color: var(--co-primary);
  border-color: var(--co-primary);
}

.co-check .co-ico {
  width: 22rpx;
  height: 22rpx;
}

/* ============================ 弹层 ============================ */
.co-mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background-color: rgba(24, 20, 18, 0.45);
  z-index: 60;
  display: flex;
  align-items: flex-end;
}

.co-sheet {
  width: 100%;
  background-color: var(--co-card);
  border-radius: 32rpx 32rpx 0 0;
  padding: 32rpx 32rpx 40rpx;
  padding-bottom: calc(40rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
}

.co-sheet__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20rpx;
}

.co-sheet__title {
  font-size: 34rpx;
  font-weight: 700;
  color: var(--co-text);
}

/* 表单字段（登录 / 注册 / 资料 / 密码 统一） */
.co-field {
  display: flex;
  align-items: center;
  min-height: 108rpx;
  border-bottom: 2rpx solid var(--co-line-soft);
}

.co-field:last-child {
  border-bottom: none;
}

.co-field__label {
  width: 150rpx;
  flex-shrink: 0;
  font-size: 29rpx;
  color: var(--co-text);
}

.co-field__input {
  flex: 1;
  min-width: 0;
  height: 108rpx;
  font-size: 29rpx;
  color: var(--co-text);
}

.co-ph {
  color: var(--co-text-4);
}
</style>
