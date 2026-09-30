# -*- coding: utf-8 -*-
"""用例 12~16：购物车（实时读写 MySQL、库存上限、越权隔离）。"""
from conftest import exec_sql, fetch_all, fetch_one, seed_food, student_headers

P1 = '13800000101'
P2 = '13800000102'


# ------------------------------------------------------------------ 12 正常加购
def test_12_cart_add_normal(client):
    fid = seed_food(1, '红烧牛肉面', '12.00', 56)
    headers, data = student_headers(client, P1)

    body = client.post('/api/cart/save', json={'food_id': fid, 'count': 2},
                       headers=headers).get_json()
    assert body['code'] == 200
    assert body['data']['count'] == 2
    assert body['data']['subtotal'] == 24.0

    # 数据真实写入 MySQL
    row = fetch_one('SELECT * FROM cart WHERE user_id=%s AND food_id=%s', (data['user_id'], fid))
    assert row['count'] == 2

    # 再次加购为累加
    again = client.post('/api/cart/save', json={'food_id': fid, 'count': 1},
                        headers=headers).get_json()
    assert again['data']['count'] == 3

    lst = client.get('/api/cart/list', headers=headers).get_json()['data']
    assert lst['total_count'] == 3
    assert lst['total_amount'] == 36.0
    assert lst['list'][0]['food_name'] == '红烧牛肉面'
    assert lst['list'][0]['valid'] is True


# ------------------------------------------------------------------ 13 超库存加购
def test_13_cart_add_over_stock(client):
    fid = seed_food(1, '限量套餐', '20.00', 2)
    headers, data = student_headers(client, P1)

    assert client.post('/api/cart/save', json={'food_id': fid, 'count': 2},
                       headers=headers).get_json()['code'] == 200
    over = client.post('/api/cart/save', json={'food_id': fid, 'count': 1},
                       headers=headers).get_json()
    assert over['code'] == 400
    assert '库存不足' in over['msg']
    assert fetch_one('SELECT `count` AS c FROM cart WHERE user_id=%s AND food_id=%s',
                     (data['user_id'], fid))['c'] == 2

    # 单次超量同样拦截
    fid2 = seed_food(1, '限量小食', '5.00', 3)
    assert client.post('/api/cart/save', json={'food_id': fid2, 'count': 4},
                       headers=headers).get_json()['code'] == 400

    # 售罄 / 下架 / 不存在
    sold_out = seed_food(1, '售罄菜', '5.00', 0)
    assert client.post('/api/cart/save', json={'food_id': sold_out, 'count': 1},
                       headers=headers).get_json()['code'] == 400
    off = seed_food(1, '下架菜', '5.00', 10, is_sale=0)
    assert client.post('/api/cart/save', json={'food_id': off, 'count': 1},
                       headers=headers).get_json()['code'] == 400
    assert client.post('/api/cart/save', json={'food_id': 999999, 'count': 1},
                       headers=headers).get_json()['code'] == 400
    # 非法数量
    assert client.post('/api/cart/save', json={'food_id': fid, 'count': 0},
                       headers=headers).get_json()['code'] == 400
    assert client.post('/api/cart/save', json={'food_id': fid, 'count': -3},
                       headers=headers).get_json()['code'] == 400
    assert client.post('/api/cart/save', json={'food_id': fid, 'count': 'abc'},
                       headers=headers).get_json()['code'] == 400


# ------------------------------------------------------------------ 14 修改购物车
def test_14_cart_modify(client):
    fid = seed_food(1, '香辣鸡腿饭', '15.00', 50)
    headers, data = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 4}, headers=headers)
    cart_id = fetch_one('SELECT id FROM cart WHERE user_id=%s AND food_id=%s',
                        (data['user_id'], fid))['id']

    # 增量 +1
    up = client.post('/api/cart/save', json={'food_id': fid, 'count': 1},
                     headers=headers).get_json()
    assert up['data']['count'] == 5

    # 契约内减少数量：先删除再按新数量保存（前端「-」按钮的实现方式）
    client.post('/api/cart/del', json={'cart_id': cart_id}, headers=headers)
    dec = client.post('/api/cart/save', json={'food_id': fid, 'count': 3},
                      headers=headers).get_json()
    assert dec['data']['count'] == 3
    assert fetch_one('SELECT COUNT(*) AS c FROM cart WHERE user_id=%s', (data['user_id'],))['c'] == 1


# ------------------------------------------------------------------ 15 删除购物车
def test_15_cart_delete(client):
    fid = seed_food(1, '面', '10.00', 10)
    headers, data = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    cart_id = fetch_one('SELECT id FROM cart WHERE user_id=%s', (data['user_id'],))['id']

    assert client.post('/api/cart/del', json={'cart_id': cart_id},
                       headers=headers).get_json()['code'] == 200
    assert len(fetch_all('SELECT * FROM cart WHERE user_id=%s', (data['user_id'],))) == 0
    # 重复删除 → 业务错误
    assert client.post('/api/cart/del', json={'cart_id': cart_id},
                       headers=headers).get_json()['code'] == 400
    assert client.post('/api/cart/del', json={'cart_id': 'x'},
                       headers=headers).get_json()['code'] == 400


# ------------------------------------------------------------------ 16 越权购物车
def test_16_cart_idor(client):
    fid = seed_food(1, '牛肉面', '12.00', 20)
    h1, d1 = student_headers(client, P1)
    h2, d2 = student_headers(client, P2)

    client.post('/api/cart/save', json={'food_id': fid, 'count': 2}, headers=h1)
    cart1 = fetch_one('SELECT id FROM cart WHERE user_id=%s', (d1['user_id'],))['id']

    # B 看不到 A 的购物车
    assert client.get('/api/cart/list', headers=h2).get_json()['data']['list'] == []
    # B 删不掉 A 的购物车
    assert client.post('/api/cart/del', json={'cart_id': cart1},
                       headers=h2).get_json()['code'] == 400
    assert fetch_one('SELECT COUNT(*) AS c FROM cart WHERE id=%s', (cart1,))['c'] == 1

    # 管理员只读查看：能看到全部，且不存在修改入口
    login = client.post('/api/admin/login',
                        json={'admin_name': 'admin_test', 'password': 'Adm1n#Test2026'}).get_json()
    ah = {'Authorization': 'Bearer ' + login['data']['token']}
    admin_list = client.get('/api/admin/cart/list', headers=ah).get_json()['data']
    assert admin_list['total'] == 1
    assert admin_list['list'][0]['nickname'] == d1['nickname']
    # 用管理员 Token 去改学生购物车必须失败（角色不匹配）
    assert client.post('/api/cart/del', json={'cart_id': cart1},
                       headers=ah).get_json()['code'] == 401


def test_16b_cart_invalid_after_offshelf(client):
    """菜品下架/库存被扣后，购物车条目标记为无效但不影响读取。"""
    fid = seed_food(1, '鸡腿饭', '15.00', 10)
    headers, data = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 3}, headers=headers)
    exec_sql('UPDATE food SET stock = 1 WHERE id = %s', (fid,))
    item = client.get('/api/cart/list', headers=headers).get_json()['data']['list'][0]
    assert item['valid'] is False
    assert '库存不足' in item['invalid_reason']

    exec_sql('UPDATE food SET stock = 10, is_sale = 0 WHERE id = %s', (fid,))
    item = client.get('/api/cart/list', headers=headers).get_json()['data']['list'][0]
    assert item['valid'] is False
    assert item['invalid_reason'] == '菜品已下架'
