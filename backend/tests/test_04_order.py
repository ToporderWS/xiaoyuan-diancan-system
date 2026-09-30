# -*- coding: utf-8 -*-
"""用例 17~31：订单创建 / 价格与库存 / 并发 / 模拟支付 / 取消 / 超时 / 越权 / 状态机。"""
import threading
from decimal import Decimal

from conftest import exec_sql, fetch_all, fetch_one, seed_food, student_headers

ADDR = '宿舍楼3栋 502'
P1 = '13800000201'
P2 = '13800000202'


def _order(client, headers, addr=ADDR, remark=''):
    return client.post('/api/order/create',
                       json={'receive_address': addr, 'remark': remark},
                       headers=headers).get_json()


def _pay(client, headers, oid):
    return client.post('/api/order/pay', json={'order_id': oid}, headers=headers).get_json()


def _cancel(client, headers, oid):
    return client.post('/api/order/cancel', json={'order_id': oid}, headers=headers).get_json()


def _admin_headers(client):
    body = client.post('/api/admin/login',
                       json={'admin_name': 'admin_test', 'password': 'Adm1n#Test2026'}).get_json()
    return {'Authorization': 'Bearer ' + body['data']['token']}


def _admin(client, headers, action, oid):
    return client.post('/api/admin/order/%s' % action, json={'order_id': oid},
                       headers=headers).get_json()


# ------------------------------------------------------------------ 17 空购物车
def test_17_order_empty_cart(client):
    headers, _ = student_headers(client, P1)
    body = _order(client, headers)
    assert body['code'] == 400
    assert '购物车为空' in body['msg']
    assert fetch_one('SELECT COUNT(*) AS c FROM orders')['c'] == 0
    # 地址必填
    seed_food(1, '面', '10.00', 10)
    assert client.post('/api/order/create', json={'receive_address': ''},
                       headers=headers).get_json()['code'] == 400
    assert client.post('/api/order/create', json={'receive_address': 'x' * 200},
                       headers=headers).get_json()['code'] == 400


# ------------------------------------------------------------------ 18 正常下单
def test_18_order_create_success(client):
    f1 = seed_food(1, '红烧牛肉面', '12.00', 56)
    f2 = seed_food(2, '香辣鸡腿饭', '15.50', 30)
    headers, data = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': f1, 'count': 2}, headers=headers)
    client.post('/api/cart/save', json={'food_id': f2, 'count': 1}, headers=headers)

    body = _order(client, headers, ADDR, '不要香菜')
    assert body['code'] == 200
    o = body['data']
    # CO + %Y%m%d%H%M%S(14) + 4位随机 + 3位序号 = 23 位
    assert o['order_no'].startswith('CO') and len(o['order_no']) == 23
    assert o['order_no'][2:16].isdigit()
    assert o['order_status'] == 0
    assert o['status_text'] == '待支付'
    assert o['total_price'] == 39.5            # 12*2 + 15.5
    assert o['receive_address'] == ADDR
    assert o['remark'] == '不要香菜'
    assert o['pay_time'] is None and o['finish_time'] is None
    assert len(o['items']) == 2
    names = sorted(i['food_name'] for i in o['items'])
    assert names == ['红烧牛肉面', '香辣鸡腿饭']
    # 明细为快照
    item = [i for i in o['items'] if i['food_name'] == '红烧牛肉面'][0]
    assert item['food_price'] == 12.0 and item['count'] == 2 and item['subtotal'] == 24.0
    # 购物车已清空
    assert client.get('/api/cart/list', headers=headers).get_json()['data']['list'] == []
    # 订单归属正确
    assert fetch_one('SELECT user_id FROM orders WHERE id=%s', (o['id'],))['user_id'] == data['user_id']


