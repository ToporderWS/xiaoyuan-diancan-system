# 校园点餐管理系统

一套面向校园食堂的完整点餐平台，包含 **学生微信小程序**、**PC 管理后台** 与 **Flask 后端服务** 三个独立工程，可独立部署、联调运行。

- 主题风格：校园餐饮风（暖红 `#E53935`），浅红渐变 + 白色卡片 + 圆角 + 适量阴影
- 数据一致性：全链路 Decimal 金额计算 + `SELECT ... FOR UPDATE` 行级锁库存扣减，**杜绝超卖**
- 权限隔离：JWT Payload 携带 `role`（0 学生 / 1 管理员），学生端与管理端 Token Key 完全隔离

---

## 一、技术栈

| 工程 | 技术栈 | 使用者 |
| --- | --- | --- |
| `miniprogram/` | UniApp + Vue3 + JavaScript + 微信小程序 | 学生 |
| `admin-pc/` | Vue3 + Vite + Vue Router + Pinia + Axios + Element Plus + ECharts | 管理员 |
| `backend/` | Python 3 + Flask + MySQL + PyMySQL + JWT + Werkzeug + APScheduler | 统一服务 |

数据库：MySQL 8.0（InnoDB / utf8mb4）。

---

## 二、项目目录

```
校园点餐系统小程序/
├── README.md                      本文件
├── docs/
│   ├── 接口补充说明.md              补充接口清单与实现说明
│   ├── 自动测试报告.md              pytest 全量测试结果
│   └── 最终开发报告.md              交付总报告
├── backend/                       Flask 后端
│   ├── app.py                     应用入口（工厂 + 统一异常 + 静态目录）
│   ├── config.py                  全部配置项（读取 .env）
│   ├── extensions.py              扩展对象出口
│   ├── requirements.txt           Python 依赖
│   ├── database.sql               建库建表脚本（8 张冻结表 + 5 个分类）
│   ├── .env.example               环境变量模板
│   ├── pytest.ini                 测试配置
│   ├── routes/                    路由层
│   │   ├── user_routes.py         学生账号 1~7
│   │   ├── food_routes.py         分类 / 菜品浏览 8~9
│   │   ├── cart_routes.py         购物车 10~12
│   │   ├── order_routes.py        订单 13~17 + 17A 模拟支付
│   │   ├── notice_routes.py       公告 17
│   │   └── admin_routes.py        管理员 18~28 + 补充接口
│   ├── services/                  业务服务层（事务在这一层）
│   │   ├── user_service.py
│   │   ├── food_service.py
│   │   ├── cart_service.py
│   │   ├── order_service.py       ★ 订单事务 / 状态机 / 库存 / 销量
│   │   ├── notice_service.py
│   │   └── admin_service.py
│   ├── utils/                     通用工具
│   │   ├── db.py                  连接池 + 请求级连接 + 事务上下文
│   │   ├── auth.py                JWT 签发/校验 + 密码哈希 + 角色装饰器
│   │   ├── response.py            统一返回 {code,msg,data}
│   │   ├── errors.py              业务异常 + 全局异常处理（永不返回 HTML 错误页）
│   │   ├── validators.py          参数校验
│   │   └── uploader.py            图片上传安全校验
│   ├── scheduler/order_scheduler.py  APScheduler 超时取消任务
│   ├── scripts/init_admin.py      管理员初始化脚本
│   ├── tests/                     pytest 测试（50 条用例）
│   └── static/upload/             图片上传目录
├── miniprogram/                   UniApp 学生小程序
│   ├── pages.json                 页面与 TabBar 配置（4 个 Tab）
│   ├── manifest.json              应用配置（vueVersion: 3）
│   ├── main.js / App.vue / uni.scss
│   ├── package.json               工程元信息 + 静态自检脚本
│   ├── scripts/check-project.js   工程静态自检（页面/TabBar/请求层/接口白名单）
│   ├── utils/config.js            全局地址与常量（集中配置）
│   ├── utils/request.js           统一请求层（Token/401/loading/解包）
│   ├── api/index.js               接口定义
│   ├── static/                    图标与占位图
│   └── pages/                     8 个页面
└── admin-pc/                      Vue3 PC 管理后台
    ├── package.json / vite.config.js / index.html
    └── src/
        ├── config.js              全局地址与常量（集中配置）
        ├── main.js / App.vue
        ├── api/request.js         统一 Axios（baseURL/admin_token/401）
        ├── api/index.js           接口定义
        ├── router/index.js        路由 + 登录守卫
        ├── stores/admin.js        Pinia 管理员状态
        ├── layout/index.vue       左侧菜单 + 顶部 Header
        ├── components/EChart.vue  ECharts 封装
        ├── styles/index.css       主题与全局样式
        └── views/                 9 个页面（登录/控制台/用户/分类/菜品/购物车/订单/公告/个人中心）
```

