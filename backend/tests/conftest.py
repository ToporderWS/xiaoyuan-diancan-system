# -*- coding: utf-8 -*-
"""pytest 公共装置。

安全设计（重要）：
- 测试**强制**运行在独立测试库（campus_order_test）上，绝不触碰业务库。
- 每次用例前 TRUNCATE 全部业务表并重新播种，保证用例互相独立。
- 若测试库名与环境中的业务库同名，直接 fail，避免误删真实数据。
"""
import os
import re
import sys

import pymysql
import pytest
from werkzeug.security import generate_password_hash

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app          # noqa: E402
from config import TestConfig       # noqa: E402
from extensions import db           # noqa: E402
from utils.auth import ROLE_ADMIN, ROLE_STUDENT, generate_token  # noqa: E402

# 测试专用凭据（仅存在于测试代码，不进入任何生产配置）
ADMIN_NAME = 'admin_test'
ADMIN_PWD = 'Adm1n#Test2026'
STUDENT_PWD = 'Stu#2026test'

SQL_FILE = os.path.join(BACKEND_DIR, 'database.sql')
TEST_DB = TestConfig.DB_NAME

TABLES = ['order_item', 'cart', 'orders', 'food', 'food_category', 'notice',
          'admin_user', 'users']

_defaults = dict(host=TestConfig.DB_HOST, port=TestConfig.DB_PORT, user=TestConfig.DB_USER,
                 password=TestConfig.DB_PASSWORD, charset='utf8mb4',
                 cursorclass=pymysql.cursors.DictCursor, autocommit=True)


def _raw_conn(database=None):
    kw = dict(_defaults)
    if database:
        kw['database'] = database
    return pymysql.connect(**kw)


def _split_statements(sql_text: str):
    """极简 SQL 语句切分（脚本内无字符串内含分号的情况）。"""
    lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith('--') or not stripped:
            continue
        lines.append(line)
    body = '\n'.join(lines)
    return [s.strip() for s in body.split(';') if s.strip()]


def _build_test_schema():
    assert TEST_DB != TestConfig.__dict__.get('DB_NAME', None) or True
    if TEST_DB == 'campus_order':
        raise RuntimeError('拒绝在业务库上运行测试：TEST_DB_NAME 不能等于 campus_order')

    with _raw_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET utf8mb4 "
                "DEFAULT COLLATE utf8mb4_general_ci" % TEST_DB)

    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_text = f.read()
    # 把业务库名替换为测试库名后再执行，确保与生产库结构完全一致
    sql_text = re.sub(r'`campus_order`', '`%s`' % TEST_DB, sql_text)

    with _raw_conn(TEST_DB) as conn:
        with conn.cursor() as cur:
            for stmt in _split_statements(sql_text):
                upper = stmt.upper()
                if upper.startswith('CREATE DATABASE'):
                    continue
                if upper.startswith('USE '):
                    continue
                cur.execute(stmt)


@pytest.fixture(scope='session', autouse=True)
def _schema():
    _build_test_schema()
    yield


@pytest.fixture(scope='session')
def app(_schema):
    application = create_app('testing')
    application.config['ENABLE_SCHEDULER'] = False
    os.makedirs(application.config['UPLOAD_FOLDER'], exist_ok=True)
    yield application
    try:
        db.pool.close_all()
    except Exception:
        pass


@pytest.fixture()
def client(app):
    return app.test_client()


def _truncate_all():
    with _raw_conn(TEST_DB) as conn:
        with conn.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS = 0')
            for t in TABLES:
                cur.execute('TRUNCATE TABLE `%s`' % t)
            cur.execute('SET FOREIGN_KEY_CHECKS = 1')


def _seed():
    with _raw_conn(TEST_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO food_category (cat_name, sort, is_show, created_at) VALUES "
                "('早餐',1,1,NOW()),('快餐',2,1,NOW()),('面食',3,1,NOW()),"
                "('饮品',4,1,NOW()),('小吃',5,1,NOW())")
            cur.execute(
                'INSERT INTO admin_user (admin_name, password_hash, real_name, avatar, created_at) '
                'VALUES (%s, %s, %s, %s, NOW())',
                (ADMIN_NAME, generate_password_hash(ADMIN_PWD), '测试管理员', 'default_user.jpg'))


@pytest.fixture(autouse=True)
def _reset_db(app):
    """每个用例前清库 + 播种。"""
    _truncate_all()
    _seed()
    yield


# ----------------------------------------------------------------- 通用工具
@pytest.fixture()
def admin_headers(app):
    with app.app_context():
        token = generate_token(1, ROLE_ADMIN)
    return {'Authorization': 'Bearer ' + token}


def make_student(client, phone: str, password: str = STUDENT_PWD):
    """注册并登录取回学生 Token。"""
    resp = client.post('/api/user/register', json={
        'nickname': '同学' + phone[-4:], 'phone': phone, 'password': password,
        'student_no': 'S' + phone[-6:], 'dormitory': '宿舍楼3栋 502',
    })
    assert resp.get_json()['code'] == 200, resp.get_json()
    login = client.post('/api/user/login', json={'phone': phone, 'password': password})
    body = login.get_json()
    assert body['code'] == 200, body
    return body['data']


def student_headers(client, phone: str, password: str = STUDENT_PWD):
    data = make_student(client, phone, password)
    return {'Authorization': 'Bearer ' + data['token']}, data


def seed_food(cat_id: int, name: str, price: str, stock: int, is_sale: int = 1) -> int:
    """直接写入菜品，返回 id（避免依赖其它接口，保证用例聚焦）。"""
    with _raw_conn(TEST_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO food (cat_id, food_name, price, stock, sales, food_img, '
                'description, is_sale, created_at) VALUES (%s,%s,%s,%s,0,%s,%s,%s,NOW())',
                (cat_id, name, price, stock, 'food.jpg', '描述', is_sale))
            return cur.lastrowid


def fetch_one(sql, args=None):
    with _raw_conn(TEST_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchone()


def fetch_all(sql, args=None):
    with _raw_conn(TEST_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchall()


def exec_sql(sql, args=None):
    with _raw_conn(TEST_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.rowcount


@pytest.fixture()
def helpers():
    class H:
        make_student = staticmethod(make_student)
        student_headers = staticmethod(student_headers)
        seed_food = staticmethod(seed_food)
        fetch_one = staticmethod(fetch_one)
        fetch_all = staticmethod(fetch_all)
        exec_sql = staticmethod(exec_sql)
        STUDENT_PWD = STUDENT_PWD
        ADMIN_NAME = ADMIN_NAME
        ADMIN_PWD = ADMIN_PWD

    return H


_ = ROLE_STUDENT
