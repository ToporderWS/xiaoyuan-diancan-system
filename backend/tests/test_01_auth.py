# -*- coding: utf-8 -*-
"""用例 1~8：注册 / 登录 / Token / 角色隔离 + 资料与密码安全。"""
import datetime as _dt

import jwt
from conftest import ADMIN_NAME, ADMIN_PWD, STUDENT_PWD, fetch_one, student_headers

PHONE = '13800000001'


def _register_payload(phone=PHONE, password=STUDENT_PWD):
    return {'nickname': '张三', 'phone': phone, 'password': password,
            'student_no': '2023123456', 'dormitory': '宿舍楼3栋 502'}


# ------------------------------------------------------------------ 1 注册
def test_01_register_success(client):
    r = client.post('/api/user/register', json=_register_payload())
    body = r.get_json()
    assert r.status_code == 200
    assert body['code'] == 200
    assert body['data']['phone'] == PHONE
    assert body['data']['avatar'] == 'default_user.jpg'
    # 响应绝不允许出现密码或哈希
    assert 'password' not in body['data']
    assert 'password_hash' not in body['data']

    row = fetch_one('SELECT password_hash, avatar, student_no, dormitory FROM users WHERE phone=%s',
                    (PHONE,))
    assert row is not None
    assert row['password_hash'] != STUDENT_PWD           # 明文绝不入库
    assert row['password_hash'].startswith(('pbkdf2:', 'scrypt:'))  # Werkzeug 哈希
    assert row['student_no'] == '2023123456'


# ------------------------------------------------------------------ 2 重复手机号
def test_02_register_duplicate_phone(client):
    assert client.post('/api/user/register', json=_register_payload()).get_json()['code'] == 200
    body = client.post('/api/user/register', json=_register_payload()).get_json()
    assert body['code'] == 400
    assert '已注册' in body['msg']
    cnt = fetch_one('SELECT COUNT(*) AS c FROM users WHERE phone=%s', (PHONE,))
    assert cnt['c'] == 1


def test_02b_register_invalid_params(client):
    bad = _register_payload()
    bad['phone'] = '123'
    assert client.post('/api/user/register', json=bad).get_json()['code'] == 400
    bad = _register_payload()
    bad['password'] = '123'
    assert client.post('/api/user/register', json=bad).get_json()['code'] == 400
    bad = _register_payload()
    bad.pop('nickname')
    assert client.post('/api/user/register', json=bad).get_json()['code'] == 400


# ------------------------------------------------------------------ 3 正确登录
def test_03_login_success(client):
    client.post('/api/user/register', json=_register_payload())
    body = client.post('/api/user/login', json={'phone': PHONE, 'password': STUDENT_PWD}).get_json()
    assert body['code'] == 200
    d = body['data']
    for k in ('token', 'user_id', 'nickname', 'phone', 'avatar', 'student_no', 'dormitory'):
        assert k in d
    payload = jwt.decode(d['token'], options={'verify_signature': False})
    assert payload['role'] == 0
    assert payload['id'] == d['user_id']
    assert 'exp' in payload
    # 数据库中不存在 role 字段
    col = fetch_one("SHOW COLUMNS FROM users LIKE 'role'")
    assert col is None


# ------------------------------------------------------------------ 4 错误密码
def test_04_login_wrong_password(client):
    client.post('/api/user/register', json=_register_payload())
    body = client.post('/api/user/login',
                       json={'phone': PHONE, 'password': 'WrongPass123'}).get_json()
    assert body['code'] == 400
    assert body['data'] == {}
    # 未注册手机号同样不泄露账号是否存在
    body2 = client.post('/api/user/login',
                        json={'phone': '13900000009', 'password': STUDENT_PWD}).get_json()
    assert body2['code'] == 400
    assert body2['msg'] == body['msg']


# ------------------------------------------------------------------ 5 学生 Token
def test_05_student_token(client):
    headers, data = student_headers(client, PHONE)
    body = client.get('/api/user/info', headers=headers).get_json()
    assert body['code'] == 200
    assert body['data']['phone'] == PHONE
    assert 'password_hash' not in body['data']

    # 修改资料
    up = client.post('/api/user/update_info', json={
        'nickname': '李四', 'student_no': '2023999999', 'dormitory': '宿舍楼9栋 101',
    }, headers=headers).get_json()
    assert up['code'] == 200
    assert up['data']['nickname'] == '李四'

    # 修改密码（旧密码错误 → 400；正确 → 200，并可用新密码登录）
    bad = client.post('/api/user/update_pwd', json={
        'old_password': 'Nope12345', 'new_password': 'NewPass#2026',
    }, headers=headers).get_json()
    assert bad['code'] == 400
    ok = client.post('/api/user/update_pwd', json={
        'old_password': STUDENT_PWD, 'new_password': 'NewPass#2026',
    }, headers=headers).get_json()
    assert ok['code'] == 200
    relogin = client.post('/api/user/login',
                          json={'phone': PHONE, 'password': 'NewPass#2026'}).get_json()
    assert relogin['code'] == 200
    assert relogin['data']['user_id'] == data['user_id']


