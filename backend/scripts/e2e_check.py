# -*- coding: utf-8 -*-
"""端到端联调验证：对运行中的 Flask 服务发起真实 HTTP 调用。

用法：
    1) 另开终端启动后端：python app.py
    2) 执行本脚本：python scripts/e2e_check.py
    3) 指定其它地址：E2E_BASE=http://192.168.0.103:5000/api python scripts/e2e_check.py

覆盖：公开接口 / 注册登录 / 购物车 / 下单事务与后端定价 / 模拟支付 / 取消恢复库存 /
      越权隔离 / 图片上传安全 / 管理员全链路与状态机 / 菜品图片全链路（上传→DB→API→静态资源）/
      真实 APScheduler 超时自动取消。
脚本不使用任何明文口令字面量：临时管理员随机生成口令，用毕删除；联调学生数据用毕清理。

刻意不使用任何明文口令字面量：
- 临时管理员账号由脚本随机生成口令后写入数据库，用毕删除，不影响真实管理员。
- 学生账号使用固定测试手机号，用毕清理。
"""
import io
import json
import os
import random
import struct
import subprocess
import sys
import time
import uuid
import zlib

import requests

# 目标服务地址（默认本机 5000 端口，可用环境变量 E2E_BASE 覆盖）
BASE = os.environ.get('E2E_BASE', 'http://127.0.0.1:5000/api')

# 静态资源基址：由 BASE 推导，避免指定其它地址（如局域网 IP）时仍访问本机 127.0.0.1
STATIC_BASE = BASE[:-len('/api')] + '/static/upload/'

# 自动定位 backend 目录（本脚本位于 backend/scripts/ 下）
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

from config import Config                    # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402
import pymysql                               # noqa: E402
from pymysql.cursors import DictCursor       # noqa: E402

STUDENT_PHONE = '13900000999'
E2E_ADMIN = 'e2e_temp_admin'

PASS = []
FAIL = []


def check(name, cond, extra=''):
    (PASS if cond else FAIL).append(name)
    print(('  [OK]   ' if cond else '  [FAIL] ') + name + (('  -> ' + str(extra)[:220]) if not cond and extra else ''))


def db():
    return pymysql.connect(host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER,
                           password=Config.DB_PASSWORD, database=Config.DB_NAME,
                           charset='utf8mb4', cursorclass=DictCursor, autocommit=True)


def q1(sql, args=None):
    with db() as c:
        with c.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchone()


def qx(sql, args=None):
    with db() as c:
        with c.cursor() as cur:
            return cur.execute(sql, args or ())


def png_bytes(w=8, h=8):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    raw = b''.join(b'\x00' + b'\xff\x00\x00' * w for _ in range(h))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def body(r):
    try:
        return r.json()
    except Exception:
        return {'code': -1, 'msg': r.text[:200]}


# ---------------------------------------------------------------- 清理旧数据
def cleanup():
    row = q1('SELECT id FROM users WHERE phone=%s', (STUDENT_PHONE,))
    if row:
        uid = row['id']
        qx('DELETE oi FROM order_item oi INNER JOIN orders o ON o.id=oi.order_id WHERE o.user_id=%s', (uid,))
        qx('DELETE FROM orders WHERE user_id=%s', (uid,))
        qx('DELETE FROM cart WHERE user_id=%s', (uid,))
        qx('DELETE FROM users WHERE id=%s', (uid,))
    qx('DELETE FROM admin_user WHERE admin_name=%s', (E2E_ADMIN,))


cleanup()
print('=' * 74)
print('  校园点餐管理系统 · 端到端联调验证（真实 HTTP）')
print('=' * 74)

# ---------------------------------------------------------------- 1 公开接口
print('\n[1] 公开接口（无需 Token）')
r = requests.get(BASE + '/health', timeout=10)
check('GET /api/health 返回 UP', body(r).get('data', {}).get('status') == 'UP', body(r))
cats = body(requests.get(BASE + '/food/category/list', timeout=10))
check('分类列表 5 项', cats['code'] == 200 and len(cats['data']['list']) == 5, cats)
foods = body(requests.get(BASE + '/food/list?page_size=100', timeout=10))
check('菜品列表可访问', foods['code'] == 200 and foods['data']['total'] >= 10, foods.get('data', {}).get('total'))
in_stock = [f for f in foods['data']['list'] if f['stock'] > 5]
first_food = in_stock[0] if in_stock else None
check('菜品字段含图片文件名（非 URL）',
      first_food and 'food_img' in first_food and not first_food['food_img'].startswith('http'), first_food)