---

## 三、环境要求

| 组件 | 版本要求 | 说明 |
| --- | --- | --- |
| Python | 3.9+（实测 3.13.12） | 后端运行环境 |
| Node.js | 18+（实测 22.22.2） | PC 后台构建 |
| MySQL | 8.0+（实测 8.0.33） | InnoDB + utf8mb4 |
| HBuilderX | 最新正式版 | 编译 UniApp 小程序 |
| 微信开发者工具 | 最新稳定版 | 运行小程序 |

---

## 四、后端启动（backend）

### 4.1 安装 Python 依赖

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4.2 配置数据库连接

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

编辑 `backend/.env`，至少修改以下两项：

```ini
DB_USER=root
DB_PASSWORD=你的MySQL密码
```

其余关键配置：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | MySQL 地址 |
| `DB_NAME` | `campus_order` | 业务库名 |
| `TEST_DB_NAME` | `campus_order_test` | 测试库名（pytest 使用，**必须与业务库不同**） |
| `JWT_SECRET` | 占位值 | **生产环境必须改为足够随机的长字符串** |
| `JWT_STUDENT_EXPIRE_MINUTES` | `1440` | 学生 Token 有效期（分钟） |
| `JWT_ADMIN_EXPIRE_MINUTES` | `720` | 管理员 Token 有效期（分钟） |
| `ORDER_TIMEOUT_MINUTES` | `15` | 未支付订单自动取消阈值 |
| `SCHEDULER_SCAN_INTERVAL` | `60` | 定时任务扫描间隔（秒） |
| `ENABLE_SCHEDULER` | `1` | 是否开启定时任务（pytest 下自动关闭） |
| `MAX_UPLOAD_SIZE` | `2097152` | 单张图片上限（2MB） |
| `PUBLIC_API_BASE` | `http://192.168.0.103:5000/api` | 对外 API 地址 |
| `PUBLIC_STATIC_BASE` | `http://192.168.0.103:5000/static/upload/` | 图片静态地址 |

### 4.3 初始化 MySQL

```bash
mysql -u root -p < backend/database.sql
```

脚本会完成：创建 `campus_order` 库（utf8mb4）→ 建 8 张 InnoDB 表（主键 / 唯一索引 / 普通索引 / 外键 / 默认值 / CHECK 约束）→ 写入 5 个分类（早餐、快餐、面食、饮品、小吃）。

脚本中**不包含任何管理员明文密码**。

### 4.4 初始化管理员

```bash
cd backend
# 交互式（密码不回显）
python scripts/init_admin.py

# 非交互式
python scripts/init_admin.py --admin-name admin --password 你的密码 --real-name 系统管理员

# 已存在时重置密码
python scripts/init_admin.py --admin-name admin --password 新密码 --force
```

### 4.5 启动后端

```bash
cd backend
python app.py
```

启动后监听 `0.0.0.0:5000`：

| 地址 | 说明 |
| --- | --- |
| `http://192.168.0.103:5000/` | 服务信息（非业务接口） |
| `http://192.168.0.103:5000/api/health` | 健康检查（含数据库连通性，非业务接口） |
| `http://192.168.0.103:5000/api` | **API Base URL** |
| `http://192.168.0.103:5000/static/upload/` | **图片静态资源基础路径** |

> 定时任务随应用启动，每 60 秒扫描一次「创建超过 15 分钟且仍为待支付」的订单并自动取消 + 恢复库存。该判断完全基于数据库，**进程重启后依旧生效**，不使用纯内存 Timer。

---

## 五、学生小程序启动（miniprogram）

### 5.1 修改后端地址

编辑 `miniprogram/utils/config.js`（**全项目唯一的地址配置点**）：

```js
export const BASE_URL = 'http://192.168.0.103:5000/api'
export const STATIC_BASE = 'http://192.168.0.103:5000/static/upload/'
```

> 该地址为电脑局域网 IP。请确保手机 / 开发者工具与后端在同一局域网，且后端以 `0.0.0.0` 监听、防火墙放行 5000 端口。

### 5.2 方式 A：HBuilderX（推荐）

