<template>
  <view class="co-page my">
    <!-- ==================== 未登录 ==================== -->
    <view class="co-empty-wrap" v-if="!logged">
      <view class="co-empty">
        <image class="co-empty__art guest__art" src="/static/logo.png" mode="aspectFit" />
        <text class="co-empty__title">登录后享用完整功能</text>
        <text class="co-empty__desc">点餐、购物车、订单进度与个人资料一并同步</text>
        <view class="co-empty__btn co-tap" @tap="goLogin">立即登录</view>
        <text class="guest__link co-tap" @tap="goRegister">还没有账号？去注册</text>
      </view>
    </view>

    <template v-else>
      <!-- ==================== 个人资料（去大红块，改白底卡片） ==================== -->
      <view class="co-card profile">
        <image
          class="profile__avatar co-tap"
          :src="avatarImg(user.avatar, user.avatar_failed)"
          mode="aspectFill"
          @tap="changeAvatar"
          @error="onAvatarError"
        />
        <view class="profile__info">
          <text class="profile__nickname">{{ user.nickname || '未填写昵称' }}</text>
          <view class="profile__phone">
            <image class="co-ico co-ico--sm" src="/static/icons/mobile.png" mode="aspectFit" />
            <text class="profile__phone-text">{{ user.phone }}</text>
          </view>
        </view>
        <view class="profile__edit co-tap" @tap="changeAvatar">
          <image class="profile__edit-ico" src="/static/icons/image.png" mode="aspectFit" />
          <text class="profile__edit-text">换头像</text>
        </view>
      </view>

      <!-- ==================== 学籍信息 ==================== -->
      <view class="co-card">
        <view class="co-card__title">
          <text>学籍信息</text>
          <text class="co-card__sub">下单时用于默认收货地址</text>
        </view>
        <view class="co-row">
          <text class="co-row__label">学号</text>
          <text class="co-row__value">{{ user.student_no || '未填写' }}</text>
        </view>
        <view class="co-row">
          <text class="co-row__label">宿舍</text>
          <text class="co-row__value">{{ user.dormitory || '未填写' }}</text>
        </view>
      </view>

      <!-- ==================== 功能菜单 ==================== -->
      <view class="co-card menu">
        <view class="co-row co-tap" @tap="changeAvatar">
          <image class="menu__ico" src="/static/icons/image.png" mode="aspectFit" />
          <text class="menu__text">修改头像</text>
          <image class="menu__arrow" src="/static/icons/arrow.png" mode="aspectFit" />
        </view>
        <view class="co-row co-tap" @tap="openProfile">
          <image class="menu__ico" src="/static/icons/edit.png" mode="aspectFit" />
          <text class="menu__text">修改资料</text>
          <text class="menu__sub">昵称 / 学号 / 宿舍</text>
          <image class="menu__arrow" src="/static/icons/arrow.png" mode="aspectFit" />
        </view>
        <view class="co-row co-tap" @tap="openPwd">
          <image class="menu__ico" src="/static/icons/lock.png" mode="aspectFit" />
          <text class="menu__text">修改密码</text>
          <image class="menu__arrow" src="/static/icons/arrow.png" mode="aspectFit" />
        </view>
        <view class="co-row co-tap" @tap="contact">
          <image class="menu__ico" src="/static/icons/service.png" mode="aspectFit" />
          <text class="menu__text">联系客服</text>
          <text class="menu__sub">工作日 08:00 - 20:00</text>
          <image class="menu__arrow" src="/static/icons/arrow.png" mode="aspectFit" />
        </view>
        <view class="co-row co-tap" @tap="about">
          <image class="menu__ico" src="/static/icons/info.png" mode="aspectFit" />
          <text class="menu__text">关于我们</text>
          <image class="menu__arrow" src="/static/icons/arrow.png" mode="aspectFit" />
        </view>
      </view>

      <view class="logout co-tap" @tap="logout">退出登录</view>
      <view class="version">校园点餐 v1.0.0</view>
    </template>

    <!-- ==================== 修改资料弹层 ==================== -->
    <view class="co-mask" v-if="profileVisible" @tap="profileVisible = false">
      <view class="co-sheet" @tap.stop>
        <view class="co-sheet__head">
          <text class="co-sheet__title">修改资料</text>
          <image
            class="co-sheet__close co-tap"
            src="/static/icons/close.png"
            mode="aspectFit"
            @tap="profileVisible = false"
          />
        </view>
        <view class="co-field">
          <text class="co-field__label">昵称</text>
          <input class="co-field__input" v-model="profileForm.nickname" maxlength="50"
                 placeholder="请输入昵称" placeholder-class="co-ph" />
        </view>
        <view class="co-field">
          <text class="co-field__label">学号</text>
          <input class="co-field__input" v-model="profileForm.student_no" maxlength="30"
                 placeholder="请输入学号" placeholder-class="co-ph" />
        </view>
        <view class="co-field">
          <text class="co-field__label">宿舍</text>
          <input class="co-field__input" v-model="profileForm.dormitory" maxlength="100"
                 placeholder="如：宿舍楼3栋 502" placeholder-class="co-ph" />
        </view>
        <view class="co-btn sheet__btn co-tap" @tap="saveProfile">保存</view>
      </view>
    </view>

    <!-- ==================== 修改密码弹层 ==================== -->
    <view class="co-mask" v-if="pwdVisible" @tap="pwdVisible = false">
      <view class="co-sheet" @tap.stop>
        <view class="co-sheet__head">
          <text class="co-sheet__title">修改密码</text>
          <image
            class="co-sheet__close co-tap"
            src="/static/icons/close.png"
            mode="aspectFit"
            @tap="pwdVisible = false"
          />
        </view>
        <view class="co-field">
          <text class="co-field__label">原密码</text>
          <input class="co-field__input" v-model="pwdForm.old_password" password maxlength="64"
                 placeholder="请输入原密码" placeholder-class="co-ph" />
        </view>
        <view class="co-field">
          <text class="co-field__label">新密码</text>
          <input class="co-field__input" v-model="pwdForm.new_password" password maxlength="64"
                 placeholder="不少于6位" placeholder-class="co-ph" />
        </view>
        <view class="co-field">
          <text class="co-field__label">确认</text>
          <input class="co-field__input" v-model="pwdForm.confirm" password maxlength="64"
                 placeholder="请再次输入新密码" placeholder-class="co-ph" />
        </view>
        <view class="sheet__tip">
          <text>修改成功后需要重新登录</text>
        </view>
        <view class="co-btn sheet__btn co-tap" @tap="savePwd">确认修改</view>
      </view>
    </view>
  </view>
