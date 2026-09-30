<template>
  <view class="co-page confirm">
    <!-- ==================== 收货地址 ==================== -->
    <view class="co-card addr">
      <view class="addr__head">
        <image class="addr__ico" src="/static/icons/location-red.png" mode="aspectFit" />
        <text class="addr__label">收货地址</text>
        <text class="addr__tip">默认取用宿舍，本次可修改</text>
      </view>
      <input
        class="addr__input"
        v-model="form.receive_address"
        maxlength="120"
        placeholder="请输入收货地址（宿舍楼栋 + 房间号）"
        placeholder-class="co-ph"
      />
      <view class="addr__quick" v-if="defaultDormitory">
        <text class="addr__quick-text">宿舍：{{ defaultDormitory }}</text>
        <text class="addr__quick-btn co-tap" @tap="useDormitory">使用默认宿舍</text>
      </view>
    </view>

    <!-- ==================== 商品清单 ==================== -->
    <view class="co-card">
      <view class="co-card__title">
        <text>商品清单</text>
        <text class="co-card__sub">共 {{ totalCount }} 件</text>
      </view>
      <view class="goods" v-if="items.length">
        <view class="goods__item" v-for="it in items" :key="it.id">
          <image
            class="goods__img"
            :src="imgUrl(it.food_img, it.food_img_failed)"
            mode="aspectFill"
            @error="onImgError(it)"
          />
          <view class="goods__body">
            <text class="goods__name">{{ it.food_name }}</text>
            <text class="goods__unit">单价 ¥{{ formatPrice(it.price) }} × {{ it.count }}</text>
          </view>
          <text class="co-price goods__sub">
            <text class="co-price__symbol">¥</text>{{ formatPrice(it.subtotal) }}
          </text>
        </view>
      </view>
      <view class="goods__empty" v-else>
        <image class="goods__empty-art" src="/static/empty/empty-cart.png" mode="aspectFit" />
        <text class="goods__empty-text">购物车为空，无法结算</text>
      </view>
    </view>

    <!-- ==================== 备注 ==================== -->
    <view class="co-card">
      <view class="co-card__title">
        <text>备注</text>
        <text class="co-card__sub">选填</text>
      </view>
      <textarea
        class="remark"
        v-model="form.remark"
        maxlength="200"
        placeholder="请输入备注信息（如：不要香菜、少放辣）"
        placeholder-class="co-ph"
      />
      <view class="remark__count">{{ (form.remark || '').length }}/200</view>
    </view>

    <!-- ==================== 金额汇总 ==================== -->
    <view class="co-card">
      <view class="summary__row">
        <text class="summary__label">商品金额</text>
        <text class="summary__value">¥{{ formatPrice(totalAmount) }}</text>
      </view>
      <view class="summary__row">
        <text class="summary__label">配送费</text>
        <text class="summary__value">¥0.00</text>
      </view>
      <view class="summary__row summary__row--total">
        <text class="summary__label summary__label--total">合计</text>
        <text class="co-price summary__total">
          <text class="co-price__symbol">¥</text>{{ formatPrice(totalAmount) }}
        </text>
      </view>
      <view class="summary__note">
        <text>最终金额以后端数据库计算为准，前端仅用于展示</text>
      </view>
    </view>

    <!-- ==================== 底部提交（含安全区） ==================== -->
    <view class="co-bar bar">
      <view class="bar__amount">
        <text class="bar__label">合计</text>
        <text class="co-price bar__price">
          <text class="co-price__symbol">¥</text>{{ formatPrice(totalAmount) }}
        </text>
      </view>
      <view
        class="co-btn bar__btn co-tap"
        :class="{ 'co-btn--disabled': !canSubmit }"
        @tap="submit"
      >
        {{ submitting ? '提交中...' : '提交订单' }}
      </view>
    </view>
  </view>
</template>

<script>
import { cartApi, orderApi, userApi } from '../../api/index.js'
import { imageUrl, markImgFailed } from '../../utils/config.js'
import { isLogin, setUser, getUser } from '../../utils/request.js'