1. HBuilderX → 文件 → 打开目录 → 选择 `miniprogram` 目录
2. 打开 `manifest.json` → 微信小程序配置 → 填入自己的 `AppID`（或在微信开发者工具中使用测试号）
3. 运行 → 运行到小程序模拟器 → 微信开发者工具
4. HBuilderX 会自动编译并在微信开发者工具中打开

### 5.3 方式 B：微信开发者工具直接导入

1. 先用 HBuilderX 或 uni-app CLI 将工程编译到 `unpackage/dist/dev/mp-weixin`
2. 微信开发者工具 → 导入项目 → 选择编译产物目录 → 填入 AppID
3. 勾选「不校验合法域名」（开发环境，因为后端为 HTTP + IP 地址）

### 5.4 工程静态自检

```bash
cd miniprogram
node scripts/check-project.js     # 或 npm run check
```

检查内容：pages.json / manifest.json 合法性、页面注册与实际文件一致、TabBar 4 项与图标存在、地址未硬编码、未绕过统一请求层、Token Key 隔离、接口路径白名单、无 TODO 占位。

### 5.5 页面清单（8 页）

| 路径 | 页面 | 说明 |
| --- | --- | --- |
| `pages/index/index` | 首页 | Slogan、滚动公告、横向分类、菜品列表、加入购物车；库存 0 显示「售罄」；未登录可浏览，加购提示登录 |
| `pages/login/login` | 登录 | 手机号 + 密码、显示/隐藏密码、记住手机号、注册入口、返回首页 |
| `pages/login/register` | 注册 | 昵称 / 手机号 / 密码 / 确认密码 / 学号 / 宿舍 + 前端校验 |
| `pages/cart/cart` | 购物车 Tab | 实时读后端、数量 +/−、删除、合计、去结算（整单结算） |
| `pages/order/confirm` | 确认订单 | 默认地址取 `users.dormitory`（本次可改，不回写默认）、商品清单、备注、提交订单 |
| `pages/order/detail` | 订单详情 | 订单号 / 状态 / 地址 / 备注 / 三个时间点 / 明细 / 总价；待支付显示【确认支付（模拟）】 |
| `pages/order/list` | 我的订单 Tab | 全部 / 待支付 / 待接单 / 配送中 / 已完成 / 已取消；待支付可支付+取消，待接单可取消，配送中无取消 |
| `pages/my/my` | 我的 Tab | 头像 / 昵称 / 手机号 / 学号 / 宿舍；修改头像、资料、密码；退出登录 |

TabBar 4 项：首页 / 购物车 / 我的订单 / 我的。

---

## 六、PC 管理后台启动（admin-pc）

### 6.1 修改后端地址

编辑 `admin-pc/src/config.js`：

```js
export const BASE_URL = 'http://192.168.0.103:5000/api'
export const STATIC_BASE = 'http://192.168.0.103:5000/static/upload/'
```

### 6.2 安装依赖并运行

```bash
cd admin-pc
npm install
npm run dev          # 开发模式，默认 http://localhost:5173
```

### 6.3 生产构建

```bash
npm run build        # 产物输出到 admin-pc/dist
npm run preview      # 本地预览构建产物
```

### 6.4 页面清单（9 页）

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/login` | 管理员登录 | 账号 + 密码，成功后保存 `admin_token` 并进入控制台 |
| `/dashboard` | 控制台 | 4 张统计卡（学生用户总数 / 今日新增订单 / 今日成交金额 / 在售菜品数）+ ECharts 折线图（最近 7 天订单数）+ 柱状图（分类销量）+ 饼图（订单状态占比），**全部为真实数据库聚合，无 Mock** |
| `/user` | 学生用户 | 只读、分页、关键字搜索（昵称/手机号/学号/宿舍） |
| `/category` | 菜品分类 | 新增 / 编辑 / 删除 / 排序 / 启用禁用；分类下有菜品时删除被拒绝 |
| `/food` | 菜品管理 | 分页 / 查询 / 新增 / 编辑 / 改库存 / 上下架 / 删除 / 图片上传；价格与库存不得为负 |
| `/cart` | 购物车查看 | 只读、分页、学生关键字查询（不提供修改入口） |
| `/order` | 订单管理 | 分页 / 状态筛选 / 时间范围 / 关键字；详情抽屉；接单（1→2）、完成（2→3） |
| `/notice` | 公告管理 | 列表 / 新增 / 编辑 / 删除 / 显示隐藏 |
| `/profile` | 个人中心 | 头像上传、账号与姓名展示、修改密码、退出登录（**不提供 admin_name 修改**） |

---

## 七、自动化测试

### 7.1 准备测试库

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS campus_order_test DEFAULT CHARACTER SET utf8mb4;"
```

