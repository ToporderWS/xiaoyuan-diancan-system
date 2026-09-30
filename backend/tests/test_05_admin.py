# -*- coding: utf-8 -*-
"""用例 32~40：管理员接单 / 完成 / 销量 / 公告 / 图片上传 / 分类菜品管理 / Dashboard。"""
import io
import os
import struct
import zlib

from conftest import (ADMIN_NAME, ADMIN_PWD, exec_sql, fetch_all, fetch_one, seed_food,
                      student_headers)

ADDR = '宿舍楼3栋 502'
P1 = '13800000301'


def _ah(client):
    body = client.post('/api/admin/login',
                       json={'admin_name': ADMIN_NAME, 'password': ADMIN_PWD}).get_json()
    assert body['code'] == 200, body
    return {'Authorization': 'Bearer ' + body['data']['token']}


def _order(client, headers, addr=ADDR):
    return client.post('/api/order/create', json={'receive_address': addr},
                       headers=headers).get_json()['data']


def _paid_order(client, headers, fid, count=1):
    client.post('/api/cart/save', json={'food_id': fid, 'count': count}, headers=headers)
    o = _order(client, headers)
    client.post('/api/order/pay', json={'order_id': o['id']}, headers=headers)
    return o['id']


def _png_bytes(w=8, h=8):
    """生成一个最小合法 PNG（用于上传测试，避免依赖外部图片文件）。"""
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    raw = b''.join(b'\x00' + b'\xff\x00\x00' * w for _ in range(h))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw))
            + chunk(b'IEND', b''))