# ------------------------------------------------------------------ 19 后端价格计算
def test_19_order_price_from_backend(client):
    fid = seed_food(1, '真价菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 2}, headers=headers)

    # 恶意注入：前端试图指定价格、用户、状态、订单号、总价
    body = client.post('/api/order/create', json={
        'receive_address': ADDR, 'remark': '',
        'total_price': 0.01, 'price': 0.01, 'order_status': 3,
        'user_id': 999999, 'order_no': 'HACK', 'items': [{'food_id': fid, 'food_price': '0.01'}],
    }, headers=headers).get_json()
    assert body['code'] == 200
    o = body['data']
    assert o['total_price'] == 24.0
    assert o['order_status'] == 0
    assert o['order_no'] != 'HACK'
    assert o['items'][0]['food_price'] == 12.0
    row = fetch_one('SELECT total_price, user_id FROM orders WHERE id=%s', (o['id'],))
    assert str(row['total_price']) == '24.00'
    assert row['user_id'] != 999999

    # 金额全部以 Decimal 存储
    assert isinstance(row['total_price'], Decimal)


# ------------------------------------------------------------------ 20 扣库存
def test_20_order_deduct_stock(client):
    f1 = seed_food(1, '扣库存菜', '10.00', 10)
    f2 = seed_food(1, '另一菜', '5.00', 4)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': f1, 'count': 3}, headers=headers)
    client.post('/api/cart/save', json={'food_id': f2, 'count': 4}, headers=headers)
    assert _order(client, headers)['code'] == 200
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f1,))['stock'] == 7
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f2,))['stock'] == 0
    # 销量此时不应增加（只有完成订单才加）
    assert fetch_one('SELECT sales FROM food WHERE id=%s', (f1,))['sales'] == 0

    # 库存被抢光后，另一学生无法下单
    h2, _ = student_headers(client, P2)
    assert client.post('/api/cart/save', json={'food_id': f2, 'count': 1},
                       headers=h2).get_json()['code'] == 400


# ------------------------------------------------------------------ 21 并发库存（强制项）
def test_21_concurrent_stock_no_oversell(app, client):
    fid = seed_food(1, '最后一份', '10.00', 1)
    h1, d1 = student_headers(client, P1)
    h2, d2 = student_headers(client, P2)
    assert client.post('/api/cart/save', json={'food_id': fid, 'count': 1},
                       headers=h1).get_json()['code'] == 200
    assert client.post('/api/cart/save', json={'food_id': fid, 'count': 1},
                       headers=h2).get_json()['code'] == 200

    barrier = threading.Barrier(2)
    results = {}
    errors = []

    def worker(name, headers):
        cli = app.test_client()
        try:
            barrier.wait(timeout=10)
            resp = cli.post('/api/order/create', json={'receive_address': ADDR},
                            headers=headers)
            results[name] = resp.get_json()
        except Exception as exc:      # pragma: no cover
            errors.append('%s: %s' % (name, exc))

    t1 = threading.Thread(target=worker, args=('A', h1))
    t2 = threading.Thread(target=worker, args=('B', h2))
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)

    assert not errors, errors
    assert len(results) == 2, results
    codes = sorted(r['code'] for r in results.values())
    assert codes == [200, 400], results
    failed = [r for r in results.values() if r['code'] == 400][0]
    assert '库存不足' in failed['msg'] or '下单失败' in failed['msg']

    stock = fetch_one('SELECT stock FROM food WHERE id=%s', (fid,))['stock']
    assert stock == 0, '库存不得出现负数或超卖'
    assert stock >= 0
    assert fetch_one('SELECT COUNT(*) AS c FROM orders')['c'] == 1
    assert fetch_one('SELECT COUNT(*) AS c FROM order_item')['c'] == 1


