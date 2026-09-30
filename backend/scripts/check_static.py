# -*- coding: utf-8 -*-
"""静态图片链路体检（真实业务库 + 真实运行中的 Flask 服务）。

为什么单独写这个脚本
------------------
之前用「本机文件存在」和「自建预览服务器返回 200」宣布过 PASS，
但那都没有打到**真实运行中的 Flask**，导致了误判。本脚本强制：

    A. 直接读真实业务库（campus_order）的图片文件名；
    B. 逐个对**真实 LAN 地址**发 HTTP GET（默认取 config.PUBLIC_STATIC_BASE）；
    C. 校验 HTTP 状态码 + Content-Type + 真实图片文件头 + 字节数与磁盘一致；
    D. 明确区分「磁盘缺文件」与「服务未暴露」，不伪造 PASS。

用法：
    python scripts/check_static.py
    python scripts/check_static.py --base http://192.168.0.103:5000/static/upload/
"""
import argparse
import os
import sys
import urllib.error
import urllib.request

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pymysql  # noqa: E402

from config import Config  # noqa: E402

MAGIC = (
    (b'\xff\xd8\xff', 'jpeg'),
    (b'\x89PNG\r\n\x1a\n', 'png'),
    (b'RIFF', 'webp'),
)

_passed = 0
_failed = 0
_notes = []


def ok(msg):
    global _passed
    _passed += 1
    print('  [OK]   %s' % msg)


def bad(msg):
    global _failed
    _failed += 1
    print('  [FAIL] %s' % msg)


def note(msg):
    _notes.append(msg)
    print('  [NOTE] %s' % msg)


def sniff(data: bytes):
    for magic, name in MAGIC:
        if data.startswith(magic):
            return name
    return None