# ------------------------------------------------------------------ 6 管理员 Token
def test_06_admin_token(client):
    body = client.post('/api/admin/login',
                       json={'admin_name': ADMIN_NAME, 'password': ADMIN_PWD}).get_json()
    assert body['code'] == 200
    token = body['data']['token']
    payload = jwt.decode(token, options={'verify_signature': False})
    assert payload['role'] == 1
    assert 'exp' in payload

    headers = {'Authorization': 'Bearer ' + token}
    info = client.get('/api/admin/info', headers=headers).get_json()
    assert info['code'] == 200
    assert info['data']['admin_name'] == ADMIN_NAME
    assert 'password_hash' not in info['data']

    bad = client.post('/api/admin/login',
                      json={'admin_name': ADMIN_NAME, 'password': 'nope'}).get_json()
    assert bad['code'] == 400


# ------------------------------------------------------------------ 7 Token 串用
def test_07_token_role_mixed(client):
    s_headers, _ = student_headers(client, PHONE)
    a_body = client.post('/api/admin/login',
                         json={'admin_name': ADMIN_NAME, 'password': ADMIN_PWD}).get_json()
    a_headers = {'Authorization': 'Bearer ' + a_body['data']['token']}

    # 学生 Token 访问管理员接口 → 401
    for path in ('/api/admin/info', '/api/admin/dashboard', '/api/admin/user/list',
                 '/api/admin/order/list', '/api/admin/cart/list'):
        r = client.get(path, headers=s_headers).get_json()
        assert r['code'] == 401, path
        assert '学生' in r['msg'] or '无权' in r['msg']

    # 管理员 Token 访问学生接口 → 401
    for path in ('/api/user/info', '/api/cart/list', '/api/order/my_list'):
        r = client.get(path, headers=a_headers).get_json()
        assert r['code'] == 401, path

    # 管理员 Token 也不能当作学生身份下单
    r = client.post('/api/order/create', json={'receive_address': '宿舍楼3栋 502'},
                    headers=a_headers).get_json()
    assert r['code'] == 401


# ------------------------------------------------------------------ 8 Token 无效
def test_08_invalid_token(client, app):
    # 无 Token
    assert client.get('/api/user/info').get_json()['code'] == 401
    assert client.get('/api/cart/list').get_json()['code'] == 401

    # 格式错误
    assert client.get('/api/user/info',
                      headers={'Authorization': 'abc'}).get_json()['code'] == 401
    assert client.get('/api/user/info',
                      headers={'Authorization': 'Basic xyz'}).get_json()['code'] == 401
    # 伪造签名
    fake = jwt.encode({'id': 1, 'role': 0, 'exp': _dt.datetime.utcnow() + _dt.timedelta(hours=1)},
                      'wrong-secret-for-forgery-test-0000000000', algorithm='HS256')
    assert client.get('/api/user/info',
                      headers={'Authorization': 'Bearer ' + fake}).get_json()['code'] == 401
    # 已过期
    expired = jwt.encode({'id': 1, 'role': 0,
                          'exp': _dt.datetime.utcnow() - _dt.timedelta(seconds=10)},
                         app.config['JWT_SECRET'], algorithm='HS256')
    body = client.get('/api/user/info',
                      headers={'Authorization': 'Bearer ' + expired}).get_json()
    assert body['code'] == 401
    assert '过期' in body['msg']


def test_08b_logout_and_public_endpoints(client):
    headers, _ = student_headers(client, PHONE)
    assert client.post('/api/user/logout', headers=headers).get_json()['code'] == 200
    login = client.post('/api/admin/login',
                        json={'admin_name': ADMIN_NAME, 'password': ADMIN_PWD}).get_json()
    ah = {'Authorization': 'Bearer ' + login['data']['token']}
    # V1.0：服务端不做 JWT 黑名单，logout 后原 Token 在有效期内仍可用（README 已说明）
    assert client.get('/api/admin/info', headers=ah).get_json()['code'] == 200
    assert client.post('/api/admin/logout', headers=ah).get_json()['code'] == 200
    # 非业务辅助接口
    assert client.get('/').get_json()['code'] == 200
    assert client.get('/api/health').get_json()['data']['status'] == 'UP'