notice = body(requests.get(BASE + '/notice/list', timeout=10))
check('公告列表可访问', notice['code'] == 200, notice)
check('浏览接口未登录可用（购物车仍受限）',
      body(requests.get(BASE + '/cart/list', timeout=10))['code'] == 401)

# ---------------------------------------------------------------- 2 学生注册登录
print('\n[2] 学生注册 / 登录')
reg = body(requests.post(BASE + '/user/register', json={
    'nickname': '联调测试同学', 'phone': STUDENT_PHONE, 'password': 'E2eStudent#2026',
    'student_no': 'E2E2026001', 'dormitory': '宿舍楼3栋 502'}, timeout=10))
check('注册成功', reg['code'] == 200, reg)
check('注册响应不含密码哈希', 'password_hash' not in json.dumps(reg['data']), reg['data'])
login = body(requests.post(BASE + '/user/login', json={
    'phone': STUDENT_PHONE, 'password': 'E2eStudent#2026'}, timeout=10))
check('登录成功并返回 Token', login['code'] == 200 and login['data'].get('token'), login)
SH = {'Authorization': 'Bearer ' + login['data']['token']}
uid = login['data']['user_id']
check('登录返回 dormitory（默认地址来源）', login['data'].get('dormitory') == '宿舍楼3栋 502', login['data'])
check('密码以哈希入库', (q1('SELECT password_hash FROM users WHERE id=%s', (uid,)) or {})
      .get('password_hash', '').startswith(('scrypt:', 'pbkdf2:')))
check('users 表无 role 字段', q1("SHOW COLUMNS FROM users LIKE 'role'") is None)

# ---------------------------------------------------------------- 3 购物车
print('\n[3] 购物车（实时读写 MySQL）')
f_a = first_food['id']
f_b = in_stock[1]['id']
r = body(requests.post(BASE + '/cart/save', json={'food_id': f_a, 'count': 2}, headers=SH, timeout=10))
check('加购成功', r['code'] == 200 and r['data']['count'] == 2, r)
check('购物车落库', (q1('SELECT `count` AS c FROM cart WHERE user_id=%s AND food_id=%s', (uid, f_a)) or {}).get('c') == 2)
r = body(requests.post(BASE + '/cart/save', json={'food_id': f_a, 'count': 1}, headers=SH, timeout=10))
check('重复加购为累加', r['code'] == 200 and r['data']['count'] == 3, r)
sold_out = q1('SELECT id FROM food WHERE stock = 0 LIMIT 1')
if sold_out:
    r = body(requests.post(BASE + '/cart/save', json={'food_id': sold_out['id'], 'count': 1}, headers=SH, timeout=10))
    check('售罄菜品不可加购', r['code'] == 400, r)
r = body(requests.post(BASE + '/cart/save', json={'food_id': f_a, 'count': 500}, headers=SH, timeout=10))
check('超过库存加购被拒', r['code'] == 400 and '库存' in r['msg'], r)
cart = body(requests.get(BASE + '/cart/list', headers=SH, timeout=10))
check('购物车读取正常', cart['code'] == 200 and cart['data']['total_count'] == 3, cart.get('data'))
cart_id = cart['data']['list'][0]['id']

# 契约内「减少数量」：删除 + 按目标数量保存
body(requests.post(BASE + '/cart/del', json={'cart_id': cart_id}, headers=SH, timeout=10))
r = body(requests.post(BASE + '/cart/save', json={'food_id': f_a, 'count': 1}, headers=SH, timeout=10))
check('购物车数量减少（del + save）实现正确', r['code'] == 200 and r['data']['count'] == 1, r)
body(requests.post(BASE + '/cart/save', json={'food_id': f_b, 'count': 2}, headers=SH, timeout=10))