</template>

<script>
import { userApi } from '../../api/index.js'
import { avatarUrl, imageUrl, markImgFailed } from '../../utils/config.js'
import { isLogin, clearToken, getUser, setUser } from '../../utils/request.js'

export default {
  data() {
    return {
      logged: false,
      user: { nickname: '', phone: '', avatar: '', student_no: '', dormitory: '' },
      profileVisible: false,
      pwdVisible: false,
      profileForm: { nickname: '', student_no: '', dormitory: '' },
      pwdForm: { old_password: '', new_password: '', confirm: '' }
    }
  },
  onShow() {
    this.logged = isLogin()
    if (!this.logged) return
    const cached = getUser()
    if (cached) this.user = Object.assign({}, this.user, cached)
    this.loadInfo()
  },
  onPullDownRefresh() {
    this.loadInfo().then(() => uni.stopPullDownRefresh())
  },
  methods: {
    imgUrl: imageUrl,
    avatarImg: avatarUrl,
    onAvatarError() {
      markImgFailed(this.user, 'avatar')
    },
    loadInfo() {
      if (!isLogin()) return Promise.resolve()
      return userApi
        .info()
        .then((u) => {
          this.user = u
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
    goLogin() {
      uni.navigateTo({ url: '/pages/login/login' })
    },
    goRegister() {
      uni.navigateTo({ url: '/pages/login/register' })
    },
    changeAvatar() {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const path = res.tempFilePaths[0]
          userApi
            .uploadAvatar(path)
            .then((d) => {
              this.user.avatar = d.avatar
              const cached = getUser() || {}
              cached.avatar = d.avatar
              setUser(cached)
              uni.showToast({ title: '头像已更新', icon: 'success' })
            })
            .catch(() => {})
        }
      })
    },
    openProfile() {
      this.profileForm = {
        nickname: this.user.nickname || '',
        student_no: this.user.student_no || '',
        dormitory: this.user.dormitory || ''
      }
      this.profileVisible = true
    },
    saveProfile() {
      const nickname = (this.profileForm.nickname || '').trim()
      if (!nickname) {
        uni.showToast({ title: '昵称不能为空', icon: 'none' })
        return
      }
      if (nickname.length > 50) {
        uni.showToast({ title: '昵称不能超过 50 个字符', icon: 'none' })
        return
      }
      userApi
        .updateInfo({
          nickname,
          student_no: (this.profileForm.student_no || '').trim(),
          dormitory: (this.profileForm.dormitory || '').trim()
        })
        .then((u) => {
          this.user = u
          setUser({
            user_id: u.id,
            nickname: u.nickname,
            phone: u.phone,
            avatar: u.avatar,
            student_no: u.student_no,
            dormitory: u.dormitory
          })
          this.profileVisible = false
          uni.showToast({ title: '保存成功', icon: 'success' })
        })
        .catch(() => {})
    },
    openPwd() {
      this.pwdForm = { old_password: '', new_password: '', confirm: '' }
      this.pwdVisible = true
    },
    savePwd() {
      const f = this.pwdForm
      if (!f.old_password) {
        uni.showToast({ title: '请输入原密码', icon: 'none' })
        return
      }
      if (!f.new_password || f.new_password.length < 6) {
        uni.showToast({ title: '新密码不能少于 6 位', icon: 'none' })
        return
      }
      if (f.new_password !== f.confirm) {
        uni.showToast({ title: '两次输入的新密码不一致', icon: 'none' })
        return
      }
      userApi
        .updatePwd({ old_password: f.old_password, new_password: f.new_password })
        .then(() => {
          this.pwdVisible = false
          uni.showToast({ title: '密码已修改，请重新登录', icon: 'success' })
          setTimeout(() => {
            clearToken()
            this.logged = false
            uni.reLaunch({ url: '/pages/login/login' })
          }, 1000)
        })
        .catch(() => {})
    },
    contact() {
      uni.showModal({
        title: '联系客服',
        content: '校园食堂服务台：工作日 08:00 - 20:00\n可在食堂一层服务窗口现场咨询。',
        showCancel: false,
        confirmText: '知道了'
      })
    },
    about() {
      uni.showModal({
        title: '关于我们',
        content: '校园点餐 v1.0.0\n校园餐饮在线点餐与配送平台，支持在线点餐、购物车、订单跟踪与食堂后台管理。',
        showCancel: false,
        confirmText: '知道了'
      })
    },
    logout() {
      uni.showModal({
        title: '退出登录',
        content: '确定要退出当前账号吗？',
        success: (res) => {
          if (!res.confirm) return
          userApi
            .logout()
            .catch(() => {})
            .then(() => {
              clearToken()
              this.logged = false
              this.user = { nickname: '', phone: '', avatar: '', student_no: '', dormitory: '' }
              uni.showToast({ title: '已退出登录', icon: 'success' })
              setTimeout(() => uni.switchTab({ url: '/pages/index/index' }), 700)
            })
        }
      })
    }
  }
}
</script>

