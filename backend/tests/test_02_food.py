# -*- coding: utf-8 -*-
"""用例 9~11：分类 / 菜品 / 未登录浏览。"""
from conftest import exec_sql, fetch_one, student_headers, seed_food


# ------------------------------------------------------------------ 9 分类
def test_09_category_list(client):
    body = client.get('/api/food/category/list').get_json()
    assert body['code'] == 200
    names = [c['cat_name'] for c in body['data']['list']]
    assert names == ['早餐', '快餐', '面食', '饮品', '小吃']

    # 隐藏分类不出现在小程序端
    exec_sql("UPDATE food_category SET is_show = 0 WHERE cat_name = '小吃'")
    names2 = [c['cat_name'] for c in client.get('/api/food/category/list').get_json()['data']['list']]
    assert '小吃' not in names2
    # 但管理员列表可以拿到
    login = client.post('/api/admin/login',
                        json={'admin_name': 'admin_test', 'password': 'Adm1n#Test2026'}).get_json()
    ah = {'Authorization': 'Bearer ' + login['data']['token']}
    adm = client.get('/api/admin/category/list', headers=ah).get_json()['data']['list']
    assert '小吃' in [c['cat_name'] for c in adm]


# ------------------------------------------------------------------ 10 菜品
def test_10_food_list(client):
    seed_food(1, '红烧牛肉面', '12.00', 56)
    seed_food(1, '香辣鸡腿饭', '15.00', 50)
    seed_food(2, '柠檬茶', '6.00', 0)          # 售罄
    seed_food(2, '下架菜', '9.00', 10, is_sale=0)  # 下架

    body = client.get('/api/food/list').get_json()
    assert body['code'] == 200
    names = [f['food_name'] for f in body['data']['list']]
    assert '下架菜' not in names          # 未上架不返回
    assert body['data']['total'] == 3

    first = [f for f in body['data']['list'] if f['food_name'] == '红烧牛肉面'][0]
    assert first['price'] == 12.0
    assert first['stock'] == 56
    assert 'food_img' in first and 'cat_name' in first
    # 图片字段只保存文件名
    assert '/' not in first['food_img']

    # 按分类过滤
    only1 = client.get('/api/food/list?cat_id=1').get_json()['data']
    assert all(f['cat_id'] == 1 for f in only1['list'])
    # 关键字
    kw = client.get('/api/food/list?keyword=牛肉').get_json()['data']
    assert kw['total'] == 1
    # 分页
    paged = client.get('/api/food/list?page=1&page_size=2').get_json()['data']
    assert len(paged['list']) == 2
    assert paged['pages'] == 2


def test_10b_food_list_hidden_category_excluded(client):
    fid = seed_food(5, '隐藏分类菜', '8.00', 10)
    exec_sql('UPDATE food_category SET is_show = 0 WHERE id = 5')
    body = client.get('/api/food/list').get_json()['data']
    assert fid not in [f['id'] for f in body['list']]


# ------------------------------------------------------------------ 11 未登录浏览
def test_11_guest_can_browse(client):
    seed_food(1, '招牌奶茶', '8.00', 30)
    exec_sql("INSERT INTO notice (title, content, publish_time, is_show) "
             "VALUES ('校园点餐上线','内容',NOW(),1),('隐藏公告','内容',NOW(),0)")
    for path in ('/api/food/category/list', '/api/food/list', '/api/notice/list'):
        assert client.get(path).get_json()['code'] == 200, path
    notices = client.get('/api/notice/list').get_json()['data']['list']
    assert len(notices) == 1
    assert notices[0]['title'] == '校园点餐上线'

    # 浏览接口即使带无效 Token 也不受影响（不做强制鉴权）
    r = client.get('/api/food/list', headers={'Authorization': 'Bearer bad-token'})
    assert r.get_json()['code'] == 200
    # 但购物车必须登录
    assert client.get('/api/cart/list').get_json()['code'] == 401
    assert client.post('/api/cart/save', json={'food_id': 1, 'count': 1}).get_json()['code'] == 401
    assert client.post('/api/order/create',
                       json={'receive_address': '宿舍楼3栋 502'}).get_json()['code'] == 401


def test_11b_admin_order_detail_requires_admin(client):
    assert client.get('/api/admin/order/detail?order_id=1').get_json()['code'] == 401
    headers, _ = student_headers(client, '13800000077')
    assert client.get('/api/admin/order/detail?order_id=1',
                      headers=headers).get_json()['code'] == 401
    assert fetch_one('SELECT COUNT(*) AS c FROM orders')['c'] == 0
