<template>
  <view class="co-page detail">
    <!-- ==================== 状态 ==================== -->
    <view class="co-card status" :class="'status--' + order.order_status">
      <view class="status__row">
        <view class="status__dot"></view>
        <text class="status__text">{{ order.status_text || '加载中' }}</text>
      </view>
      <text class="status__hint">{{ statusHint }}</text>
    </view>

    <!-- ==================== 配送信息 ==================== -->
    <view class="co-card">
      <view class="co-card__title"><text>配送信息</text></view>
      <view class="row">
        <text class="row__label">订单号</text>
        <text class="row__value row__value--mono">{{ order.order_no }}</text>
      </view>
      <view class="row">
        <text class="row__label">收货地址</text>
        <text class="row__value">{{ order.receive_address }}</text>
      </view>
      <view class="row">
        <text class="row__label">备注</text>
        <text class="row__value">{{ order.remark || '无' }}</text>
      </view>
    </view>

    <!-- ==================== 商品明细 ==================== -->
    <view class="co-card">
      <view class="co-card__title">
        <text>商品明细</text>
        <text class="co-card__sub">共 {{ itemCount }} 件</text>
      </view>
      <view class="goods__item" v-for="it in order.items" :key="it.id">
        <image
          class="goods__img"
          :src="imgUrl(it.food_img, it.food_img_failed)"
          mode="aspectFill"
          @error="onImgError(it)"
        />
        <view class="goods__body">
          <text class="goods__name">{{ it.food_name }}</text>
          <text class="goods__unit">单价 ¥{{ formatPrice(it.food_price) }} × {{ it.count }}</text>
        </view>
        <text class="co-price goods__sub">
          <text class="co-price__symbol">¥</text>{{ formatPrice(it.subtotal) }}
        </text>
      </view>
      <view class="total">
        <text class="total__label">订单总价</text>
        <text class="co-price total__value">
          <text class="co-price__symbol">¥</text>{{ formatPrice(order.total_price) }}
        </text>
      </view>
    </view>

    <!-- ==================== 时间轴 ==================== -->
    <view class="co-card">
      <view class="co-card__title"><text>时间轴</text></view>
      <view class="row">
        <text class="row__label">创建时间</text>
        <text class="row__value">{{ order.created_at || '-' }}</text>
      </view>
      <view class="row">
        <text class="row__label">支付时间</text>
        <text class="row__value">{{ order.pay_time || '-' }}</text>
      </view>
      <view class="row">
        <text class="row__label">完成时间</text>
        <text class="row__value">{{ order.finish_time || '-' }}</text>
      </view>
    </view>

    <!-- ==================== 待支付操作（含安全区） ==================== -->
    <view class="co-bar actionbar" v-if="order.can_pay || order.can_cancel">
      <view class="paynote" v-if="order.can_pay">
        <text>本按钮为模拟支付，仅将订单状态由「待支付」变更为「待接单」，不接入真实微信支付。</text>
      </view>
      <view class="actionbar__btns">
        <view class="co-btn co-btn--plain actionbar__ghost co-tap" v-if="order.can_cancel" @tap="cancel">
          取消订单
        </view>
        <view class="co-btn actionbar__main co-tap" v-if="order.can_pay" @tap="pay">
          确认支付（模拟）
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { orderApi } from '../../api/index.js'
import { imageUrl, markImgFailed } from '../../utils/config.js'
import { isLogin } from '../../utils/request.js'

const HINTS = {
  0: '请在 15 分钟内完成支付，超时订单将自动取消并恢复库存',
  1: '已支付成功，等待食堂接单',
  2: '食堂已接单，正在配送中，请留意取餐通知',
  3: '订单已完成，感谢使用校园点餐',
  4: '订单已取消，库存已恢复'
}

