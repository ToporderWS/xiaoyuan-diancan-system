<template>
  <view class="co-page cart">
    <!-- ==================== 未登录 ==================== -->
    <view class="co-empty-wrap" v-if="!logged">
      <view class="co-empty">
        <image class="co-empty__art" src="/static/empty/empty-cart.png" mode="aspectFit" />
        <text class="co-empty__title">登录后查看购物车</text>
        <text class="co-empty__desc">购物车数据实时保存在服务器，换设备也能同步</text>
        <view class="co-empty__btn co-tap" @tap="goLogin">去登录</view>
      </view>
    </view>

    <template v-else>
      <!-- ==================== 列表 ==================== -->
      <view class="cart__head" v-if="items.length">
        <text class="cart__head-title">已在购物车</text>
        <text class="cart__head-count">共 {{ totalCount }} 件</text>
      </view>

      <view class="list" v-if="items.length">
        <view class="co-card item" v-for="it in items" :key="it.id">
          <image
            class="item__img co-tap"
            :src="imgUrl(it.food_img, it.food_img_failed)"
            mode="aspectFill"
            @tap="preview(it)"
            @error="onImgError(it)"
          />
          <view class="item__body">
            <text class="item__name">{{ it.food_name }}</text>
            <view class="item__tags" v-if="!it.valid">
              <text class="co-tag co-tag--gray">{{ it.invalid_reason }}</text>
            </view>
            <view class="item__bottom">
              <text class="co-price item__price">
                <text class="co-price__symbol">¥</text>{{ formatPrice(it.price) }}
              </text>
              <view class="co-stepper">
                <view
                  class="co-stepper__btn co-tap"
                  :class="{ 'co-stepper__btn--disabled': busy }"
                  @tap="decrease(it)"
                >
                  <image class="co-ico" src="/static/icons/minus.png" mode="aspectFit" />
                </view>
                <text class="co-stepper__num">{{ it.count }}</text>
                <view
                  class="co-stepper__btn co-stepper__btn--plus co-tap"
                  :class="{ 'co-stepper__btn--disabled': busy || it.count >= it.stock }"
                  @tap="increase(it)"
                >
                  <image class="co-ico" src="/static/icons/plus-white.png" mode="aspectFit" />
                </view>
              </view>
            </view>
          </view>
          <view class="item__del co-tap" @tap="removeItem(it)">
            <image class="item__del-ico" src="/static/icons/close.png" mode="aspectFit" />
          </view>
        </view>
      </view>

      <!-- ==================== 空购物车（居中重做） ==================== -->
      <view class="co-empty-wrap" v-else>
        <view class="co-empty">
          <image class="co-empty__art" src="/static/empty/empty-cart.png" mode="aspectFit" />
          <text class="co-empty__title">{{ loading ? '正在同步购物车' : '购物车还是空的' }}</text>
          <text class="co-empty__desc">去挑几道喜欢的菜，下单后送到宿舍楼下</text>
          <view class="co-empty__btn co-tap" v-if="!loading" @tap="goHome">去点餐</view>
        </view>
      </view>

      <!-- ==================== 结算栏（含 Home Indicator 安全区） ==================== -->
      <view class="co-bar co-bar--tabbar checkout" v-if="items.length">
        <view class="checkout__select">
          <view class="co-check co-check--on">
            <image class="co-ico" src="/static/icons/check-white.png" mode="aspectFit" />
          </view>
          <text class="checkout__select-text">全选</text>
        </view>
        <view class="checkout__amount">
          <text class="checkout__label">合计</text>
          <text class="co-price checkout__price">
            <text class="co-price__symbol">¥</text>{{ formatPrice(totalAmount) }}
          </text>
        </view>
        <view
          class="co-btn co-btn--sm checkout__btn"
          :class="{ 'co-btn--disabled': !canCheckout }"
          @tap="goCheckout"
        >
          去结算({{ validCount }})
        </view>
      </view>
      <view class="checkout-note" v-if="items.length">
        <text>本版本按购物车整单结算，不支持部分勾选</text>
      </view>
    </template>
  </view>
</template>

<script>
import { cartApi } from '../../api/index.js'
import { imageUrl, markImgFailed } from '../../utils/config.js'
import { isLogin } from '../../utils/request.js'