def http_get(url, timeout=8):
    """返回 (status, content_type, body 前 64 字节, 实际长度)。HTTPError 也正常返回。"""
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        body = r.read()
        return r.status, r.headers.get('Content-Type', ''), body[:64], len(body)
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read()[:64], -1
    except Exception as e:
        return 'ERR:%s' % type(e).__name__, str(e)[:60], b'', -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=Config.PUBLIC_STATIC_BASE,
                    help='静态资源基础地址（默认取 config.PUBLIC_STATIC_BASE）')
    args = ap.parse_args()
    base = args.base if args.base.endswith('/') else args.base + '/'

    upload_dir = Config.UPLOAD_FOLDER

    print('=' * 96)
    print('静态图片链路体检')
    print('  数据库   : %s@%s:%d/%s' % (Config.DB_USER, Config.DB_HOST, Config.DB_PORT, Config.DB_NAME))
    print('  上传目录 : %s' % upload_dir)
    print('  静态基址 : %s' % base)
    print('=' * 96)

    cn = pymysql.connect(host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER,
                         password=Config.DB_PASSWORD, database=Config.DB_NAME,
                         charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    cur = cn.cursor()

    # ---------------------------------------------------------- 菜品图片
    cur.execute('SELECT id, food_name, food_img, is_sale FROM food ORDER BY id')
    foods = cur.fetchall()
    print()
    print('一、菜品图片（共 %d 道，逐个真实 HTTP GET）' % len(foods))
    print('-' * 96)
    dish_ok = 0
    for f in foods:
        fn = f['food_img']
        url = base + fn
        disk = os.path.join(upload_dir, fn)
        disk_ok = os.path.isfile(disk)
        disk_size = os.path.getsize(disk) if disk_ok else 0
        status, ctype, head, length = http_get(url)
        kind = sniff(head)

        if status == 200 and kind and length == disk_size and disk_size > 0:
            dish_ok += 1
            print('  [OK]   id=%-3s %-14s %s -> 200 %s %s (%d B=磁盘一致)'
                  % (f['id'], f['food_name'], fn, ctype.split(';')[0], kind, length))
        else:
            print('  [FAIL] id=%-3s %-14s %s' % (f['id'], f['food_name'], fn))
            if not disk_ok:
                note('food_id=%s food_name=%s food_img=%s —— 磁盘上不存在该文件，'
                     '数据库有记录但文件缺失（需重新上传或清理记录）'
                     % (f['id'], f['food_name'], fn))
            else:
                print('         磁盘存在(%d B) 但 HTTP 返回 status=%s type=%s len=%s'
                      % (disk_size, status, ctype, length))

    print()
    print('  → 菜品图片 LAN 可访问: %d / %d' % (dish_ok, len(foods)))
    if dish_ok == len(foods):
        ok('13/13 菜品图片真实 HTTP 200 且为真实图片内容')
    else:
        bad('%d 道菜品图片未通过' % (len(foods) - dish_ok))

    # ---------------------------------------------------------- 头像
    print()
    print('二、头像（学生 / 管理员，逐个真实 HTTP GET）')
    print('-' * 96)
    avatars = []
    cur.execute('SELECT id, nickname, avatar FROM `users`')
    for u in cur.fetchall():
        avatars.append(('学生', u['id'], u['nickname'], u['avatar']))
    cur.execute('SELECT id, admin_name, avatar FROM `admin_user`')
    for a in cur.fetchall():
        avatars.append(('管理员', a['id'], a['admin_name'], a['avatar']))

    av_ok = 0
    for kind_cn, rid, who, fn in avatars:
        fn = fn or Config.DEFAULT_AVATAR
        url = base + fn
        status, ctype, head, length = http_get(url)
        img = sniff(head)
        if status == 200 and img:
            av_ok += 1
            print('  [OK]   %s id=%-3s %-10s %s -> 200 %s' % (kind_cn, rid, who, fn, ctype.split(';')[0]))
        else:
            print('  [FAIL] %s id=%-3s %-10s %s -> status=%s' % (kind_cn, rid, who, fn, status))
    print()
    print('  → 头像 LAN 可访问: %d / %d' % (av_ok, len(avatars)))
    if avatars and av_ok == len(avatars):
        ok('头像链路与菜品图同一条，全部正常')
    elif avatars:
        bad('%d 个头像未通过' % (len(avatars) - av_ok))

    # ---------------------------------------------------------- 404 语义
    print()
    print('三、404 语义（文件不存在时必须返回真实 HTTP 404，不得返回 HTTP 200 + JSON）')
    print('-' * 96)
    probe = base + 'definitely-not-exists-20260929.jpg'
    status, ctype, head, _ = http_get(probe)
    print('  GET %s' % probe)
    print('       -> status=%s content-type=%s' % (status, ctype))
    if status == 404:
        ok('不存在文件返回真实 HTTP 404')
    elif status == 200:
        bad('不存在文件仍返回 HTTP 200（错误：前端无法区分 404，会把 JSON 当图片解码）')
    else:
        bad('不存在文件返回非预期状态码 %s' % status)

    # ---------------------------------------------------------- 路径穿越
    print()
    print('四、路径穿越防护（不得返回上传目录之外的文件）')
    print('-' * 96)
    for evil in ('../config.py', '..%2fconfig.py', '../../app.py'):
        url = base + evil
        status, ctype, head, _ = http_get(url)
        leaked = b'SECRET_KEY' in head or b'DB_PASSWORD' in head or b'Flask' in head
        if status != 200 and not leaked:
            ok('拒绝 %-16s -> status=%s' % (evil, status))
        else:
            bad('穿越尝试 %s 返回 status=%s 且泄漏=%s' % (evil, status, leaked))

    cn.close()

    print()
    print('=' * 96)
    print('汇总: passed=%d  failed=%d' % (_passed, _failed))
    if _notes:
        print('需要人工处理的条目：')
        for n in _notes:
            print('  - %s' % n)
    print('=' * 96)
    return 1 if _failed else 0


if __name__ == '__main__':
    sys.exit(main())
