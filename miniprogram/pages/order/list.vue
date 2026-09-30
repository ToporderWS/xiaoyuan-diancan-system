<template>
  <view class="co-page orders">
    <!-- ==================== 未登录 ==================== -->
    <view class="co-empty-wrap" v-if="!logged">
      <view class="co-empty">
        <image class="co-empty__art" src="/static/empty/empty-order.png" mode="aspectFit" />
        <text class="co-empty__title">登录后查看订单</text>
        <text class="co-empty__desc">下单记录、配送进度都会同步到你的账号</text>
        <view class="co-empty__btn co-tap" @tap="goLogin">去登录</view>
      </view>
    </view>

    <template v-else>
      <!-- ==================== 状态筛选 ==================== -->
      <view class="tabs">
        <view class="tabs__inner">
          <view
            class="tabs__item co-tap"
            v-for="t in tabs"
            :key="t.label"
            :class="{ 'tabs__item--active': activeStatus === t.value }"
            @tap="switchTab(t.value)"
          >
            <text class="tabs__text">{{ t.label }}</text>
            <view class="tabs__line" v-if="activeStatus === t.value"></view>
          </view>
        </view>
      </view>

      <!-- ==================== 订单列表 ==================== -->
      <view class="list" v-if="orders.length">
        <view class="co-card order co-tap" v-for="o in orders" :key="o.id" @tap="goDetail(o)">
          <view class="order__head">
            <text class="order__no">{{ o.order_no }}</text>
            <text class="order__status" :class="'order__status--' + o.order_status">
              {{ o.status_text }}
            </text>
          </view>

          <view class="order__goods">
            <view class="order__good" v-for="it in o.items" :key="it.id">
              <image
                class="order__img"
                :src="imgUrl(it.food_img, it.food_img_failed)"
                mode="aspectFill"
                @error="onImgError(it)"
              />
              <view class="order__info">
                <text class="order__name">{{ it.food_name }}</text>
                <text class="order__meta">¥{{ formatPrice(it.food_price) }} × {{ it.count }}</text>
              </view>
              <text class="order__sub">¥{{ formatPrice(it.subtotal) }}</text>
            </view>
          </view>

          <view class="order__foot">
            <text class="order__count">共 {{ itemCount(o) }} 件</text>
            <text class="order__total">
              合计
              <text class="co-price order__price">
                <text class="co-price__symbol">¥</text>{{ formatPrice(o.total_price) }}
              </text>
            </text>
          </view>

          <view class="order__actions" @tap.stop>
            <text class="order__time">{{ o.created_at }}</text>
            <view class="co-btn co-btn--sm co-btn--plain" v-if="o.can_cancel" @tap="cancel(o)">
              取消订单
            </view>
            <view class="co-btn co-btn--sm" v-if="o.can_pay" @tap="pay(o)">模拟支付</view>
          </view>
        </view>
      </view>

      <!-- ==================== 空订单（居中重做） ==================== -->
      <view class="co-empty-wrap" v-else>
        <view class="co-empty">
          <image class="co-empty__art" src="/static/empty/empty-order.png" mode="aspectFit" />
          <text class="co-empty__title">{{ loading ? '正在加载订单' : '暂无相关订单' }}</text>
          <text class="co-empty__desc">当前筛选条件下还没有订单记录</text>
          <view class="co-empty__btn co-tap" v-if="!loading" @tap="goHome">去点餐</view>
        </view>
      </view>

      <view class="co-loadmore" v-if="orders.length">
        <text v-if="loading">加载中...</text>
        <text v-else-if="finished">没有更多了</text>
      </view>
    </template>
  </view>
</template>

<script>
import { orderApi } from '../../api/index.js'
import { imageUrl, markImgFailed, ORDER_TABS } from '../../utils/config.js'
import { isLogin } from '../../utils/request.js'