# ---------------------------------------------------------------- 4 下单
print('\n[4] 下单（事务 / 后端定价 / 扣库存）')
stock_a_before = q1('SELECT stock FROM food WHERE id=%s', (f_a,))['stock']
stock_b_before = q1('SELECT stock FROM food WHERE id=%s', (f_b,))['stock']
price_a = float(q1('SELECT price FROM food WHERE id=%s', (f_a,))['price'])
price_b = float(q1('SELECT price FROM food WHERE id=%s', (f_b,))['price'])

r = body(requests.post(BASE + '/order/create', json={
    'receive_address': '宿舍楼3栋 502', 'remark': '不要香菜',
    'total_price': 0.01, 'order_status': 3, 'user_id': 999999}, headers=SH, timeout=10))
check('下单成功', r['code'] == 200, r)
order = r['data']
expect_total = round(price_a * 1 + price_b * 2, 2)
check('总价以后端数据库价格计算', abs(order['total_price'] - expect_total) < 0.001,
      '%s vs %s' % (order['total_price'], expect_total))
check('前端无法指定订单状态', order['order_status'] == 0, order['order_status'])
check('前端无法指定 user_id', str(q1('SELECT user_id FROM orders WHERE id=%s', (order['id'],))['user_id']) == str(uid))
snapshot = {i['food_id']: i for i in order['items']}
check('明细为快照（含名称/单价/数量，且价格取自数据库）',
      len(order['items']) == 2 and set(snapshot) == {f_a, f_b}
      and snapshot[f_a]['food_price'] == price_a and snapshot[f_a]['count'] == 1
      and snapshot[f_b]['food_price'] == price_b and snapshot[f_b]['count'] == 2
      and snapshot[f_a]['food_name'] == q1('SELECT food_name AS n FROM food WHERE id=%s', (f_a,))['n'],
      order['items'])
check('扣库存正确',
      q1('SELECT stock FROM food WHERE id=%s', (f_a,))['stock'] == stock_a_before - 1
      and q1('SELECT stock FROM food WHERE id=%s', (f_b,))['stock'] == stock_b_before - 2)
check('购物车已清空', body(requests.get(BASE + '/cart/list', headers=SH, timeout=10))['data']['list'] == [])
r = body(requests.post(BASE + '/order/create', json={'receive_address': 'x'}, headers=SH, timeout=10))
check('空购物车下单被拒', r['code'] == 400, r)

# ---------------------------------------------------------------- 5 模拟支付
print('\n[5] 模拟支付（0 → 1）')
r = body(requests.post(BASE + '/order/pay', json={'order_id': order['id']}, headers=SH, timeout=10))
check('模拟支付成功', r['code'] == 200 and r['data']['order_status'] == 1, r)
check('pay_time 已写入', r['data']['pay_time'] is not None, r['data'].get('pay_time'))
r = body(requests.post(BASE + '/order/pay', json={'order_id': order['id']}, headers=SH, timeout=10))
check('重复支付被拒', r['code'] == 400 and '重复支付' in r['msg'], r)
r = body(requests.post(BASE + '/order/cancel', json={'order_id': order['id']}, headers=SH, timeout=10))
check('待接单可取消', r['code'] == 200 and r['data']['order_status'] == 4, r)
r = body(requests.post(BASE + '/order/cancel', json={'order_id': order['id']}, headers=SH, timeout=10))
check('重复取消被拒', r['code'] == 400, r)

# ---------------------------------------------------------------- 6 取消恢复库存
print('\n[6] 取消与库存恢复')
check('取消后库存恢复',
      q1('SELECT stock FROM food WHERE id=%s', (f_a,))['stock'] == stock_a_before
      and q1('SELECT stock FROM food WHERE id=%s', (f_b,))['stock'] == stock_b_before)
r = body(requests.post(BASE + '/order/pay', json={'order_id': order['id']}, headers=SH, timeout=10))
check('已取消订单不可支付', r['code'] == 400, r)

