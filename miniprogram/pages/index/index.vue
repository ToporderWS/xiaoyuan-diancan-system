<template>
  <view class="co-page index">
    <!-- ==================== 顶部 ==================== -->
    <view class="hero">
      <view class="hero__top">
        <view class="hero__campus co-tap" @tap="onCampusTap">
          <image class="co-ico co-ico--sm" src="/static/icons/location.png" mode="aspectFit" />
          <text class="hero__campus-name">{{ campus }}</text>
          <image class="hero__campus-arrow" src="/static/icons/arrow.png" mode="aspectFit" />
        </view>
        <view class="hero__user co-tap" v-if="!logged" @tap="goLogin">登录</view>
        <view class="hero__user co-tap" v-else @tap="goMy">
          <image class="co-ico co-ico--sm" src="/static/icons/user-line.png" mode="aspectFit" />
          <text class="hero__user-name">{{ nickname || '我的' }}</text>
        </view>
      </view>

      <text class="hero__title">今天想吃点什么？</text>
      <text class="hero__sub">校园食堂现做 · 送到宿舍楼下</text>

      <view class="search">
        <image class="search__icon" src="/static/icons/search.png" mode="aspectFit" />
        <input
          class="search__input"
          v-model="keyword"
          type="text"
          placeholder="搜索菜品名称"
          placeholder-class="co-ph search__ph"
          confirm-type="search"
          @confirm="onSearch"
        />
        <view class="search__act co-tap" @tap="onSearch">搜索</view>
      </view>
    </view>

    <!-- ==================== 公告 ==================== -->
    <view class="notice" v-if="notices.length">
      <image class="notice__icon" src="/static/icons/bell-red.png" mode="aspectFit" />
      <swiper class="notice__swiper" vertical autoplay circular :interval="3500" :duration="400">
        <swiper-item v-for="n in notices" :key="n.id">
          <text class="notice__text">{{ n.title }}</text>
        </swiper-item>
      </swiper>
    </view>

    <!-- ==================== 分类 ==================== -->
    <scroll-view class="cats" scroll-x :show-scrollbar="false">
      <view class="cats__inner">
        <view
          class="cats__item co-tap"
          :class="{ 'cats__item--active': activeCatId === null }"
          @tap="switchCat(null)"
        >
          <view class="cats__ico">
            <image class="cats__icon" src="/static/icons/cat-all.png" mode="aspectFit" />
          </view>
          <text class="cats__name">全部</text>
        </view>
        <view
          class="cats__item co-tap"
          v-for="c in categories"
          :key="c.id"
          :class="{ 'cats__item--active': activeCatId === c.id }"
          @tap="switchCat(c.id)"
        >
          <view class="cats__ico">
            <image class="cats__icon" :src="catIcon(c.cat_name)" mode="aspectFit" />
          </view>
          <text class="cats__name">{{ c.cat_name }}</text>
        </view>
      </view>
    </scroll-view>

    <!-- ==================== 菜品 ==================== -->
    <view class="co-section">
      <text class="co-section__title">{{ activeCatName }}</text>
      <text class="co-section__extra" v-if="total">{{ total }} 道菜品</text>
    </view>

    <view class="foods" v-if="foods.length">
      <view class="food co-tap" v-for="f in foods" :key="f.id" @tap="goDetail(f)">
        <view class="food__media">
          <image
            class="food__img"
            :src="imgUrl(f.food_img, f.food_img_failed)"
            mode="aspectFill"
            @error="onImgError(f)"
          />
          <view class="food__sold" v-if="f.stock <= 0">已售罄</view>
        </view>
        <view class="food__body">
          <text class="food__name">{{ f.food_name }}</text>
          <view class="food__meta">
            <text class="food__sales">月售 {{ f.sales }}</text>
            <text class="food__sep">·</text>
            <text class="food__stock" v-if="f.stock > 3">库存充足</text>
            <text class="food__stock food__stock--low" v-else-if="f.stock > 0">仅剩 {{ f.stock }}</text>
            <text class="food__stock" v-else>暂无供应</text>
          </view>
          <view class="food__bottom">
            <text class="co-price food__price">
              <text class="co-price__symbol">¥</text>{{ formatPrice(f.price) }}
            </text>
            <view
              class="food__add"
              :class="{ 'food__add--off': f.stock <= 0 }"
              @tap.stop="addCart(f)"
            >
              <image
                class="food__add-ico"
                :src="f.stock > 0 ? '/static/icons/plus-white.png' : '/static/icons/plus.png'"
                mode="aspectFit"
              />
            </view>
          </view>
        </view>
      </view>
    </view>

    <view class="co-empty-wrap" v-else>
      <view class="co-empty">
        <image
          class="co-empty__art"
          :src="keyword ? '/static/empty/empty-search.png' : '/static/empty/empty-data.png'"
          mode="aspectFit"
        />
        <text class="co-empty__title">{{ loading ? '正在加载菜品' : searchEmptyTitle }}</text>
        <text class="co-empty__desc">{{ searchEmptyDesc }}</text>
        <view class="co-empty__btn co-tap" v-if="keyword" @tap="clearSearch">查看全部菜品</view>
      </view>
    </view>

    <view class="co-loadmore" v-if="foods.length">
      <text v-if="loading">加载中...</text>
      <text v-else-if="finished">已到底部</text>
    </view>

    <!-- ==================== 悬浮购物车 ==================== -->
    <view class="fab co-tap" @tap="goCart">
      <image class="fab__icon" src="/static/icons/cart-white.png" mode="aspectFit" />
      <view class="fab__badge" v-if="cartCount > 0">{{ cartCount > 99 ? '99+' : cartCount }}</view>
    </view>

    <!-- ==================== 菜品简介弹层 ==================== -->
    <view class="co-mask" v-if="detailFood" @tap="detailFood = null">
      <view class="co-sheet sheet" @tap.stop>
        <view class="sheet__media">
          <image
            class="sheet__img"
            :src="imgUrl(detailFood.food_img, detailFood.food_img_failed)"
            mode="aspectFill"
            @error="onImgError(detailFood)"
          />
        </view>
        <view class="sheet__body">
          <text class="sheet__name">{{ detailFood.food_name }}</text>
          <view class="sheet__meta">
            <text class="co-tag">{{ detailFood.cat_name }}</text>
            <text class="sheet__sales">月售 {{ detailFood.sales }}</text>
            <text class="sheet__stock">
              {{ detailFood.stock > 0 ? '库存 ' + detailFood.stock : '已售罄' }}
            </text>
          </view>
          <text class="sheet__desc">{{ detailFood.description || '暂无菜品描述' }}</text>
          <view class="sheet__bottom">
            <text class="co-price sheet__price">
              <text class="co-price__symbol">¥</text>{{ formatPrice(detailFood.price) }}
            </text>
            <view
              class="sheet__btn"
              :class="{ 'sheet__btn--off': detailFood.stock <= 0 }"
              @tap="addCart(detailFood)"
            >
              {{ detailFood.stock > 0 ? '加入购物车' : '已售罄' }}
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { foodApi, cartApi, noticeApi } from '../../api/index.js'
import { imageUrl, markImgFailed, STORAGE_KEY } from '../../utils/config.js'
import { isLogin, getUser } from '../../utils/request.js'