export default {
  data() {
    return {
      logged: false,
      tabs: ORDER_TABS,
      activeStatus: null,
      orders: [],
      page: 1,
      pageSize: 10,
      total: 0,
      loading: false,
      finished: false
    }
  },
  onShow() {
    this.logged = isLogin()
    if (this.logged) this.load(true)
    else this.orders = []
  },
  onPullDownRefresh() {
    this.load(true).then(() => uni.stopPullDownRefresh())
  },
  onReachBottom() {
    if (!this.loading && !this.finished) this.load(false)
  },
  methods: {
    imgUrl: imageUrl,
    onImgError: markImgFailed,
    formatPrice(v) {
      return Number(v || 0).toFixed(2)
    },
    itemCount(o) {
      return (o.items || []).reduce((s, i) => s + Number(i.count || 0), 0)
    },
    load(reset) {
      if (!isLogin()) {
        this.logged = false
        return Promise.resolve()
      }
      if (this.loading) return Promise.resolve()
      this.loading = true
      if (reset) {
        this.page = 1
        this.finished = false
      }
      const params = { page: this.page, page_size: this.pageSize }
      if (this.activeStatus !== null) params.order_status = this.activeStatus

      return orderApi
        .myList(params)
        .then((d) => {
          const list = d.list || []
          this.orders = reset ? list : this.orders.concat(list)
          this.total = d.total || 0
          this.finished = this.orders.length >= this.total || list.length === 0
          if (list.length) this.page += 1
        })
        .catch(() => {})
        .then(() => {
          this.loading = false
        })
    },
    switchTab(value) {
      if (this.activeStatus === value) return
      this.activeStatus = value
      this.load(true)
    },
    goDetail(o) {
      uni.navigateTo({ url: '/pages/order/detail?order_id=' + o.id })
    },
    goLogin() {
      uni.navigateTo({ url: '/pages/login/login' })
    },
    goHome() {
      uni.switchTab({ url: '/pages/index/index' })
    },
    pay(o) {
      uni.showModal({
        title: '模拟支付',
        content: '订单 ' + o.order_no + '\n确认执行「模拟支付」？不产生真实扣款。',
        confirmText: '确认支付',
        success: (res) => {
          if (!res.confirm) return
          orderApi
            .pay(o.id)
            .then(() => {
              uni.showToast({ title: '模拟支付成功', icon: 'success' })
              this.load(true)
            })
            .catch(() => this.load(true))
        }
      })
    },
    cancel(o) {
      uni.showModal({
        title: '取消订单',
        content: '取消后库存将恢复，确定要取消吗？',
        success: (res) => {
          if (!res.confirm) return
          orderApi
            .cancel(o.id)
            .then(() => {
              uni.showToast({ title: '订单已取消', icon: 'success' })
              this.load(true)
            })
            .catch(() => this.load(true))
        }
      })
    }
  }
}
</script>

<style>
.orders {
  padding-bottom: 60rpx;
}

/* ==================== 状态筛选 ====================
   用「文字 + 短下划线」表达选中，替代整块红底胶囊，
   降低页面红色面积，同时保留清晰的选中反馈。 */
.tabs {
  width: 100%;
  background-color: var(--co-card);
  padding: 8rpx 0 0;
}
.tabs__inner {
  display: flex;
  padding: 0 12rpx;
}
.tabs__item {
  /* 全部 + 5 个状态共 6 项，等分整行：小屏不换行、不出现半截 */
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20rpx 0 14rpx;
}
.tabs__text {
  font-size: 26rpx;
  color: var(--co-text-2);
  white-space: nowrap;
}
.tabs__item--active .tabs__text {
  font-size: 27rpx;
  font-weight: 700;
  color: var(--co-text);
}
.tabs__line {
  margin-top: 10rpx;
  width: 40rpx;
  height: 6rpx;
  border-radius: 3rpx;
  background-color: var(--co-primary);
}

/* ==================== 订单卡片 ==================== */
.list {
  padding-top: 12rpx;
}
.order__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 18rpx;
  border-bottom: 2rpx solid var(--co-line-soft);
}
.order__no {
  font-size: 24rpx;
  color: var(--co-text-3);
  letter-spacing: 1rpx;
}
.order__status {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--co-primary);
}
.order__status--0 {
  color: var(--co-warning);
}
.order__status--1 {
  color: var(--co-primary);
}
.order__status--2 {
  color: var(--co-info);
}
.order__status--3 {
  color: var(--co-success);
}
.order__status--4 {
  color: var(--co-text-3);
}

.order__goods {
  padding: 6rpx 0;
}
.order__good {
  display: flex;
  align-items: center;
  padding: 14rpx 0;
}
.order__img {
  width: 100rpx;
  height: 100rpx;
  border-radius: 16rpx;
  background-color: var(--co-line-soft);
  flex-shrink: 0;
}
.order__info {
  flex: 1;
  margin-left: 18rpx;
  min-width: 0;
}
.order__name {
  display: block;
  font-size: 27rpx;
  color: var(--co-text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.order__meta {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: var(--co-text-3);
}
.order__sub {
  flex-shrink: 0;
  font-size: 26rpx;
  color: var(--co-text-2);
  margin-left: 14rpx;
}

.order__foot {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 16rpx 0 18rpx;
  border-top: 2rpx solid var(--co-line-soft);
}
.order__count {
  font-size: 24rpx;
  color: var(--co-text-3);
}
.order__total {
  font-size: 26rpx;
  color: var(--co-text-2);
}
.order__price {
  font-size: 34rpx;
}

.order__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
.order__time {
  flex: 1;
  min-width: 0;
  font-size: 22rpx;
  color: var(--co-text-4);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  padding-right: 16rpx;
}
.order__actions .co-btn--sm {
  margin-left: 16rpx;
  flex-shrink: 0;
}
</style>