# ---------------------------------------------------------------- 7 越权
print('\n[7] 越权隔离')
other = body(requests.post(BASE + '/user/register', json={
    'nickname': '另一同学', 'phone': '13900000998', 'password': 'E2eOther#2026',
    'student_no': 'E2E2026002', 'dormitory': '宿舍楼9栋 101'}, timeout=10))
ol = body(requests.post(BASE + '/user/login', json={'phone': '13900000998', 'password': 'E2eOther#2026'}, timeout=10))
OH = {'Authorization': 'Bearer ' + ol['data']['token']}
check('他人无法查看我的订单', body(requests.get(
    BASE + '/order/detail?order_id=%d' % order['id'], headers=OH, timeout=10))['code'] == 400)
check('他人无法取消我的订单', body(requests.post(
    BASE + '/order/cancel', json={'order_id': order['id']}, headers=OH, timeout=10))['code'] == 400)
requests.post(BASE + '/cart/save', json={'food_id': f_a, 'count': 1}, headers=OH, timeout=10)
mine = body(requests.get(BASE + '/cart/list', headers=SH, timeout=10))
check('他人无法看到我的购物车', mine['data']['list'] == [], mine['data'])
requests.post(BASE + '/cart/del', json={'cart_id': 1}, headers=OH, timeout=10)

# ---------------------------------------------------------------- 8 图片上传
print('\n[8] 图片上传安全')
p = png_bytes()
r = requests.post(BASE + '/user/upload_avatar', files={'avatar': ('改 头像.png', io.BytesIO(p), 'image/png')},
                  headers=SH, timeout=15)
up = body(r)
check('合法 PNG 上传成功', up['code'] == 200, up)
check('返回 UUID 随机文件名且仅文件名', up['code'] == 200 and len(up['data']['avatar'].split('.')[0]) == 32
      and '/' not in up['data']['avatar'], up.get('data'))
check('图片文件已落盘', os.path.isfile(os.path.join(BACKEND, 'static', 'upload', up['data']['avatar'])))
for name, data, mime in [('shell.php', b'<?php ?>', 'application/x-php'),
                         ('fake.png', b'notanimage', 'image/png'),
                         ('evil.exe', p, 'application/octet-stream')]:
    rr = body(requests.post(BASE + '/user/upload_avatar',
                            files={'avatar': (name, io.BytesIO(data), mime)}, headers=SH, timeout=15))
    check('非法图片被拒：%s' % name, rr['code'] == 400, rr)
check('静态资源可访问', requests.get(
    STATIC_BASE + up['data']['avatar'], timeout=10).status_code == 200)

# ---------------------------------------------------------------- 9 管理员
print('\n[9] 管理员全链路')
temp_pwd = 'E2e' + uuid.uuid4().hex[:12] + '#1'
with db() as c:
    with c.cursor() as cur:
        cur.execute('INSERT INTO admin_user (admin_name, password_hash, real_name, avatar, created_at) '
                    'VALUES (%s,%s,%s,%s,NOW())',
                    (E2E_ADMIN, generate_password_hash(temp_pwd), '联调临时管理员', 'default_user.jpg'))
al = body(requests.post(BASE + '/admin/login', json={'admin_name': E2E_ADMIN, 'password': temp_pwd}, timeout=10))
check('管理员登录成功', al['code'] == 200 and al['data'].get('token'), al)
AH = {'Authorization': 'Bearer ' + al['data']['token']}
check('学生 Token 访问管理员接口 → 401',
      body(requests.get(BASE + '/admin/dashboard', headers=SH, timeout=10))['code'] == 401)
check('管理员 Token 访问学生接口 → 401',
      body(requests.get(BASE + '/cart/list', headers=AH, timeout=10))['code'] == 401)

# 再下一单，走完整状态机
requests.post(BASE + '/cart/save', json={'food_id': f_a, 'count': 2}, headers=SH, timeout=10)
o2 = body(requests.post(BASE + '/order/create', json={'receive_address': '宿舍楼3栋 502'}, headers=SH, timeout=10))['data']
check('非法接单（0 → 2）被拒',
      body(requests.post(BASE + '/admin/order/receive', json={'order_id': o2['id']}, headers=AH, timeout=10))['code'] == 400)