export default {
  data() {
    return {
      campus: '校园食堂（东校区）',
      keyword: '',
      categories: [],
      activeCatId: null,
      foods: [],
      page: 1,
      pageSize: 10,
      total: 0,
      loading: false,
      finished: false,
      notices: [],
      cartCount: 0,
      logged: false,
      nickname: '',
      detailFood: null
    }
  },
  computed: {
    activeCatName() {
      if (this.keyword) return '搜索结果'
      if (this.activeCatId === null) return '推荐菜品'
      const hit = this.categories.filter((c) => c.id === this.activeCatId)[0]
      return hit ? hit.cat_name : '推荐菜品'
    },
    searchEmptyTitle() {
      if (this.keyword) return '没有找到相关菜品'
      if (this.activeCatId !== null) return '该分类暂无菜品'
      return '暂无菜品'
    },
    searchEmptyDesc() {
      if (this.keyword) return '换个关键词试试，或看看全部菜品'
      if (this.activeCatId !== null) return '切换其它分类，看看有没有喜欢的'
      return '稍后再来看看，食堂正在准备中'
    }
  },
  onLoad() {
    this.loadCategories()
    this.loadNotices()
    this.loadFoods(true)
  },
  onShow() {
    this.logged = isLogin()
    const u = getUser()
    this.nickname = u && u.nickname ? u.nickname : ''
    if (this.logged) this.loadCartCount()
    else this.cartCount = 0
    // 从其它页面返回时刷新库存
    if (this.foods.length) this.loadFoods(true, true)
  },
  onPullDownRefresh() {
    Promise.all([this.loadCategories(), this.loadNotices(), this.loadFoods(true)])
      .then(() => uni.stopPullDownRefresh())
      .catch(() => uni.stopPullDownRefresh())
  },
  onReachBottom() {
    if (!this.loading && !this.finished) this.loadFoods(false)
  },
  methods: {
    imgUrl: imageUrl,
    onImgError: markImgFailed,
    formatPrice(v) {
      return Number(v || 0).toFixed(2)
    },
    catIcon(name) {
      const map = {
        早餐: '/static/icons/cat-breakfast.png',
        快餐: '/static/icons/cat-fastfood.png',
        面食: '/static/icons/cat-noodles.png',
        饮品: '/static/icons/cat-drink.png',
        小吃: '/static/icons/cat-snack.png'
      }
      return map[name] || '/static/icons/cat-all.png'
    },
    loadCategories() {
      return foodApi
        .categories()
        .then((d) => {
          this.categories = d.list || []
        })
        .catch(() => {})
    },
    loadNotices() {
      return noticeApi
        .list()
        .then((d) => {
          this.notices = d.list || []
        })
        .catch(() => {})
    },
    loadFoods(reset, silent) {
      if (this.loading) return Promise.resolve()
      this.loading = true
      if (reset) {
        this.page = 1
        this.finished = false
      }
      const params = { page: this.page, page_size: this.pageSize }
      if (this.activeCatId) params.cat_id = this.activeCatId
      if (this.keyword) params.keyword = this.keyword

      return foodApi
        .list(params)
        .then((d) => {
          const list = d.list || []
          this.foods = reset ? list : this.foods.concat(list)
          this.total = d.total || 0
          this.finished = this.foods.length >= this.total || list.length === 0
          if (list.length) this.page += 1
        })
        .catch(() => {})
        .then(() => {
          this.loading = false
        })
    },
    loadCartCount() {
      return cartApi
        .list({ silent: true })
        .then((d) => {
          this.cartCount = d.total_count || 0
        })
        .catch(() => {})
    },
    onSearch() {
      this.loadFoods(true)
    },
    clearSearch() {
      this.keyword = ''
      this.activeCatId = null
      this.loadFoods(true)
    },
    switchCat(catId) {
      if (this.activeCatId === catId) return
      this.activeCatId = catId
      this.loadFoods(true)
    },
    onCampusTap() {
      uni.showToast({ title: '当前为单一校区配送', icon: 'none' })
    },
    goLogin() {
      uni.navigateTo({ url: '/pages/login/login' })
    },
    goMy() {
      uni.switchTab({ url: '/pages/my/my' })
    },
    goCart() {
      uni.switchTab({ url: '/pages/cart/cart' })
    },
    goDetail(f) {
      // 不新增菜品详情页路由（接口/页面清单已冻结），以弹层展示简介
      this.detailFood = f
    },
    addCart(f) {
      if (!f.stock || f.stock <= 0) {
        uni.showToast({ title: '该菜品已售罄', icon: 'none' })
        return
      }
      if (!isLogin()) {
        uni.showModal({
          title: '需要登录',
          content: '加入购物车前请先登录账号',
          confirmText: '去登录',
          success: (res) => {
            if (res.confirm) uni.navigateTo({ url: '/pages/login/login' })
          }
        })
        return
      }
      cartApi
        .save(f.id, 1)
        .then(() => {
          uni.showToast({ title: '已加入购物车', icon: 'success' })
          this.loadCartCount()
          // 库存本地预估减少，真实库存以下单时后端校验为准
          f.stock = Math.max(0, f.stock - 1)
        })
        .catch(() => {})
    }
  }
}
</script>

