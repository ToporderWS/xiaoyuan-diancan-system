# -*- coding: utf-8 -*-
"""静态图片访问链路回归测试（/static/upload/<filename>）。

对应本轮真机缺陷：
    图片文件不存在时，后端返回的是 HTTP 200 + {"code":400,"msg":"接口不存在"}。
    浏览器与小程序 <image> 会把 JSON 当图片解码 → 破图；
    且「文件不存在」被伪装成「接口不存在」，掩盖真实原因。

覆盖项：
    1. 正常 JPG    → HTTP 200 + image/jpeg
    2. 正常 PNG    → HTTP 200 + image/png
    3. 文件不存在  → 真实 HTTP 404（不是 200 + 业务 JSON）
    4. 路径穿越    → 拒绝，且绝不返回上传目录之外的文件内容
    5. 新上传图片保存后立即可以 GET
    6. 图片文件名仍只保存「纯文件名」（与数据库约定一致）
    7. 响应头：强缓存 + 允许跨源读取
    8. 静态资源只读，不接受写方法

测试隔离：
    TestConfig.UPLOAD_FOLDER = backend/static/upload_test，
    本文件所有写操作都落在该目录，绝不触碰真实业务图片（static/upload）。
"""
import os
import re
import time
from io import BytesIO

import pytest

STATIC_PREFIX = '/static/upload/'

# 满足 utils.uploader 的 magic bytes 校验的最小合法文件
JPEG_BYTES = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01' + b'\x00' * 256 + b'\xff\xd9'
PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 256


def _upload_avatar(app, client, headers, filename, payload):
    """通过真实上传接口落盘，返回后端保存的**纯文件名**。"""
    resp = client.post('/api/admin/upload_avatar',
                       data={'avatar': (BytesIO(payload), filename)},
                       headers=headers,
                       content_type='multipart/form-data')
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body['code'] == 200, body
    return body['data']['avatar']


@pytest.fixture(autouse=True)
def _clean_upload_dir(app):
    """记录上传目录初始状态，用例结束后删除本次新增文件，保持测试环境卫生。"""
    folder = app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    before = set(os.listdir(folder))
    yield
    # Windows 上 send_file 的响应对象可能仍持有文件句柄，删除会短暂失败，故重试
    for name in set(os.listdir(folder)) - before:
        path = os.path.join(folder, name)
        for _ in range(6):
            try:
                os.remove(path)
                break
            except OSError:
                time.sleep(0.1)


# ------------------------------------------------------------------ 1 / 2
def test_jpg_returns_200_and_jpeg_mime(app, client, admin_headers):
    name = _upload_avatar(app, client, admin_headers, 'dish.jpg', JPEG_BYTES)
    resp = client.get(STATIC_PREFIX + name)
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('image/jpeg')
    assert resp.data == JPEG_BYTES, '返回内容必须与磁盘文件逐字节一致'


def test_png_returns_200_and_png_mime(app, client, admin_headers):
    name = _upload_avatar(app, client, admin_headers, 'dish.png', PNG_BYTES)
    resp = client.get(STATIC_PREFIX + name)
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('image/png')
    assert resp.data == PNG_BYTES


def test_existing_plain_filename_also_served(app, client):
    """直接放在上传目录里的文件（如兜底图）同样应可访问。"""
    folder = app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    probe = '_probe_static_check.png'
    with open(os.path.join(folder, probe), 'wb') as f:
        f.write(PNG_BYTES)
    try:
        resp = client.get(STATIC_PREFIX + probe)
        assert resp.status_code == 200
        assert resp.headers['Content-Type'].startswith('image/png')
    finally:
        try:
            os.remove(os.path.join(folder, probe))
        except OSError:
            pass


# ------------------------------------------------------------------ 3
def test_missing_file_returns_real_404(client):
    resp = client.get(STATIC_PREFIX + 'definitely-not-exists-20260929.jpg')
    assert resp.status_code == 404, (
        '静态资源文件不存在必须返回真实 HTTP 404，而不是 HTTP 200 + 业务 JSON')


def test_missing_file_body_is_not_business_json(client):
    resp = client.get(STATIC_PREFIX + 'definitely-not-exists-20260929.jpg')
    text = resp.get_data(as_text=True)
    assert '接口不存在' not in text
    assert '"code"' not in text, '不得再返回业务 JSON 错误体'


def test_api_404_still_returns_business_json(client):
    """/api/* 的错误 JSON 化行为必须保持不变（不因本次修复而回归）。"""
    resp = client.get('/api/no-such-endpoint-20260929')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['code'] == 400 and body['msg'] == '接口不存在'


# ------------------------------------------------------------------ 4
@pytest.mark.parametrize('evil', [
    '../config.py',
    '../../config.py',
    '..%2fconfig.py',
    '....//config.py',
    '..\\config.py',
    '%2e%2e/config.py',
])
def test_path_traversal_rejected(client, evil):
    resp = client.get(STATIC_PREFIX + evil)
    assert resp.status_code != 200, '路径穿越不得成功返回内容'
    text = resp.get_data(as_text=True)
    assert 'SECRET_KEY' not in text
    assert 'DB_PASSWORD' not in text
    assert 'JWT_SECRET' not in text


# ------------------------------------------------------------------ 5 / 6
def test_upload_then_immediately_available(app, client, admin_headers):
    """新上传图片落盘后立即可以 GET（对应真机新增菜品的真实场景）。"""
    name = _upload_avatar(app, client, admin_headers, 'brand-new-dish.jpg', JPEG_BYTES)
    assert os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], name))
    resp = client.get(STATIC_PREFIX + name)
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('image/jpeg')
    assert resp.data == JPEG_BYTES


def test_filename_is_bare_uuid(app, client, admin_headers):
    """数据库只保存纯文件名 —— 不含任何路径分隔符，固定为 uuid4.hex + 扩展名。"""
    name = _upload_avatar(app, client, admin_headers, '名称 带空格与中文.png', PNG_BYTES)
    assert '/' not in name and '\\' not in name
    assert re.fullmatch(r'[0-9a-f]{32}\.(png|jpg|jpeg|webp)', name), name


# ------------------------------------------------------------------ 7 / 8
def test_cache_and_cors_headers(app, client, admin_headers):
    name = _upload_avatar(app, client, admin_headers, 'hdr.jpg', JPEG_BYTES)
    resp = client.get(STATIC_PREFIX + name)
    assert 'max-age' in (resp.headers.get('Cache-Control') or '')
    assert resp.headers.get('Access-Control-Allow-Origin') == '*'
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'


def test_static_resource_is_read_only(client):
    """静态资源不提供写入能力。"""
    resp = client.post(STATIC_PREFIX + 'anything.jpg', data=b'x')
    assert resp.status_code in (404, 405)