export default {
  data() {
    return {
      logged: false,
      items: [],
      loading: false,
      busy: false
    }
  },
  computed: {
    totalCount() {
      return this.items.reduce((s, i) => s + Number(i.count || 0), 0)
    },
    validCount() {
      return this.items.filter((i) => i.valid).reduce((s, i) => s + Number(i.count || 0), 0)
    },
    totalAmount() {
      return this.items.filter((i) => i.valid).reduce((s, i) => s + Number(i.subtotal || 0), 0)
    },
    hasInvalid() {
      return this.items.some((i) => !i.valid)
    },
    canCheckout() {
      return this.items.length > 0 && !this.hasInvalid && this.validCount > 0 && !this.busy
    }
  },
  onShow() {
    this.logged = isLogin()
    this.load()
  },
  onPullDownRefresh() {
    this.load().then(() => uni.stopPullDownRefresh())
  },
  methods: {
    imgUrl: imageUrl,
    onImgError: markImgFailed,
    formatPrice(v) {
      return Number(v || 0).toFixed(2)
    },
    load() {
      if (!isLogin()) {
        this.items = []
        return Promise.resolve()
      }
      this.loading = true
      return cartApi
        .list({ silent: true })
        .then((d) => {
          this.items = d.list || []
        })
        .catch(() => {})
        .then(() => {
          this.loading = false
        })
    },
    preview(it) {
      uni.showToast({ title: it.food_name + '　¥' + this.formatPrice(it.price), icon: 'none' })
    },
    goLogin() {
      uni.navigateTo({ url: '/pages/login/login' })
    },
    goHome() {
      uni.switchTab({ url: '/pages/index/index' })
    },
    increase(it) {
      if (this.busy) return
      if (it.count >= it.stock) {
        uni.showToast({ title: '不能超过当前库存 ' + it.stock, icon: 'none' })
        return
      }
      this.busy = true
      cartApi
        .save(it.food_id, 1)
        .then(() => this.load())
        .catch((e) => {
          if (e && e.code === 400) this.load()
        })
        .then(() => {
          this.busy = false
        })
    },
    /**
     * 契约内实现「数量减少」：购物车接口只提供 save / del。
     * count > 1 时先删除该条目，再按新的目标数量保存；
     * count === 1 时直接删除条目。
     */
    decrease(it) {
      if (this.busy) return
      this.busy = true
      const finish = () => {
        this.busy = false
      }
      if (it.count <= 1) {
        cartApi
          .del(it.id)
          .then(() => this.load())
          .catch(() => {})
          .then(finish)
        return
      }
      cartApi
        .del(it.id)
        .then(() => cartApi.save(it.food_id, it.count - 1))
        .then(() => this.load())
        .catch((e) => {
          uni.showToast({ title: (e && e.msg) || '操作失败，请刷新后重试', icon: 'none' })
          return this.load()
        })
        .then(finish)
    },
    removeItem(it) {
      uni.showModal({
        title: '移出购物车',
        content: '确定将「' + it.food_name + '」移出购物车吗？',
        success: (res) => {
          if (!res.confirm) return
          cartApi
            .del(it.id)
            .then(() => {
              uni.showToast({ title: '已移除', icon: 'success' })
              this.load()
            })
            .catch(() => {})
        }
      })
    },
    goCheckout() {
      if (this.items.length === 0) return
      if (this.hasInvalid) {
        uni.showToast({ title: '存在已下架或库存不足的菜品，请先移除', icon: 'none' })
        return
      }
      uni.navigateTo({ url: '/pages/order/confirm' })
    }
  }
}
</script>

<style>
.cart {
  padding-bottom: 200rpx;
}

/* 列表标题 */
.cart__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 26rpx 32rpx 14rpx;
}
.cart__head-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--co-text);
}
.cart__head-count {
  font-size: 24rpx;
  color: var(--co-text-3);
}

/* 列表条目 */
.list {
  padding-top: 4rpx;
}
.item {
  position: relative;
  display: flex;
  align-items: flex-start;
}
.item__img {
  width: 168rpx;
  height: 168rpx;
  border-radius: 18rpx;
  background-color: var(--co-line-soft);
  flex-shrink: 0;
}
.item__body {
  flex: 1;
  margin-left: 22rpx;
  min-width: 0;
  /* 为右上角删除按钮（含热区）留出安全距离，长菜名不会压到按钮 */
  padding-right: 68rpx;
}
.item__name {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  color: var(--co-text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.item__tags {
  margin-top: 12rpx;
  display: flex;
  flex-wrap: wrap;
}
.item__tags .co-tag {
  margin-right: 12rpx;
  margin-bottom: 6rpx;
}
.item__bottom {
  margin-top: 18rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.item__price {
  font-size: 34rpx;
}
.item__del {
  position: absolute;
  top: 10rpx;
  right: 14rpx;
  /* 视觉尺寸不变，热区由 23px 放大到 31px */
  padding: 18rpx;
}
.item__del-ico {
  width: 26rpx;
  height: 26rpx;
  opacity: 0.55;
}

/* 结算栏 */
.checkout {
  align-items: center;
}
.checkout__select {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.checkout__select-text {
  margin-left: 12rpx;
  font-size: 26rpx;
  color: var(--co-text-2);
}
.checkout__amount {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  padding-right: 20rpx;
}
.checkout__label {
  font-size: 26rpx;
  color: var(--co-text-2);
  margin-right: 8rpx;
}
.checkout__price {
  font-size: 38rpx;
}
.checkout__btn {
  flex-shrink: 0;
  width: 236rpx;
  padding: 0;
  border-radius: 34rpx;
}
.checkout-note {
  position: fixed;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 20rpx;
  color: var(--co-text-4);
  padding: 6rpx 0;
  z-index: 29;
  /* 贴在结算栏之上（结算栏已走 tabBar 变体，底部不再叠安全区） */
  bottom: 100rpx;
}
</style>
