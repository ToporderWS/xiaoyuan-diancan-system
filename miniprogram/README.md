# 校园点餐 · 学生微信小程序（UniApp + Vue3）

## 一、运行前置

1. 后端已启动：`http://192.168.0.103:5000/api/health` 返回 `status: UP`
2. 修改接口地址：`utils/config.js`

```js
export const BASE_URL = 'http://192.168.0.103:5000/api'
export const STATIC_BASE = 'http://192.168.0.103:5000/static/upload/'
```

> 该 IP 必须是电脑当前局域网 IP，手机 / 模拟器需与电脑处于同一局域网。

## 二、运行方式

### 方式 A：HBuilderX（推荐）

1. HBuilderX → 文件 → 打开目录 → 选择本目录
2. `manifest.json` → 微信小程序配置 → 填写 AppID
3. 运行 → 运行到小程序模拟器 → 微信开发者工具

### 方式 B：微信开发者工具导入编译产物

1. HBuilderX 或 uni-app CLI 编译到 `unpackage/dist/dev/mp-weixin`
2. 微信开发者工具 → 导入项目 → 选择该产物目录 → 填写 AppID
3. 详情 → 本地设置 → 勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」

## 三、静态自检

```bash
node scripts/check-project.js
# 或
npm run check
```

校验：JSON 合法性、页面注册一致性、TabBar 4 项与图标、地址集中配置、统一请求层、Token Key 隔离、接口路径白名单、无 TODO 占位。

## 四、目录说明

```
miniprogram/
├── App.vue / main.js / uni.scss     应用根组件、入口、设计令牌
├── pages.json                       页面与 TabBar 配置
├── manifest.json                    应用配置（vueVersion: 3）
├── package.json                     工程元信息 + npm run check
├── scripts/check-project.js         工程静态自检
├── utils/
│   ├── config.js                    ★ 唯一地址配置点 + 常量
│   └── request.js                   统一请求层（Authorization / student_token / 401 / loading）
├── api/index.js                     接口定义（与后端路由一一对应）
├── static/                          图标与占位图
│   ├── tabbar/                      TabBar 图标（普通 + 选中）
│   ├── logo.png                     品牌 Logo
│   └── food-default.png             菜品占位图
└── pages/                           8 个页面
    ├── index/index.vue              首页
    ├── login/login.vue              登录
    ├── login/register.vue           注册
    ├── cart/cart.vue                购物车
    ├── order/confirm.vue            确认订单
    ├── order/detail.vue             订单详情
    ├── order/list.vue               我的订单
    └── my/my.vue                    我的
```

## 五、约定

- 请求一律走 `utils/request.js`，页面中不出现 `uni.request` / `uni.uploadFile`
- 地址一律取自 `utils/config.js`，页面中不出现硬编码 IP
- 本地存储只使用 `student_token`，与 PC 后台的 Token Key 隔离
- 购物车「数量减少」在既有契约（`/cart/save`、`/cart/del`）内实现：先删除条目再按目标数量保存，未新增接口
- 支付为**模拟支付**，UI 明确标注，不接入真实微信支付

## 六、已知限制

- 购物车按整单结算，不做部分勾选（后端契约冻结为「当前购物车全部有效商品结算」）
- 未提供「忘记密码」自助找回，需管理员协助
- V1.0 退出登录为客户端清除 Token，服务端不做 JWT 吊销