`backend/tests/conftest.py` 会自动把 `database.sql` 的库名替换为测试库名后建表，并在**每个用例前 TRUNCATE + 重新播种**，保证用例互相独立。

> **安全说明**：若 `TEST_DB_NAME` 被误配为业务库名 `campus_order`，测试启动即抛错并拒绝运行，避免误删真实数据。

### 7.2 运行测试

```bash
cd backend
python -m pytest -q                 # 全量
python -m pytest -v                 # 明细
python -m pytest tests/test_04_order.py -q   # 单文件
```

覆盖 40 项要求（注册/重复手机号/登录/错误密码/学生 Token/管理员 Token/Token 串用/Token 无效/分类/菜品/未登录浏览/加购/超库存加购/改购物车/删购物车/越权购物车/空车下单/正常下单/后端价格/扣库存/**并发库存**/模拟支付/重复支付/取消待支付/取消待接单/重复取消/配送中禁取消/取消恢复库存/超时取消/超时恢复库存/越权订单/接单/非法接单/完成/重复完成/销量只加一次/公告/图片上传/非法图片/Dashboard）及若干状态机与边界用例。

实际结果见 `docs/自动测试报告.md`。

---

## 八、统一约定

### 8.1 API 返回格式

所有接口（含异常）一律返回：

```json
{ "code": 200, "msg": "文本", "data": {} }
```

| code | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 / 业务错误 |
| 401 | 未登录 / Token 失效 / 权限不匹配 |
| 500 | 服务异常 |

后端已注册全局异常处理器，**永远不会把 Flask 的 HTML 错误页返回给前端**。

### 8.2 Token 规则

- 除登录接口外，需登录的接口请求头携带 `Authorization: Bearer {token}`
- JWT Payload 包含 `id` / `role` / `exp`；`role=0` 学生、`role=1` 管理员
- **数据库表中不存在 `role` 字段**，角色只存在于 JWT
- 学生 Token 只能访问学生接口，管理员 Token 只能访问管理员接口，串用一律 `code=401`
- 前端分别保存 `student_token`（小程序）与 `admin_token`（PC 后台），**不共用 Key**

### 8.3 密码安全

- 使用 Werkzeug `generate_password_hash()` / `check_password_hash()`
- 数据库只保存 `password_hash`，无明文密码、无 API 返回哈希、无日志输出密码、前端不保存密码

### 8.4 图片规则

- 上传目录：`backend/static/upload/`
- 允许类型：`jpg` / `jpeg` / `png` / `webp`，单张 ≤ 2MB
- 扩展名白名单 + MIME 校验 + 文件头（Magic Bytes）校验三重防护
- 使用 UUID 随机文件名，不使用用户原始文件名（防路径穿越 / 覆盖 / 恶意文件名）
- **数据库字段只保存文件名**（如 `a1b2c3.jpg`），禁止保存完整 URL；前端拼接 `STATIC_BASE`
- **菜品未设置图片时 `food.food_img` 必须为空字符串**，绝不写入 `food-default.jpg`
- `food-default.jpg` / `default_user.jpg` 是**全站共享兜底图**，只在下列三种情况由前端显示，且**永不写库、永不被删除**：
  1. 图片字段为空（菜品未设置图片）
  2. 图片加载失败（`<image>` / `<el-image>` 的 `@error` 已触发）
  3. 后端仍残留历史的占位图名（前端等价视为"未设置"）
- 前端图片地址**只有一个生成入口**：小程序 `utils/config.js` 的 `imageUrl()`、PC `src/config.js` 的 `imageUrl()`；所有 `<image>` 必须带 `@error` 兜底

### 8.5 菜品图片链路（管理员改图 → 小程序生效）

```
PC 后台「菜品管理」→ 新增/编辑 → 选择图片 → 保存
   ↓ multipart/form-data（字段 food_img）
POST /api/admin/food/save → save_uploaded_image() 三重校验 → UUID 文件名落盘
   ↓
UPDATE/INSERT food.food_img = 'UUID.png'（只存文件名）
   ↓
GET /api/food/list → 返回 food_img 文件名
   ↓
小程序 imageUrl(food_img) → STATIC_BASE + 文件名 → <image> 显示真实图片
```

- **编辑时不传图片 → 保留原图**（不会把已有图片清空）
- 编辑时传了新图片 → 旧图片文件自动清理（共享兜底图除外）
- 一次操作完成"改信息 + 换图"，无需额外的菜品图片上传接口

### 8.6 金额与库存