# ------------------------------------------------------------------ 22 模拟支付
def test_22_pay_success(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    oid = _order(client, headers)['data']['id']

    body = _pay(client, headers, oid)
    assert body['code'] == 200
    assert body['data']['order_status'] == 1
    assert body['data']['status_text'] == '待接单'
    assert body['data']['pay_time'] is not None
    row = fetch_one('SELECT order_status, pay_time FROM orders WHERE id=%s', (oid,))
    assert row['order_status'] == 1 and row['pay_time'] is not None


# ------------------------------------------------------------------ 23 重复支付
def test_23_pay_twice(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    oid = _order(client, headers)['data']['id']
    assert _pay(client, headers, oid)['code'] == 200
    again = _pay(client, headers, oid)
    assert again['code'] == 400
    assert '重复支付' in again['msg']
    assert fetch_one('SELECT order_status FROM orders WHERE id=%s', (oid,))['order_status'] == 1


# ------------------------------------------------------------------ 24 取消待支付
def test_24_cancel_pending_pay(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 2}, headers=headers)
    oid = _order(client, headers)['data']['id']
    body = _cancel(client, headers, oid)
    assert body['code'] == 200
    assert body['data']['order_status'] == 4
    assert body['data']['status_text'] == '已取消'
    # 取消后不能支付
    assert _pay(client, headers, oid)['code'] == 400


# ------------------------------------------------------------------ 25 取消待接单
def test_25_cancel_pending_accept(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    oid = _order(client, headers)['data']['id']
    _pay(client, headers, oid)
    body = _cancel(client, headers, oid)
    assert body['code'] == 200
    assert body['data']['order_status'] == 4


# ------------------------------------------------------------------ 26 重复取消
def test_26_cancel_twice(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    oid = _order(client, headers)['data']['id']
    assert _cancel(client, headers, oid)['code'] == 200
    again = _cancel(client, headers, oid)
    assert again['code'] == 400
    assert '重复取消' in again['msg'] or '不允许取消' in again['msg']
    # 库存只恢复一次
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (fid,))['stock'] == 10


# ------------------------------------------------------------------ 27 配送中禁止取消
def test_27_cancel_delivering_forbidden(client):
    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    ah = _admin_headers(client)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    oid = _order(client, headers)['data']['id']
    _pay(client, headers, oid)
    assert _admin(client, ah, 'receive', oid)['code'] == 200

    body = _cancel(client, headers, oid)
    assert body['code'] == 400
    assert '不允许取消' in body['msg']
    assert fetch_one('SELECT order_status FROM orders WHERE id=%s', (oid,))['order_status'] == 2

    # 完成后也不能取消
    assert _admin(client, ah, 'finish', oid)['code'] == 200
    assert _cancel(client, headers, oid)['code'] == 400


# ------------------------------------------------------------------ 28 取消恢复库存
def test_28_cancel_restore_stock(client):
    f1 = seed_food(1, '菜A', '12.00', 10)
    f2 = seed_food(1, '菜B', '8.00', 5)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': f1, 'count': 3}, headers=headers)
    client.post('/api/cart/save', json={'food_id': f2, 'count': 5}, headers=headers)
    oid = _order(client, headers)['data']['id']
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f1,))['stock'] == 7
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f2,))['stock'] == 0

    assert _cancel(client, headers, oid)['code'] == 200
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f1,))['stock'] == 10
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f2,))['stock'] == 5
    # 订单明细保留为历史快照
    assert len(fetch_all('SELECT * FROM order_item WHERE order_id=%s', (oid,))) == 2


# ------------------------------------------------------------------ 29 超时取消
def test_29_auto_cancel_timeout(client, app):
    from services.order_service import auto_cancel_expired_orders

    fid = seed_food(1, '菜', '12.00', 10)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 2}, headers=headers)
    oid = _order(client, headers)['data']['id']
    # 另一笔刚下单的订单不应被取消
    h2, _ = student_headers(client, P2)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=h2)
    fresh = _order(client, h2)['data']['id']

    # 已支付订单即使超时也不应被取消
    h3, _ = student_headers(client, '13800000203')
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=h3)
    paid = _order(client, h3)['data']['id']
    _pay(client, h3, paid)

    # 把待支付订单的创建时间拨回 20 分钟前
    exec_sql('UPDATE orders SET created_at = DATE_SUB(NOW(), INTERVAL 20 MINUTE) '
             'WHERE id IN (%s, %s)', (oid, paid))

    with app.app_context():
        canceled = auto_cancel_expired_orders()

    assert canceled == 1
    assert fetch_one('SELECT order_status FROM orders WHERE id=%s', (oid,))['order_status'] == 4
    assert fetch_one('SELECT order_status FROM orders WHERE id=%s',
                     (fresh,))['order_status'] == 0
    assert fetch_one('SELECT order_status FROM orders WHERE id=%s',
                     (paid,))['order_status'] == 1

    # 幂等：再次扫描不会重复处理
    with app.app_context():
        assert auto_cancel_expired_orders() == 0

    # 已超时取消的订单无法支付
    assert _pay(client, headers, oid)['code'] == 400


# ------------------------------------------------------------------ 30 超时恢复库存
def test_30_auto_cancel_restore_stock(client, app):
    from services.order_service import auto_cancel_expired_orders

    f1 = seed_food(1, '菜A', '12.00', 6)
    f2 = seed_food(1, '菜B', '7.00', 4)
    headers, _ = student_headers(client, P1)
    client.post('/api/cart/save', json={'food_id': f1, 'count': 4}, headers=headers)
    client.post('/api/cart/save', json={'food_id': f2, 'count': 3}, headers=headers)
    oid = _order(client, headers)['data']['id']
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f1,))['stock'] == 2

    exec_sql('UPDATE orders SET created_at = DATE_SUB(NOW(), INTERVAL 16 MINUTE) WHERE id=%s',
             (oid,))
    with app.app_context():
        assert auto_cancel_expired_orders() == 1

    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f1,))['stock'] == 6
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f2,))['stock'] == 4
    # 再次扫描不会把库存加成两次
    with app.app_context():
        auto_cancel_expired_orders()
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f1,))['stock'] == 6
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (f2,))['stock'] == 4