<style>
.my {
  padding-bottom: 60rpx;
}

/* 未登录 */
.guest__art {
  border-radius: 48rpx;
}
.guest__link {
  margin-top: 30rpx;
  font-size: 26rpx;
  color: var(--co-primary);
}

/* ==================== 个人资料卡 ====================
   由整块红色渐变改为白底卡片：头像 + 昵称/手机号 + 换头像入口，
   品牌红只体现在头像描边与图标细节上。 */
.profile {
  display: flex;
  align-items: center;
  margin-top: 24rpx;
  padding: 32rpx 28rpx;
}
.profile__avatar {
  width: 124rpx;
  height: 124rpx;
  border-radius: 62rpx;
  background-color: var(--co-line-soft);
  flex-shrink: 0;
  border: 4rpx solid var(--co-primary-soft);
}
.profile__info {
  flex: 1;
  min-width: 0;
  margin-left: 24rpx;
}
.profile__nickname {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: var(--co-text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.profile__phone {
  display: flex;
  align-items: center;
  margin-top: 10rpx;
}
.profile__phone-text {
  margin-left: 8rpx;
  font-size: 25rpx;
  color: var(--co-text-2);
}
.profile__edit {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8rpx 12rpx;
}
.profile__edit-ico {
  width: 34rpx;
  height: 34rpx;
}
.profile__edit-text {
  margin-top: 6rpx;
  font-size: 21rpx;
  color: var(--co-text-3);
}

/* ==================== 菜单 ==================== */
.menu {
  padding: 0 28rpx;
}
.menu__ico {
  width: 38rpx;
  height: 38rpx;
  flex-shrink: 0;
  margin-right: 22rpx;
}
.menu__text {
  font-size: 29rpx;
  color: var(--co-text);
}
.menu__sub {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 23rpx;
  color: var(--co-text-4);
  margin-right: 12rpx;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.menu__arrow {
  width: 26rpx;
  height: 26rpx;
  flex-shrink: 0;
  margin-left: auto;
  opacity: 0.5;
}
/* .menu__arrow 已自带 margin-left: auto，此处不再重复声明 */

/* ==================== 退出登录 ==================== */
.logout {
  margin: 34rpx 24rpx 0;
  height: 92rpx;
  line-height: 92rpx;
  text-align: center;
  border-radius: 46rpx;
  background-color: var(--co-card);
  color: var(--co-primary);
  font-size: 30rpx;
  font-weight: 500;
  box-shadow: 0 2rpx 12rpx rgba(31, 26, 22, 0.04);
}
.version {
  margin-top: 30rpx;
  text-align: center;
  font-size: 22rpx;
  color: var(--co-text-4);
}

/* ==================== 弹层细节 ==================== */
.co-sheet__close {
  width: 30rpx;
  height: 30rpx;
  padding: 10rpx;
  opacity: 0.6;
}
.sheet__tip {
  margin-top: 18rpx;
  font-size: 22rpx;
  color: var(--co-text-4);
}
.sheet__btn {
  margin-top: 40rpx;
}
</style>