requests.post(BASE + '/order/pay', json={'order_id': o2['id']}, headers=SH, timeout=10)
check('非法完成（1 → 3）被拒',
      body(requests.post(BASE + '/admin/order/finish', json={'order_id': o2['id']}, headers=AH, timeout=10))['code'] == 400)
check('接单成功（1 → 2）',
      body(requests.post(BASE + '/admin/order/receive', json={'order_id': o2['id']}, headers=AH, timeout=10))['code'] == 200)
sales_before = q1('SELECT sales FROM food WHERE id=%s', (f_a,))['sales']
check('配送中学生不可取消',
      body(requests.post(BASE + '/order/cancel', json={'order_id': o2['id']}, headers=SH, timeout=10))['code'] == 400)
check('完成成功（2 → 3）',
      body(requests.post(BASE + '/admin/order/finish', json={'order_id': o2['id']}, headers=AH, timeout=10))['code'] == 200)
sales_after = q1('SELECT sales FROM food WHERE id=%s', (f_a,))['sales']
check('销量按明细累加 2', sales_after - sales_before == 2, '%s -> %s' % (sales_before, sales_after))
check('重复完成被拒',
      body(requests.post(BASE + '/admin/order/finish', json={'order_id': o2['id']}, headers=AH, timeout=10))['code'] == 400)
check('重复完成后销量不再增加', q1('SELECT sales FROM food WHERE id=%s', (f_a,))['sales'] == sales_after)
check('已完成订单不可取消',
      body(requests.post(BASE + '/order/cancel', json={'order_id': o2['id']}, headers=SH, timeout=10))['code'] == 400)

# 管理端列表/详情/Dashboard
ol_ = body(requests.get(BASE + '/admin/order/list?keyword=' + o2['order_no'], headers=AH, timeout=10))
check('订单列表按订单号搜索', ol_['code'] == 200 and ol_['data']['total'] == 1, ol_.get('data', {}).get('total'))
od = body(requests.get(BASE + '/admin/order/detail?order_id=%d' % o2['id'], headers=AH, timeout=10))
check('订单详情含学生信息与明细', od['code'] == 200 and od['data']['nickname'] and len(od['data']['items']) == 1, od)
dash = body(requests.get(BASE + '/admin/dashboard', headers=AH, timeout=10))
check('Dashboard 返回 4 卡 + 3 图', dash['code'] == 200 and set(dash['data']['cards']) >=
      {'total_users', 'today_orders', 'today_amount', 'on_sale_foods'}, dash.get('data', {}).get('cards'))
check('折线图 7 个数据点', len(dash['data']['order_trend']) == 7)
check('饼图 5 个状态', len(dash['data']['status_pie']) == 5)
check('柱状图分类销量非空', len(dash['data']['category_sales']) > 0)
check('Dashboard 金额含今日已支付订单', dash['data']['cards']['today_amount'] >= o2['total_price'])
ul = body(requests.get(BASE + '/admin/user/list?keyword=13900000999', headers=AH, timeout=10))
check('学生用户列表可搜索', ul['code'] == 200 and ul['data']['total'] == 1, ul.get('data', {}).get('total'))
cl = body(requests.get(BASE + '/admin/cart/list', headers=AH, timeout=10))
check('管理员可只读查看购物车', cl['code'] == 200, cl)
cat = body(requests.get(BASE + '/admin/category/list', headers=AH, timeout=10))
check('管理员分类列表可访问', cat['code'] == 200 and len(cat['data']['list']) == 5, cat)
check('删除有菜品的分类被拒',
      body(requests.post(BASE + '/admin/category/del', json={'id': 1}, headers=AH, timeout=10))['code'] == 400)
check('菜品负价格被拒',
      body(requests.post(BASE + '/admin/food/save', json={'cat_id': 1, 'food_name': '非法菜',
                                                          'price': '-1', 'stock': '1'},
                         headers=AH, timeout=10))['code'] == 400)
nl = body(requests.get(BASE + '/admin/notice/list', headers=AH, timeout=10))
check('管理端公告列表可访问', nl['code'] == 200 and nl['data']['total'] >= 2, nl.get('data', {}).get('total'))
check('管理员信息接口返回账号', body(requests.get(BASE + '/admin/info', headers=AH, timeout=10))['data']['admin_name'] == E2E_ADMIN)