export default {
  data() {
    return {
      orderId: 0,
      order: { items: [] }
    }
  },
  computed: {
    statusHint() {
      const s = this.order.order_status
      if (s === undefined || s === null) return ''
      return HINTS[s] || ''
    },
    itemCount() {
      return (this.order.items || []).reduce((s, i) => s + Number(i.count || 0), 0)
    }
  },
  onLoad(options) {
    this.orderId = Number(options.order_id || 0)
    if (!isLogin()) {
      uni.showToast({ title: '请先登录', icon: 'none' })
      setTimeout(() => uni.navigateTo({ url: '/pages/login/login' }), 600)
      return
    }
    if (!this.orderId) {
      uni.showToast({ title: '订单参数错误', icon: 'none' })
      setTimeout(() => uni.navigateBack(), 800)
      return
    }
    this.load()
  },
  methods: {
    imgUrl: imageUrl,
    onImgError: markImgFailed,
    formatPrice(v) {
      return Number(v || 0).toFixed(2)
    },
    load() {
      return orderApi
        .detail(this.orderId)
        .then((d) => {
          this.order = d
        })
        .catch(() => {})
    },
    pay() {
      uni.showModal({
        title: '模拟支付',
        content: '确认对该订单执行「模拟支付」吗？\n（不产生真实扣款，仅用于功能演示）',
        confirmText: '确认支付',
        success: (res) => {
          if (!res.confirm) return
          orderApi
            .pay(this.orderId)
            .then(() => {
              uni.showToast({ title: '模拟支付成功', icon: 'success' })
              this.load()
            })
            .catch(() => this.load())
        }
      })
    },
    cancel() {
      uni.showModal({
        title: '取消订单',
        content: '取消后库存将恢复，确定要取消该订单吗？',
        success: (res) => {
          if (!res.confirm) return
          orderApi
            .cancel(this.orderId)
            .then(() => {
              uni.showToast({ title: '订单已取消', icon: 'success' })
              this.load()
            })
            .catch(() => this.load())
        }
      })
    }
  }
}
</script>

<style>
.detail {
  padding: 24rpx 0 340rpx;
}

/* ==================== 状态卡（去大红块，改白底 + 状态色点） ====================
   品牌红只出现在状态圆点与价格上，信息层级靠字重与色彩语义表达。 */
.status {
  background-color: var(--co-card);
}
.status__row {
  display: flex;
  align-items: center;
}
.status__dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background-color: var(--co-primary);
  flex-shrink: 0;
  margin-right: 14rpx;
}
.status__text {
  font-size: 38rpx;
  font-weight: 700;
  color: var(--co-text);
}
.status__hint {
  display: block;
  margin-top: 12rpx;
  padding-left: 30rpx;
  font-size: 24rpx;
  color: var(--co-text-3);
  line-height: 1.6;
}
.status--0 .status__dot {
  background-color: var(--co-warning);
}
.status--1 .status__dot {
  background-color: var(--co-primary);
}
.status--2 .status__dot {
  background-color: var(--co-info);
}
.status--3 .status__dot {
  background-color: var(--co-success);
}
.status--4 .status__dot {
  background-color: var(--co-text-4);
}

/* ==================== 信息行 ==================== */
.row {
  display: flex;
  align-items: flex-start;
  padding: 14rpx 0;
}
.row__label {
  width: 160rpx;
  flex-shrink: 0;
  font-size: 26rpx;
  color: var(--co-text-3);
}
.row__value {
  flex: 1;
  min-width: 0;
  font-size: 26rpx;
  color: var(--co-text);
  word-break: break-all;
}
.row__value--mono {
  letter-spacing: 1rpx;
}

/* ==================== 商品明细 ==================== */
.goods__item {
  display: flex;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 2rpx solid var(--co-line-soft);
}
.goods__item:last-child {
  border-bottom: none;
}
.goods__img {
  width: 108rpx;
  height: 108rpx;
  border-radius: 16rpx;
  background-color: var(--co-line-soft);
  flex-shrink: 0;
}
.goods__body {
  flex: 1;
  margin-left: 20rpx;
  min-width: 0;
}
.goods__name {
  display: block;
  font-size: 28rpx;
  color: var(--co-text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.goods__unit {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: var(--co-text-3);
}
.goods__sub {
  flex-shrink: 0;
  font-size: 30rpx;
  margin-left: 16rpx;
}
.total {
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  padding-top: 20rpx;
}
.total__label {
  font-size: 26rpx;
  color: var(--co-text-2);
  margin-right: 12rpx;
}
.total__value {
  font-size: 44rpx;
}

/* ==================== 底部操作栏 ==================== */
.actionbar {
  /* 覆盖 co-bar 的横向 flex：改为「说明行 + 按钮行」两段，避免浮层压住页面内容 */
  display: block;
}
.actionbar__btns {
  display: flex;
  align-items: center;
}
.actionbar__ghost {
  flex: 1;
  margin-right: 20rpx;
  padding: 0;
}
.actionbar__main {
  flex: 1.4;
  padding: 0;
}

/* 模拟支付说明：作为底栏内的第一行，不占用也不遮挡页面内容 */
.paynote {
  padding: 0 16rpx 14rpx;
}
.paynote text {
  display: block;
  font-size: 20rpx;
  color: var(--co-text-4);
  text-align: center;
  line-height: 1.5;
}
</style>