# ------------------------------------------------------------------ 31 越权订单
def test_31_order_idor(client):
    fid = seed_food(1, '菜', '12.00', 10)
    h1, d1 = student_headers(client, P1)
    h2, d2 = student_headers(client, P2)
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=h1)
    oid = _order(client, h1)['data']['id']

    assert client.get('/api/order/detail?order_id=%d' % oid,
                      headers=h2).get_json()['code'] == 400
    assert _cancel(client, h2, oid)['code'] == 400
    assert _pay(client, h2, oid)['code'] == 400
    # A 自己的订单正常可见
    assert client.get('/api/order/detail?order_id=%d' % oid,
                      headers=h1).get_json()['code'] == 200
    assert fetch_one('SELECT order_status FROM orders WHERE id=%s', (oid,))['order_status'] == 0
    assert fetch_one('SELECT stock FROM food WHERE id=%s', (fid,))['stock'] == 9

    # 我的订单列表只含自己的
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=h2)
    _order(client, h2)
    assert client.get('/api/order/my_list', headers=h2).get_json()['data']['total'] == 1
    assert client.get('/api/order/my_list', headers=h1).get_json()['data']['total'] == 1


# ------------------------------------------------------------------ 状态机非法迁移
def test_31b_illegal_state_transitions(client):
    fid = seed_food(1, '菜', '12.00', 20)
    headers, _ = student_headers(client, P1)
    ah = _admin_headers(client)

    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    oid = _order(client, headers)['data']['id']

    # 0 → 2 / 0 → 3 非法
    assert _admin(client, ah, 'receive', oid)['code'] == 400   # 未支付不能接单
    assert _admin(client, ah, 'finish', oid)['code'] == 400    # 未接单不能完成
    # 1 → 3 非法
    _pay(client, headers, oid)
    assert _admin(client, ah, 'finish', oid)['code'] == 400
    # 1 → 2 合法
    assert _admin(client, ah, 'receive', oid)['code'] == 200
    # 2 → 4 非法（管理员无取消入口，学生取消被拒）
    assert _cancel(client, headers, oid)['code'] == 400
    # 2 → 3 合法
    assert _admin(client, ah, 'finish', oid)['code'] == 200
    # 3 → 4 / 3 → 2 非法
    assert _cancel(client, headers, oid)['code'] == 400
    assert _admin(client, ah, 'receive', oid)['code'] == 400

    # 已取消订单不可再迁移
    client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
    oid2 = _order(client, headers)['data']['id']
    assert _cancel(client, headers, oid2)['code'] == 200
    assert _pay(client, headers, oid2)['code'] == 400
    assert _admin(client, ah, 'receive', oid2)['code'] == 400
    assert _admin(client, ah, 'finish', oid2)['code'] == 400


def test_31c_order_list_filter_and_paging(client):
    fid = seed_food(1, '菜', '12.00', 20)
    headers, _ = student_headers(client, P1)
    ah = _admin_headers(client)
    ids = []
    for _i in range(3):
        client.post('/api/cart/save', json={'food_id': fid, 'count': 1}, headers=headers)
        ids.append(_order(client, headers)['data']['id'])
    _pay(client, headers, ids[0])

    data = client.get('/api/order/my_list?order_status=0', headers=headers).get_json()['data']
    assert data['total'] == 2
    data_paid = client.get('/api/order/my_list?order_status=1', headers=headers).get_json()['data']
    assert data_paid['total'] == 1
    paged = client.get('/api/order/my_list?page=1&page_size=2', headers=headers).get_json()['data']
    assert len(paged['list']) == 2 and paged['pages'] == 2
    assert set(paged['status_text_map'].keys()) == {'0', '1', '2', '3', '4'}

    adm = client.get('/api/admin/order/list', headers=ah).get_json()['data']
    assert adm['total'] == 3
    adm2 = client.get('/api/admin/order/list?order_status=1&keyword=' + data_paid['list'][0]['order_no'][:8],
                      headers=ah).get_json()['data']
    assert adm2['total'] == 1
    detail = client.get('/api/admin/order/detail?order_id=%d' % ids[0], headers=ah).get_json()
    assert detail['code'] == 200
    me = client.get('/api/user/info', headers=headers).get_json()['data']
    assert detail['data']['nickname'] == me['nickname']
    assert detail['data']['phone'] == me['phone']
    # 学生端订单列表不返回他人信息字段
    assert 'nickname' not in data_paid['list'][0]