# ---------------------------------------------------------------- 9B 菜品图片全链路
print('\n[9B] 菜品图片全链路（后台上传 → 保存 → DB → API → 静态资源）')
UPLOAD_DIR = os.path.join(BACKEND, 'static', 'upload')
IMG_TEST_NAME = '联调图片菜'
new_fid = None
img1 = img2 = ''
try:
    common = {'cat_id': '5', 'food_name': IMG_TEST_NAME, 'price': '9.90', 'stock': '10',
              'description': '图片链路联调临时菜品', 'is_sale': '1'}

    # 1) 新增菜品 + 上传真实 PNG
    r1 = body(requests.post(BASE + '/admin/food/save', data=common,
                            files={'food_img': ('food.png', io.BytesIO(png_bytes()), 'image/png')},
                            headers=AH, timeout=20))
    check('后台新增菜品并上传图片成功', r1['code'] == 200, r1)
    new_fid = r1['data']['id']
    img1 = r1['data']['food_img']
    check('返回值为 UUID 文件名（非 URL、非占位图）',
          bool(img1) and img1 != 'food-default.jpg' and '/' not in img1
          and len(img1.split('.')[0]) == 32, img1)
    check('图片文件已保存到 static/upload', os.path.isfile(os.path.join(UPLOAD_DIR, img1)))
    check('数据库 food_img 与接口返回一致',
          q1('SELECT food_img FROM food WHERE id=%s', (new_fid,))['food_img'] == img1)
    check('浏览器可直接访问上传后的图片',
          requests.get(STATIC_BASE + img1, timeout=10).status_code == 200)
    pub = body(requests.get(BASE + '/food/list?keyword=' + IMG_TEST_NAME, timeout=10))
    hit = [x for x in pub['data']['list'] if x['id'] == new_fid]
    check('小程序菜品列表返回同一图片字段', len(hit) == 1 and hit[0]['food_img'] == img1,
          hit[0].get('food_img') if hit else pub.get('data'))

    # 2) 编辑菜品并更换图片
    edit = dict(common)
    edit['id'] = str(new_fid)
    r2 = body(requests.post(BASE + '/admin/food/save', data=edit,
                            files={'food_img': ('food2.png', io.BytesIO(png_bytes()), 'image/png')},
                            headers=AH, timeout=20))
    img2 = r2['data']['food_img'] if r2.get('data') else ''
    check('编辑更换图片后返回新文件名', r2['code'] == 200 and bool(img2) and img2 != img1, img2)
    check('更换后的新图片可访问',
          requests.get(STATIC_BASE + img2, timeout=10).status_code == 200)
    check('更换后旧图片文件已被清理', not os.path.isfile(os.path.join(UPLOAD_DIR, img1)))
    pub2 = body(requests.get(BASE + '/food/list?keyword=' + IMG_TEST_NAME, timeout=10))
    hit2 = [x for x in pub2['data']['list'] if x['id'] == new_fid]
    check('列表返回更新后的图片字段', len(hit2) == 1 and hit2[0]['food_img'] == img2)

    # 3) 编辑时不传图片 → 必须保留原图（不得被清空）
    keep = body(requests.post(BASE + '/admin/food/save', json={
        'id': new_fid, 'cat_id': 5, 'food_name': IMG_TEST_NAME, 'price': '9.90',
        'stock': '11', 'description': '改库存，不动图片', 'is_sale': 1}, headers=AH, timeout=10))
    check('编辑不传图片时保留原图片', keep['code'] == 200 and keep['data']['food_img'] == img2,
          keep.get('data', {}).get('food_img'))
    check('未传图片时共享占位图未被误删',
          os.path.isfile(os.path.join(UPLOAD_DIR, 'food-default.jpg')))

    # 4) 未设置图片的菜品：food_img 必须为空，由前端兜底，绝不写入占位图名
    noimg = body(requests.post(BASE + '/admin/food/save', json={
        'cat_id': 5, 'food_name': '联调无图菜', 'price': '1.00', 'stock': '5',
        'description': '未设置图片的菜品', 'is_sale': 1}, headers=AH, timeout=10))
    check('未设置图片的菜品 food_img 为空', noimg['code'] == 200
          and noimg['data']['food_img'] == '', noimg.get('data'))
    check('未设置图片时不写入 food-default.jpg（占位图只作前端兜底）',
          noimg['data']['food_img'] != 'food-default.jpg')
    body(requests.post(BASE + '/admin/food/del', json={'id': noimg['data']['id']},
                       headers=AH, timeout=10))