- MySQL 使用 `DECIMAL(10,2)`，Python 全程 `Decimal`，禁止核心金额使用 `float`
- 下单使用 `SELECT ... FOR UPDATE` 行级锁 + 条件扣减 `stock = stock - n WHERE stock >= n` 双重保障
- 所有金额、用户身份、订单状态一律以后端为准，前端仅展示

---

## 九、订单状态机

```
0 待支付 ──支付──▶ 1 待接单 ──接单──▶ 2 配送中 ──完成──▶ 3 已完成
   │                  │
   └──── 取消 ────────┴────▶ 4 已取消
        （超时 15 分钟自动取消同样落到 4）
```

| 合法迁移 | 触发方 |
| --- | --- |
| 0 → 1 | 学生：`POST /api/order/pay`（模拟支付，写入 `pay_time`） |
| 1 → 2 | 管理员：`POST /api/admin/order/receive` |
| 2 → 3 | 管理员：`POST /api/admin/order/finish`（同时按明细累加 `food.sales`） |
| 0 → 4 / 1 → 4 | 学生取消 / APScheduler 超时取消（同时按明细恢复库存） |

非法迁移（`0→2`、`0→3`、`1→3`、`2→1`、`2→4`、`3→4`、`4→任意`）一律返回 `code=400`。

- 销量只在 `2 → 3` 时增加，重复完成不会重复累加
- 取消会按 `order_item` 恢复库存，重复取消不会重复恢复

---

## 十、登出说明（V1.0 已知限制）

数据库结构**冻结为 8 张表**，不新增 Token 黑名单表，因此：

- `POST /api/user/logout` 与 `POST /api/admin/logout` 服务端只返回成功，**不吊销 JWT**
- 登出为客户端行为：前端清除本地 `student_token` / `admin_token`
- JWT 已设置合理较短的有效期（学生 24 小时、管理员 12 小时，可在 `.env` 调整）
- **V1.0 logout 不提供服务端 JWT 黑名单**

---

## 十一、常见问题

**Q1：小程序请求报「网络异常，请检查后端服务是否已启动」**
1. 后端是否已 `python app.py` 启动，`/api/health` 是否返回 `status: UP`
2. `miniprogram/utils/config.js` 的 IP 是否为本机当前局域网 IP（`ipconfig` 查看）
3. 手机与电脑是否在同一局域网；Windows 防火墙是否放行 5000 端口
4. 微信开发者工具需勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」

**Q2：图片不显示**
1. 数据库只存文件名，`STATIC_BASE` 拼接是否正确（结尾必须带 `/`）
2. 文件是否真实存在于 `backend/static/upload/`
3. 后端是否已重启（静态目录在启动时挂载）

**Q3：PC 后台登录后马上跳回登录页**
- 检查后端 `JWT_SECRET` 是否稳定（重启后端不会改变）；`localStorage` 中的 `admin_token` 是否被浏览器隐私模式清理

**Q4：下单提示「库存不足」**
- 下单会在事务内重新锁定并校验库存，若期间被其他同学买走会明确提示剩余数量 —— 这是防超卖的预期行为

**Q5：订单超时没有被自动取消**
1. `.env` 中 `ENABLE_SCHEDULER` 是否为 `1`
2. 后端日志是否出现 `[scheduler] 已启动`
3. 订单是否确实已超过 `ORDER_TIMEOUT_MINUTES` 分钟且仍为「待支付」

**Q6：`pip install` 报 MySQL 相关编译错误**
- `PyMySQL` 是纯 Python 实现，无需编译；如报 `mysqlclient` 相关错误，请确认未误装该包

**Q7：pytest 报「拒绝在业务库上运行测试」**
- `TEST_DB_NAME` 不能等于 `campus_order`，请在 `.env` 中修正

**Q8：uni-app 页面路径 404 / TabBar 不显示**
- 执行 `node miniprogram/scripts/check-project.js` 校验页面注册与 TabBar 图标

---

## 十二、接口总览

学生端 17 组 + 1 组模拟支付（17A）= 18 个接口；管理员端 11 组原始接口 + 7 个最小必要补充接口。

详见 `docs/接口补充说明.md`。

---

## 十三、默认地址速查

| 项 | 值 |
| --- | --- |
| API Base URL | `http://192.168.0.103:5000/api` |
| 图片基础路径 | `http://192.168.0.103:5000/static/upload/` |
| 后端端口 | `5000`（`0.0.0.0`） |
| PC 后台开发端口 | `5173` |
| 图片上传目录 | `backend/static/upload/` |
| 测试库 | `campus_order_test` |