export default {
  data() {
    return {
      form: { receive_address: '', remark: '' },
      items: [],
      defaultDormitory: '',
      submitting: false
    }
  },
  computed: {
    totalCount() {
      return this.items.reduce((s, i) => s + Number(i.count || 0), 0)
    },
    totalAmount() {
      return this.items.reduce((s, i) => s + Number(i.subtotal || 0), 0)
    },
    canSubmit() {
      return (
        !this.submitting &&
        this.items.length > 0 &&
        !!(this.form.receive_address || '').trim() &&
        (this.form.remark || '').length <= 200
      )
    }
  },
  onLoad() {
    if (!isLogin()) {
      uni.showToast({ title: '请先登录', icon: 'none' })
      setTimeout(() => uni.navigateTo({ url: '/pages/login/login' }), 600)
      return
    }
    const cached = getUser()
    if (cached && cached.dormitory) {
      this.defaultDormitory = cached.dormitory
      this.form.receive_address = cached.dormitory
    }
    this.loadUser()
    this.loadCart()
  },
  methods: {
    imgUrl: imageUrl,
    onImgError: markImgFailed,
    formatPrice(v) {
      return Number(v || 0).toFixed(2)
    },
    loadUser() {
      userApi
        .info()
        .then((u) => {
          // 仅用于本次下单的默认地址，不回写用户默认宿舍
          this.defaultDormitory = u.dormitory || ''
          if (!this.form.receive_address && u.dormitory) {
            this.form.receive_address = u.dormitory
          }
          setUser({
            user_id: u.id,
            nickname: u.nickname,
            phone: u.phone,
            avatar: u.avatar,
            student_no: u.student_no,
            dormitory: u.dormitory
          })
        })
        .catch(() => {})
    },
    loadCart() {
      return cartApi
        .list({ silent: true })
        .then((d) => {
          this.items = d.list || []
          if (this.items.length === 0) {
            uni.showToast({ title: '购物车为空', icon: 'none' })
          }
        })
        .catch(() => {})
    },
    useDormitory() {
      this.form.receive_address = this.defaultDormitory
    },
    submit() {
      if (this.submitting) return
      const address = (this.form.receive_address || '').trim()
      if (!address) {
        uni.showToast({ title: '请填写收货地址', icon: 'none' })
        return
      }
      if (address.length > 120) {
        uni.showToast({ title: '收货地址不能超过 120 个字符', icon: 'none' })
        return
      }
      if ((this.form.remark || '').length > 200) {
        uni.showToast({ title: '备注不能超过 200 个字符', icon: 'none' })
        return
      }
      if (this.items.length === 0) {
        uni.showToast({ title: '购物车为空，无法下单', icon: 'none' })
        return
      }

      this.submitting = true
      // 只提交地址与备注：金额、用户、订单状态全部由后端决定
      orderApi
        .create({ receive_address: address, remark: (this.form.remark || '').trim() })
        .then((order) => {
          uni.showToast({ title: '下单成功', icon: 'success' })
          setTimeout(() => {
            uni.redirectTo({ url: '/pages/order/detail?order_id=' + order.id })
          }, 700)
        })
        .catch((e) => {
          // 库存/上架状态可能已变化，刷新购物车
          if (e && e.code === 400) this.loadCart()
        })
        .then(() => {
          this.submitting = false
        })
    }
  }
}
</script>

<style>
.confirm {
  padding: 24rpx 0 240rpx;
}

/* ==================== 收货地址 ==================== */
.addr__head {
  display: flex;
  align-items: center;
  margin-bottom: 18rpx;
}
.addr__ico {
  width: 34rpx;
  height: 34rpx;
  flex-shrink: 0;
  margin-right: 12rpx;
}
.addr__label {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--co-text);
}
.addr__tip {
  margin-left: auto;
  font-size: 22rpx;
  color: var(--co-text-3);
}
.addr__input {
  height: 88rpx;
  background-color: var(--co-bg);
  border-radius: 16rpx;
  padding: 0 22rpx;
  font-size: 28rpx;
  color: var(--co-text);
}
.addr__quick {
  margin-top: 18rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.addr__quick-text {
  flex: 1;
  min-width: 0;
  font-size: 24rpx;
  color: var(--co-text-3);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  margin-right: 16rpx;
}
.addr__quick-btn {
  flex-shrink: 0;
  font-size: 24rpx;
  color: var(--co-primary);
  padding: 8rpx 22rpx;
  border: 2rpx solid var(--co-primary-line);
  border-radius: 999rpx;
}

/* ==================== 商品清单 ==================== */
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
.goods__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20rpx 0 8rpx;
}
.goods__empty-art {
  width: 160rpx;
  height: 160rpx;
}
.goods__empty-text {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: var(--co-text-3);
}

/* ==================== 备注 ==================== */
.remark {
  width: 100%;
  height: 150rpx;
  background-color: var(--co-bg);
  border-radius: 16rpx;
  padding: 20rpx 22rpx;
  font-size: 28rpx;
  color: var(--co-text);
}
.remark__count {
  text-align: right;
  font-size: 22rpx;
  color: var(--co-text-4);
  margin-top: 8rpx;
}

/* ==================== 金额汇总 ==================== */
.summary__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10rpx 0;
}
.summary__label {
  font-size: 26rpx;
  color: var(--co-text-2);
}
.summary__value {
  font-size: 26rpx;
  color: var(--co-text);
}
.summary__row--total {
  border-top: 2rpx solid var(--co-line-soft);
  margin-top: 8rpx;
  padding-top: 18rpx;
}
.summary__label--total {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--co-text);
}
.summary__total {
  font-size: 40rpx;
}
.summary__note {
  margin-top: 12rpx;
  font-size: 20rpx;
  color: var(--co-text-4);
}

/* ==================== 底部提交栏 ==================== */
.bar__amount {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
}
.bar__label {
  font-size: 26rpx;
  color: var(--co-text-2);
  margin-right: 8rpx;
}
.bar__price {
  font-size: 42rpx;
}
.bar__btn {
  flex-shrink: 0;
  width: 268rpx;
}
</style>