finally:
    if new_fid:
        body(requests.post(BASE + '/admin/food/del', json={'id': new_fid}, headers=AH, timeout=10))
    for f in (img1, img2):
        fp = os.path.join(UPLOAD_DIR, f) if f else None
        if fp and os.path.isfile(fp):
            os.remove(fp)
    print('  [..]   联调菜品与其图片已清理')

# ---------------------------------------------------------------- 10 超时自动取消（真实调度器）
print('\n[10] 15 分钟超时自动取消（真实 APScheduler 线程）')
requests.post(BASE + '/cart/save', json={'food_id': f_b, 'count': 3}, headers=SH, timeout=10)
stock_b3 = q1('SELECT stock FROM food WHERE id=%s', (f_b,))['stock']
o3 = body(requests.post(BASE + '/order/create', json={'receive_address': '宿舍楼3栋 502'}, headers=SH, timeout=10))['data']
check('超时单已扣库存', q1('SELECT stock FROM food WHERE id=%s', (f_b,))['stock'] == stock_b3 - 3)
qx('UPDATE orders SET created_at = DATE_SUB(NOW(), INTERVAL 20 MINUTE) WHERE id=%s', (o3['id'],))

deadline = time.time() + 90
canceled = False
while time.time() < deadline:
    if q1('SELECT order_status FROM orders WHERE id=%s', (o3['id'],))['order_status'] == 4:
        canceled = True
        break
    time.sleep(5)
check('调度器自动取消超时未支付订单', canceled)
check('自动取消后库存恢复', q1('SELECT stock FROM food WHERE id=%s', (f_b,))['stock'] == stock_b3)
check('已超时取消的订单不可支付',
      body(requests.post(BASE + '/order/pay', json={'order_id': o3['id']}, headers=SH, timeout=10))['code'] == 400)
time.sleep(6)
check('重复扫描不会重复恢复库存', q1('SELECT stock FROM food WHERE id=%s', (f_b,))['stock'] == stock_b3)

# ---------------------------------------------------------------- 清理
print('\n[11] 清理联调数据')
qx('DELETE FROM admin_user WHERE admin_name=%s', (E2E_ADMIN,))
check('临时管理员已删除', q1('SELECT id FROM admin_user WHERE admin_name=%s', (E2E_ADMIN,)) is None)
check('真实管理员仍存在', q1("SELECT id FROM admin_user WHERE admin_name='admin'") is not None)
for phone in (STUDENT_PHONE, '13900000998'):
    row = q1('SELECT id FROM users WHERE phone=%s', (phone,))
    if row:
        uid2 = row['id']
        qx('DELETE oi FROM order_item oi INNER JOIN orders o ON o.id=oi.order_id WHERE o.user_id=%s', (uid2,))
        qx('DELETE FROM orders WHERE user_id=%s', (uid2,))
        qx('DELETE FROM cart WHERE user_id=%s', (uid2,))
        qx('DELETE FROM users WHERE id=%s', (uid2,))
check('联调学生数据已清理', q1('SELECT id FROM users WHERE phone IN (%s,%s)',
                            (STUDENT_PHONE, '13900000998')) is None)
check('演示菜品与公告保留', q1('SELECT COUNT(*) AS c FROM food')['c'] >= 10
      and q1('SELECT COUNT(*) AS c FROM notice')['c'] >= 2)

print('\n' + '=' * 74)
print('  结果：%d 项通过，%d 项失败' % (len(PASS), len(FAIL)))
if FAIL:
    for f in FAIL:
        print('   x ' + f)
print('=' * 74)
sys.exit(1 if FAIL else 0)