# ------------------------------------------------------------------ 32 接单
def test_32_admin_receive(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    ah = _ah(client)
    oid = _paid_order(client, headers, fid)

    body = client.post('/api/admin/order/receive', json={'order_id': oid},
                       headers=ah).get_json()
    assert body['code'] == 200
    assert body['data']['order_status'] == 2
    assert body['data']['status_text'] == '配送中'
    assert fetch_one('SELECT order_status FROM orders WHERE id=%s', (oid,))['order_status'] == 2


# ------------------------------------------------------------------ 33 非法接单
def test_33_admin_receive_illegal(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    ah = _ah(client)
    # 未支付（0）接单
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    oid = _order(client, headers)['id']
    assert client.post('/api/admin/order/receive', json={'order_id': oid},
                       headers=ah).get_json()['code'] == 400
    # 已取消（4）接单
    client.post('/api/order/cancel', json={'order_id': oid}, headers=headers)
    assert client.post('/api/admin/order/receive', json={'order_id': oid},
                       headers=ah).get_json()['code'] == 400
    # 已完成（3）接单
    oid2 = _paid_order(client, headers, fid)
    assert client.post('/api/admin/order/receive', json={'order_id': oid2},
                       headers=ah).get_json()['code'] == 200
    assert client.post('/api/admin/order/finish', json={'order_id': oid2},
                       headers=ah).get_json()['code'] == 200
    assert client.post('/api/admin/order/receive', json={'order_id': oid2},
                       headers=ah).get_json()['code'] == 400
    # 重复接单
    oid3 = _paid_order(client, headers, fid)
    assert client.post('/api/admin/order/receive', json={'order_id': oid3},
                       headers=ah).get_json()['code'] == 200
    again = client.post('/api/admin/order/receive', json={'order_id': oid3},
                        headers=ah).get_json()
    assert again['code'] == 400
    assert '重复' in again['msg']
    # 不存在的订单 / 参数错误
    assert client.post('/api/admin/order/receive', json={'order_id': 999999},
                       headers=ah).get_json()['code'] == 400
    assert client.post('/api/admin/order/receive', json={'order_id': 'x'},
                       headers=ah).get_json()['code'] == 400


# ------------------------------------------------------------------ 34 完成订单
def test_34_admin_finish(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    ah = _ah(client)
    oid = _paid_order(client, headers, fid, 2)
    assert client.post('/api/admin/order/receive', json={'order_id': oid},
                       headers=ah).get_json()['code'] == 200
    body = client.post('/api/admin/order/finish', json={'order_id': oid},
                       headers=ah).get_json()
    assert body['code'] == 200
    assert body['data']['order_status'] == 3
    assert body['data']['status_text'] == '已完成'
    assert body['data']['finish_time'] is not None
    # 未接单直接完成（0→3 / 1→3）非法
    oid2 = _paid_order(client, headers, fid)
    assert client.post('/api/admin/order/finish', json={'order_id': oid2},
                       headers=ah).get_json()['code'] == 400


# ------------------------------------------------------------------ 35 重复完成
def test_35_finish_twice(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    ah = _ah(client)
    oid = _paid_order(client, headers, fid)
    client.post('/api/admin/order/receive', json={'order_id': oid}, headers=ah)
    assert client.post('/api/admin/order/finish', json={'order_id': oid},
                       headers=ah).get_json()['code'] == 200
    again = client.post('/api/admin/order/finish', json={'order_id': oid},
                        headers=ah).get_json()
    assert again['code'] == 400
    assert '重复' in again['msg']


# ------------------------------------------------------------------ 36 销量只加一次
def test_36_sales_increase_once(client):
    f1 = seed_food(1, '销量菜', '10.00', 20)
    f2 = seed_food(1, '副菜', '5.00', 20)
    headers, _ = student_headers(client, P1)
    ah = _ah(client)
    client.post('/api/cart/save', json={'food_id': f1, 'count': 3}, headers=headers)
    client.post('/api/cart/save', json={'food_id': f2, 'count': 1}, headers=headers)
    o = _order(client, headers)
    client.post('/api/order/pay', json={'order_id': o['id']}, headers=headers)

    assert fetch_one('SELECT sales FROM food WHERE id=%s', (f1,))['sales'] == 0
    client.post('/api/admin/order/receive', json={'order_id': o['id']}, headers=ah)
    assert fetch_one('SELECT sales FROM food WHERE id=%s', (f1,))['sales'] == 0
    client.post('/api/admin/order/finish', json={'order_id': o['id']}, headers=ah)
    assert fetch_one('SELECT sales FROM food WHERE id=%s', (f1,))['sales'] == 3
    assert fetch_one('SELECT sales FROM food WHERE id=%s', (f2,))['sales'] == 1

    # 重复完成失败后销量不得变化
    client.post('/api/admin/order/finish', json={'order_id': o['id']}, headers=ah)
    assert fetch_one('SELECT sales FROM food WHERE id=%s', (f1,))['sales'] == 3
    # 取消订单不增加销量
    o2 = _paid_order(client, headers, f1, 2)
    client.post('/api/order/cancel', json={'order_id': o2}, headers=headers)
    assert fetch_one('SELECT sales FROM food WHERE id=%s', (f1,))['sales'] == 3


# ------------------------------------------------------------------ 37 公告
def test_37_notice_crud(client):
    ah = _ah(client)
    # 新增
    add = client.post('/api/admin/notice/save', json={
        'title': '校园食堂今日上新', 'content': '欢迎选购', 'is_show': 1}, headers=ah).get_json()
    assert add['code'] == 200
    nid = add['data']['id']
    assert add['data']['publish_time'] is not None

    # 公开列表只读 is_show=1
    pub = client.get('/api/notice/list').get_json()['data']['list']
    assert len(pub) == 1 and pub[0]['title'] == '校园食堂今日上新'

    # 编辑
    upd = client.post('/api/admin/notice/save', json={
        'id': nid, 'title': '标题已更新', 'content': '新内容', 'is_show': 0}, headers=ah).get_json()
    assert upd['code'] == 200
    assert client.get('/api/notice/list').get_json()['data']['list'] == []

    # 管理端列表可见隐藏项
    adm = client.get('/api/admin/notice/list', headers=ah).get_json()['data']
    assert adm['total'] == 1 and adm['list'][0]['is_show'] == 0
    adm_kw = client.get('/api/admin/notice/list?keyword=已更新', headers=ah).get_json()['data']
    assert adm_kw['total'] == 1

    # 删除
    assert client.post('/api/admin/notice/del', json={'id': nid},
                       headers=ah).get_json()['code'] == 200
    assert fetch_one('SELECT COUNT(*) AS c FROM notice')['c'] == 0
    assert client.post('/api/admin/notice/del', json={'id': nid},
                       headers=ah).get_json()['code'] == 400
    assert client.post('/api/admin/notice/save', json={'title': ''},
                       headers=ah).get_json()['code'] == 400


# ------------------------------------------------------------------ 38 图片上传
def test_38_avatar_upload(client, app):
    headers, _ = student_headers(client, P1)
    png = _png_bytes()

    r = client.post('/api/user/upload_avatar',
                    data={'avatar': (io.BytesIO(png), 'my avatar.png')},
                    content_type='multipart/form-data', headers=headers)
    body = r.get_json()
    assert body['code'] == 200, body
    name = body['data']['avatar']
    # 数据库只保存文件名，不保存 URL
    assert '/' not in name and 'http' not in name
    assert name.endswith('.png')
    # 使用 UUID 随机名，不使用原始文件名（防覆盖 / 恶意文件名）
    assert 'my avatar' not in name and ' ' not in name
    assert len(name.split('.')[0]) == 32             # uuid4().hex
    # 文件确实落盘
    target = os.path.join(app.config['UPLOAD_FOLDER'], name)
    assert os.path.isfile(target) and os.path.getsize(target) == len(png)
    assert fetch_one('SELECT avatar FROM users WHERE phone=%s', (P1,))['avatar'] == name

    # 管理员头像同样支持
    ah = _ah(client)
    r2 = client.post('/api/admin/upload_avatar',
                     data={'avatar': (io.BytesIO(png), 'a.png')},
                     content_type='multipart/form-data', headers=ah)
    assert r2.get_json()['code'] == 200
    assert client.post('/api/admin/upload_avatar',
                       data={'avatar': (io.BytesIO(png), 'a.png')},
                       content_type='multipart/form-data').get_json()['code'] == 401

    # 菜品图片通过 food/save multipart 一并上传（无需额外接口）
    save = client.post('/api/admin/food/save', data={
        'cat_id': '1', 'food_name': '带图菜品', 'price': '9.90', 'stock': '10',
        'description': '描述', 'is_sale': '1',
        'food_img': (io.BytesIO(png), 'dish.png'),
    }, content_type='multipart/form-data', headers=ah).get_json()
    assert save['code'] == 200, save
    assert save['data']['food_img'].endswith('.png')
    assert '/' not in save['data']['food_img']


# ------------------------------------------------------------------ 39 非法图片
def test_39_invalid_image_upload(client, app):
    headers, _ = student_headers(client, P1)
    cases = [
        (io.BytesIO(b'<?php echo 1; ?>'), 'shell.php', '仅支持'),      # 扩展名白名单
        (io.BytesIO(b'notanimage'), 'fake.png', '内容'),               # 文件头校验
        (io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 10), 'evil.exe', '仅支持'),
        (io.BytesIO(b''), 'empty.png', '空'),                          # 空文件
    ]
    for stream, name, kw in cases:
        body = client.post('/api/user/upload_avatar',
                           data={'avatar': (stream, name)},
                           content_type='multipart/form-data', headers=headers).get_json()
        assert body['code'] == 400, (name, body)
        assert kw in body['msg'], (name, body['msg'])

    # 路径穿越文件名
    body = client.post('/api/user/upload_avatar',
                       data={'avatar': (io.BytesIO(_png_bytes()), '../../../../evil.png')},
                       content_type='multipart/form-data', headers=headers).get_json()
    assert body['code'] == 200
    name = body['data']['avatar']
    assert os.path.sep not in name and '/' not in name
    # 未上传文件
    assert client.post('/api/user/upload_avatar', data={},
                       content_type='multipart/form-data',
                       headers=headers).get_json()['code'] == 400
    # 上传目录内没有出现越界文件
    outside = os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'evil.png')
    assert not os.path.exists(outside)


# ------------------------------------------------------------------ 40 Dashboard
def test_40_dashboard(client):
    ah = _ah(client)
    headers, _ = student_headers(client, P1)
    f1 = seed_food(1, '早餐菜', '6.00', 20)
    f2 = seed_food(2, '快餐菜', '16.00', 20)
    seed_food(3, '下架菜', '10.00', 5, is_sale=0)

    student_headers(client, '13800000302')

    o1 = _paid_order(client, headers, f1, 2)
    client.post('/api/admin/order/receive', json={'order_id': o1}, headers=ah)
    client.post('/api/admin/order/finish', json={'order_id': o1}, headers=ah)
    o2 = _paid_order(client, headers, f2, 1)
    client.post('/api/admin/order/receive', json={'order_id': o2}, headers=ah)
    client.post('/api/cart/save', json={'food_id': f1, 'count': 1}, headers=headers)
    _order(client, headers)

    body = client.get('/api/admin/dashboard', headers=ah).get_json()
    assert body['code'] == 200
    d = body['data']
    assert d['cards']['total_users'] == 2
    assert d['cards']['today_orders'] == 3
    assert d['cards']['today_amount'] == 28.0      # 6*2 + 16*1（未支付的 6 元不计入）
    assert d['cards']['on_sale_foods'] == 2
    # 此时 o2 已接单、第三笔未支付 → 待接单数为 0；再支付一笔后应变为 1
    assert d['cards']['pending_accept_orders'] == 0
    _paid_order(client, headers, f1, 1)
    d3 = client.get('/api/admin/dashboard', headers=ah).get_json()['data']
    assert d3['cards']['pending_accept_orders'] == 1
    assert d3['cards']['today_orders'] == 4
    assert d3['cards']['today_amount'] == 34.0     # 28 + 6

    assert len(d['order_trend']) == 7
    assert d['order_trend'][-1]['count'] == 3      # 今日
    assert [x['count'] for x in d['order_trend'][:6]] == [0] * 6

    cats = {c['cat_name']: c['sales'] for c in d['category_sales']}
    assert cats.get('早餐') == 2
    assert cats.get('快餐') == 1

    pie = {p['name']: p['value'] for p in d['status_pie']}
    assert pie == {'待支付': 1, '待接单': 0, '配送中': 1, '已完成': 1, '已取消': 0}

    # 学生 Token 不能看 Dashboard
    assert client.get('/api/admin/dashboard', headers=headers).get_json()['code'] == 401
    # 空库场景
    exec_sql('DELETE FROM order_item')
    exec_sql('DELETE FROM orders')
    d2 = client.get('/api/admin/dashboard', headers=ah).get_json()['data']
    assert d2['cards']['today_orders'] == 0
    assert d2['cards']['today_amount'] == 0.0
    assert all(p['value'] == 0 for p in d2['status_pie'])


# ------------------------------------------------------------------ 补充：分类 / 菜品管理
def test_41_admin_category_crud(client):
    ah = _ah(client)
    add = client.post('/api/admin/category/save',
                      json={'cat_name': '烧烤', 'sort': 6, 'is_show': 1}, headers=ah).get_json()
    assert add['code'] == 200
    cid = add['data']['id']
    # 重名
    assert client.post('/api/admin/category/save',
                       json={'cat_name': '烧烤', 'sort': 7}, headers=ah).get_json()['code'] == 400
    # 编辑
    up = client.post('/api/admin/category/save',
                     json={'id': cid, 'cat_name': '烧烤档', 'sort': 9, 'is_show': 0},
                     headers=ah).get_json()
    assert up['data']['cat_name'] == '烧烤档' and up['data']['is_show'] == 0
    # 非法 is_show
    assert client.post('/api/admin/category/save',
                       json={'id': cid, 'cat_name': 'x', 'is_show': 5},
                       headers=ah).get_json()['code'] == 400
    # 删除空分类
    assert client.post('/api/admin/category/del', json={'id': cid},
                       headers=ah).get_json()['code'] == 200
    # 删除有关联菜品的分类 → 业务错误，且不产生脏数据
    fid = seed_food(1, '早餐菜', '6.00', 10)
    bad = client.post('/api/admin/category/del', json={'id': 1}, headers=ah).get_json()
    assert bad['code'] == 400 and '无法删除' in bad['msg']
    assert fetch_one('SELECT COUNT(*) AS c FROM food WHERE id=%s', (fid,))['c'] == 1
    assert fetch_one('SELECT COUNT(*) AS c FROM food_category WHERE id=1')['c'] == 1


def test_42_admin_food_crud(client):
    ah = _ah(client)
    add = client.post('/api/admin/food/save', json={
        'cat_id': 1, 'food_name': '新菜品', 'price': '13.50', 'stock': '20',
        'description': '好吃', 'is_sale': 1}, headers=ah).get_json()
    assert add['code'] == 200
    fid = add['data']['id']
    assert add['data']['price'] == 13.5

    # 负数价格 / 库存被拒
    assert client.post('/api/admin/food/save', json={
        'cat_id': 1, 'food_name': 'X', 'price': '-1', 'stock': '5'},
        headers=ah).get_json()['code'] == 400
    assert client.post('/api/admin/food/save', json={
        'cat_id': 1, 'food_name': 'X', 'price': '1', 'stock': '-5'},
        headers=ah).get_json()['code'] == 400
    # 不存在的分类
    assert client.post('/api/admin/food/save', json={
        'cat_id': 999, 'food_name': 'X', 'price': '1', 'stock': '5'},
        headers=ah).get_json()['code'] == 400
    # 同分类重名
    assert client.post('/api/admin/food/save', json={
        'cat_id': 1, 'food_name': '新菜品', 'price': '1', 'stock': '5'},
        headers=ah).get_json()['code'] == 400

    # 编辑（含上下架）
    up = client.post('/api/admin/food/save', json={
        'id': fid, 'cat_id': 2, 'food_name': '新菜品改', 'price': '14.00',
        'stock': '3', 'description': '改', 'is_sale': 0}, headers=ah).get_json()
    assert up['data']['food_name'] == '新菜品改'
    assert up['data']['is_sale'] == 0 and up['data']['stock'] == 3
    assert up['data']['cat_id'] == 2

    # 下架后小程序端不可见
    assert fid not in [f['id'] for f in client.get('/api/food/list').get_json()['data']['list']]
    # 管理员列表可见 + 关键字
    adm = client.get('/api/admin/food/list?keyword=新菜品改', headers=ah).get_json()['data']
    assert adm['total'] == 1
    adm_cat = client.get('/api/admin/food/list?cat_id=2', headers=ah).get_json()['data']
    assert fid in [f['id'] for f in adm_cat['list']]

    # 删除
    assert client.post('/api/admin/food/del', json={'id': fid},
                       headers=ah).get_json()['code'] == 200
    assert fetch_one('SELECT COUNT(*) AS c FROM food WHERE id=%s', (fid,))['c'] == 0
    assert client.post('/api/admin/food/del', json={'id': fid},
                       headers=ah).get_json()['code'] == 400


def test_43_admin_user_list_and_pwd(client):
    ah = _ah(client)
    student_headers(client, '13800000311')
    student_headers(client, '13800000312')

    data = client.get('/api/admin/user/list', headers=ah).get_json()['data']
    assert data['total'] == 2
    first = data['list'][0]
    for k in ('nickname', 'phone', 'student_no', 'dormitory', 'created_at'):
        assert k in first
    assert 'password_hash' not in first

    kw = client.get('/api/admin/user/list?keyword=13800000311', headers=ah).get_json()['data']
    assert kw['total'] == 1
    paged = client.get('/api/admin/user/list?page=1&page_size=1', headers=ah).get_json()['data']
    assert len(paged['list']) == 1 and paged['pages'] == 2

    # 管理员改密码：原密码错误 → 400；正确 → 200
    assert client.post('/api/admin/update_pwd',
                       json={'old_password': 'wrong123', 'new_password': 'NewAdmin#2026'},
                       headers=ah).get_json()['code'] == 400
    assert client.post('/api/admin/update_pwd',
                       json={'old_password': ADMIN_PWD, 'new_password': 'NewAdmin#2026'},
                       headers=ah).get_json()['code'] == 200
    assert client.post('/api/admin/login',
                       json={'admin_name': ADMIN_NAME,
                             'password': 'NewAdmin#2026'}).get_json()['code'] == 200
    assert client.post('/api/admin/login',
                       json={'admin_name': ADMIN_NAME, 'password': ADMIN_PWD}).get_json()['code'] == 400
    # admin_name 无修改入口
    assert not any(r.rule.endswith('admin_name') for r in client.application.url_map.iter_rules())
    _ = fetch_all('SELECT id FROM admin_user')