<style>
.index {
  padding-bottom: 180rpx;
}

/* ==================== 顶部 ==================== */
.hero {
  position: relative;
  background-color: var(--co-card);
  /* 首页减法：压缩顶部纵向占用，让首屏更快露出真实菜品 */
  padding: 14rpx 28rpx 20rpx;
  border-radius: 0 0 28rpx 28rpx;
}

.hero__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48rpx;
}

.hero__campus {
  display: flex;
  align-items: center;
  min-width: 0;
}

.hero__campus-name {
  margin-left: 6rpx;
  font-size: 25rpx;
  color: var(--co-text-2);
  max-width: 380rpx;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.hero__campus-arrow {
  width: 20rpx;
  height: 20rpx;
  margin-left: 4rpx;
  transform: rotate(-90deg);
  opacity: 0.6;
}

.hero__user {
  display: flex;
  align-items: center;
  height: 48rpx;
  padding: 0 18rpx;
  border-radius: 24rpx;
  background-color: var(--co-bg);
  font-size: 24rpx;
  color: var(--co-text-2);
  max-width: 240rpx;
}

.hero__user-name {
  margin-left: 6rpx;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.hero__title {
  display: block;
  margin-top: 14rpx;
  font-size: 40rpx;
  font-weight: 700;
  color: var(--co-text);
  letter-spacing: 1rpx;
}

.hero__sub {
  display: block;
  margin-top: 4rpx;
  font-size: 23rpx;
  color: var(--co-text-3);
}

/* 搜索 */
.search {
  margin-top: 16rpx;
  height: 70rpx;
  background-color: var(--co-bg);
  border-radius: 35rpx;
  display: flex;
  align-items: center;
  padding: 0 10rpx 0 22rpx;
}

.search__icon {
  width: 30rpx;
  height: 30rpx;
  flex-shrink: 0;
}

.search__input {
  flex: 1;
  min-width: 0;
  height: 70rpx;
  margin-left: 10rpx;
  font-size: 27rpx;
  color: var(--co-text);
}

.search__ph {
  font-size: 26rpx;
}

.search__act {
  flex-shrink: 0;
  padding: 0 20rpx;
  height: 52rpx;
  line-height: 52rpx;
  font-size: 26rpx;
  color: var(--co-primary);
  font-weight: 500;
}

/* ==================== 公告 ==================== */
.notice {
  margin: 12rpx 24rpx 0;
  height: 54rpx;
  background-color: var(--co-card);
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  padding: 0 20rpx;
}

.notice__icon {
  width: 24rpx;
  height: 24rpx;
  flex-shrink: 0;
}

.notice__swiper {
  flex: 1;
  min-width: 0;
  height: 54rpx;
  margin-left: 12rpx;
}

.notice__text {
  display: block;
  line-height: 54rpx;
  font-size: 24rpx;
  color: var(--co-text-2);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* ==================== 分类 ==================== */
.cats {
  margin-top: 14rpx;
  white-space: nowrap;
  width: 100%;
}

.cats__inner {
  display: flex;
  padding: 0 24rpx;
}

.cats__item {
  flex-shrink: 0;
  /* 6 个分类（全部 + 5 类）需在 375 宽下一屏排完，不留半截 */
  width: 106rpx;
  margin-right: 8rpx;
  padding: 6rpx 0 4rpx;
  text-align: center;
  border-radius: 16rpx;
}

/* 分类图标底：全部类别统一中性暖灰，选中项用品牌红浅底 —— 消除"6 个不同色圆底"的杂色感 */
.cats__ico {
  width: 74rpx;
  height: 74rpx;
  margin: 0 auto;
  border-radius: 50%;
  background-color: var(--co-media-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.cats__item--active .cats__ico {
  background-color: var(--co-primary-soft);
}

.cats__icon {
  width: 42rpx;
  height: 42rpx;
  display: block;
}

.cats__name {
  display: block;
  margin-top: 6rpx;
  font-size: 23rpx;
  color: var(--co-text-2);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.cats__item--active .cats__name {
  color: var(--co-primary);
  font-weight: 600;
}

/* ==================== 推荐菜品标题行 ====================
   仅本页覆盖 App.vue 的 .co-section（该公共类只有首页在用，不会外溢到其它页面），
   与上方区域一起压缩，使首屏更早露出第一排菜品。
   ==================================================== */
.index .co-section {
  padding: 18rpx 28rpx 12rpx;
}

.index .co-section__title {
  font-size: 30rpx;
}

/* ==================== 菜品卡片 ==================== */
.foods {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  padding: 0 24rpx;
}

.food {
  width: calc(50% - 10rpx);
  margin-bottom: 20rpx;
  background-color: var(--co-card);
  border-radius: 24rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 12rpx rgba(31, 26, 22, 0.04);
}

.food__media {
  position: relative;
  width: 100%;
  height: 340rpx;
  background-color: var(--co-media-bg);
}

.food__img {
  width: 100%;
  height: 100%;
  display: block;
}

.food__sold {
  position: absolute;
  left: 10rpx;
  top: 10rpx;
  padding: 2rpx 10rpx;
  border-radius: 999rpx;
  background-color: rgba(31, 29, 27, 0.5);
  color: #ffffff;
  font-size: 18rpx;
}

.food__body {
  padding: 14rpx 16rpx 16rpx;
}

.food__name {
  display: block;
  font-size: 29rpx;
  font-weight: 600;
  color: var(--co-text);
  line-height: 1.35;
  height: 40rpx;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.food__meta {
  display: flex;
  align-items: center;
  margin-top: 6rpx;
  height: 28rpx;
}

.food__sales,
.food__stock {
  font-size: 22rpx;
  color: var(--co-text-3);
}

.food__sep {
  margin: 0 8rpx;
  font-size: 22rpx;
  color: var(--co-line-strong);
}

.food__stock--low {
  color: var(--co-warning);
}

.food__bottom {
  margin-top: 12rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.food__price {
  font-size: 32rpx;
}

.food__add {
  width: 52rpx;
  height: 52rpx;
  border-radius: 50%;
  background-color: var(--co-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.food__add--off {
  background-color: var(--co-disable);
}

.food__add-ico {
  width: 26rpx;
  height: 26rpx;
}

/* ==================== 悬浮购物车 ==================== */
.fab {
  position: fixed;
  right: 28rpx;
  bottom: 56rpx;
  width: 84rpx;
  height: 84rpx;
  border-radius: 50%;
  background-color: var(--co-primary);
  box-shadow: 0 4rpx 12rpx rgba(31, 26, 22, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}

.fab__icon {
  width: 38rpx;
  height: 38rpx;
}

.fab__badge {
  position: absolute;
  top: -4rpx;
  right: -4rpx;
  min-width: 32rpx;
  height: 32rpx;
  line-height: 32rpx;
  padding: 0 7rpx;
  border-radius: 16rpx;
  background-color: var(--co-card);
  color: var(--co-primary);
  font-size: 19rpx;
  text-align: center;
  border: 2rpx solid var(--co-primary);
}

/* ==================== 菜品简介弹层 ==================== */
.sheet {
  padding: 0 0 40rpx;
  overflow: hidden;
}

.sheet__media {
  width: 100%;
  height: 420rpx;
  background-color: var(--co-media-bg);
}

.sheet__img {
  width: 100%;
  height: 100%;
  display: block;
}

.sheet__body {
  padding: 28rpx 32rpx 0;
}

.sheet__name {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: var(--co-text);
}

.sheet__meta {
  display: flex;
  align-items: center;
  margin-top: 14rpx;
}

.sheet__sales,
.sheet__stock {
  font-size: 24rpx;
  color: var(--co-text-3);
  margin-left: 16rpx;
}

.sheet__desc {
  display: block;
  margin-top: 18rpx;
  font-size: 26rpx;
  color: var(--co-text-2);
  line-height: 1.65;
}

.sheet__bottom {
  margin-top: 30rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sheet__price {
  font-size: 44rpx;
}

.sheet__btn {
  min-width: 260rpx;
  height: 84rpx;
  line-height: 84rpx;
  border-radius: 42rpx;
  background-color: var(--co-primary);
  color: #ffffff;
  font-size: 29rpx;
  font-weight: 500;
  text-align: center;
}

.sheet__btn--off {
  background-color: var(--co-disable);
  color: var(--co-text-3);
}
</style>
