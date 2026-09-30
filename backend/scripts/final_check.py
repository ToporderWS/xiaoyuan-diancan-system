# -*- coding: utf-8 -*-
"""全项目最终收尾验证 —— 真实 Flask + 真实 MySQL + 真实 HTTP。

与 scripts/e2e_check.py 的关系：
    e2e_check.py 覆盖「订单主链路 + 越权 + 图片上传安全 + 调度器」。
    本脚本**不重复**上述内容，专门补齐 e2e 未覆盖的缺口，并做一次前后台联动与
    数据库一致性收口：

    [1] 静态资源回归（真实 HTTP：200/404 语义、magic bytes、路径穿越）
    [2] 学生端补缺接口（/user/info、update_info、update_pwd、logout、
        /order/my_list 全状态筛选、未登录保护）
    [3] PC 后台补缺接口（/category/save 增改、/admin/food/list 含下架、
        /notice/save 与 /notice/del、/admin/upload_avatar、/update_pwd、/logout）
    [4] 前后台真实联动闭环（PC 增菜带图 → DB → API → 小程序可见；
        学生下单 → DB → PC 可见；PC 改状态 → 小程序同步；库存一致）
    [5] 数据库一致性（负库存、孤儿行、金额勾稽、food_img 纯文件名、
        被引用图片文件是否存在）

用法：
    1) 启动后端：python app.py
    2) python scripts/final_check.py
    3) 指定地址：E2E_BASE=http://192.168.0.103:5000/api python scripts/final_check.py

安全约定：
    - 只用临时账号 / 临时菜品 / 临时分类 / 临时公告，用毕清理；
    - 临时管理员口令随机生成，用毕删除；
    - 不对真实业务数据做任何破坏性写入。
"""
import io
import json
import os
import re
import struct
import sys
import time
import uuid
import zlib

import requests

BASE = os.environ.get('E2E_BASE', 'http://127.0.0.1:5000/api')
STATIC_BASE = BASE[:-len('/api')] + '/static/upload/'

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

from config import Config                              # noqa: E402
from werkzeug.security import generate_password_hash    # noqa: E402
import pymysql                                          # noqa: E402
from pymysql.cursors import DictCursor                  # noqa: E402

UPLOAD_DIR = os.path.join(BACKEND, 'static', 'upload')

STUDENT_PHONE = '13900000997'
STUDENT_PWD = 'Final#Student2026'
STUDENT_PWD2 = 'Final#Student2026b'
TEMP_ADMIN = 'final_temp_admin'
TAG = uuid.uuid4().hex[:8]

PASS, FAIL = [], []
TEMP_FILES = []          # 本脚本落盘的临时图片文件名（收尾时按"无引用"回收）


def check(name, cond, extra=''):
    (PASS if cond else FAIL).append(name)
    print(('  [OK]   ' if cond else '  [FAIL] ') + name
          + (('   -> ' + str(extra)[:260]) if not cond and extra else ''))


def db():
    return pymysql.connect(host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER,
                           password=Config.DB_PASSWORD, database=Config.DB_NAME,
                           charset='utf8mb4', cursorclass=DictCursor, autocommit=True)


def q1(sql, args=None):
    with db() as c, c.cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchone()


def qall(sql, args=None):
    with db() as c, c.cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchall()


def qx(sql, args=None):
    with db() as c, c.cursor() as cur:
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
        return {'code': -1, 'msg': (r.text or '')[:200]}


def get_static(path, timeout=10):
    """返回 (status_code, content_type, content_bytes)。不跟随 3xx。"""
    r = requests.get(STATIC_BASE + path, timeout=timeout, allow_redirects=False)
    return r.status_code, r.headers.get('Content-Type', ''), r.content


def magic_ok(b):
    return (b[:3] == b'\xff\xd8\xff' or b[:8] == b'\x89PNG\r\n\x1a\n'
            or (b[:4] == b'RIFF' and b[8:12] == b'WEBP'))


def drop_file_if_orphan(fn):
    """删除文件，但只在该文件名已不被任何 user / admin_user 记录引用时。"""
    if not fn or fn == Config.DEFAULT_AVATAR:
        return
    still = (q1('SELECT COUNT(*) AS c FROM users WHERE avatar=%s', (fn,))['c']
             + q1('SELECT COUNT(*) AS c FROM admin_user WHERE avatar=%s', (fn,))['c'])
    if still:
        return
    p = os.path.join(UPLOAD_DIR, fn)
    if os.path.isfile(p):
        try:
            os.remove(p)
        except OSError:
            pass


def cleanup():
    """清理本脚本产生的全部临时数据（幂等，可反复执行）。"""
    row = q1('SELECT id FROM users WHERE phone=%s', (STUDENT_PHONE,))
    if row:
        uid = row['id']
        qx('DELETE oi FROM order_item oi INNER JOIN orders o ON o.id=oi.order_id WHERE o.user_id=%s', (uid,))
        qx('DELETE FROM orders WHERE user_id=%s', (uid,))
        qx('DELETE FROM cart WHERE user_id=%s', (uid,))
        qx('DELETE FROM users WHERE id=%s', (uid,))
    adm = q1('SELECT avatar FROM admin_user WHERE admin_name=%s', (TEMP_ADMIN,))
    qx('DELETE FROM admin_user WHERE admin_name=%s', (TEMP_ADMIN,))
    if adm:
        drop_file_if_orphan(adm.get('avatar'))
    for fn in TEMP_FILES:
        drop_file_if_orphan(fn)
    del TEMP_FILES[:]
    qx('DELETE FROM food WHERE food_name LIKE %s', ('联调菜品' + TAG + '%',))
    qx('DELETE FROM food_category WHERE cat_name LIKE %s', ('联调分类%' + TAG + '%',))
    qx('DELETE FROM notice WHERE title LIKE %s', ('联调公告%' + TAG + '%',))


cleanup()
print('=' * 78)
print('  校园点餐系统 · 全项目最终收尾验证（真实 Flask + 真实 MySQL + 真实 HTTP）')
print('  目标地址：%s' % BASE)
print('=' * 78)

# ================================================================ [1] 静态资源回归
print('\n[1] 静态资源回归（真实 HTTP）')
r = requests.get(BASE + '/health', timeout=10)
check('服务在线 /api/health', r.status_code == 200 and body(r)['data']['status'] == 'UP', r.text[:120])

foods_all = qall('SELECT id, food_name, food_img FROM food ORDER BY id')
img_rows = [f for f in foods_all if f['food_img']]
ok_cnt = 0
missing = []
for f in img_rows:
    st, ct, content = get_static(f['food_img'])
    if st == 200 and ct.startswith('image/') and magic_ok(content):
        ok_cnt += 1
    else:
        missing.append('food_id=%s %s img=%s -> %s %s %dB'
                       % (f['id'], f['food_name'], f['food_img'], st, ct or '-', len(content)))
print('    当前菜品图片：%d 道菜有 food_img，%d 张 HTTP 200' % (len(img_rows), ok_cnt))
check('菜品图片 %d/%d 均为真实图片（200 + image/* + magic bytes）' % (ok_cnt, len(img_rows)),
      ok_cnt == len(img_rows) and len(img_rows) > 0, '; '.join(missing[:5]))
if missing:
    for m in missing:
        print('         MISSING -> ' + m)

avatars = []
av_ok = 0
for r_ in qall('SELECT id, nickname, avatar FROM users WHERE avatar IS NOT NULL AND avatar<>%s', ('',)):
    avatars.append(('student', r_['id'], r_['nickname'], r_['avatar']))
for r_ in qall('SELECT id, admin_name, avatar FROM admin_user WHERE avatar IS NOT NULL AND avatar<>%s', ('',)):
    avatars.append(('admin', r_['id'], r_['admin_name'], r_['avatar']))
for kind, rid, who, fn in avatars:
    st, ct, content = get_static(fn)
    if st == 200 and ct.startswith('image/') and magic_ok(content):
        av_ok += 1
    else:
        print('         AVATAR MISS -> %s id=%s %s %s -> %s' % (kind, rid, who, fn, st))
print('    头像：%d 个有头像记录，%d 张 HTTP 200' % (len(avatars), av_ok))
check('头像 %d/%d 全部可访问（学生 + 管理员）' % (av_ok, len(avatars)), av_ok == len(avatars))

st, ct, content = get_static('__definitely_not_exist_%s__.jpg' % TAG)
check('不存在的图片返回真实 HTTP 404（不是 200 + JSON）', st == 404, 'status=%s ct=%s body=%s' % (st, ct, content[:80]))
check('404 响应 Content-Type 不是 application/json（未被业务错误层包装）',
      not ct.startswith('application/json'), ct)

for attack in ['../config.py', '..%2f..%2fconfig.py', '%2e%2e%2fconfig.py', '..\\..\\config.py',
               '....//....//config.py']:
    try:
        rr = requests.get(STATIC_BASE + attack, timeout=10, allow_redirects=False)
        blocked = rr.status_code != 200 or b'DB_PASSWORD' not in rr.content
    except Exception:
        blocked = True
    check('路径穿越被拒绝：%s' % attack, blocked)

# ================================================================ [2] 学生端
print('\n[2] 学生端全功能（补齐 e2e 未覆盖部分）')

# 未登录保护
for path in ['/user/info', '/order/my_list', '/cart/list']:
    check('未登录访问 %s → 401' % path, body(requests.get(BASE + path, timeout=10))['code'] == 401)

reg = body(requests.post(BASE + '/user/register', json={
    'nickname': '收尾联调同学', 'phone': STUDENT_PHONE, 'password': STUDENT_PWD,
    'student_no': 'FIN%s' % TAG, 'dormitory': '宿舍楼5栋 301'}, timeout=10))
check('注册（含学号/宿舍）', reg['code'] == 200, reg)
uid = reg['data']['id'] if reg['code'] == 200 else None
lg = body(requests.post(BASE + '/user/login', json={'phone': STUDENT_PHONE, 'password': STUDENT_PWD}, timeout=10))
check('登录成功', lg['code'] == 200 and lg['data'].get('token'), lg)
SH = {'Authorization': 'Bearer ' + lg['data']['token']}

info = body(requests.get(BASE + '/user/info', headers=SH, timeout=10))
check('GET /user/info 返回完整资料', info['code'] == 200
      and info['data']['nickname'] == '收尾联调同学' and info['data']['dormitory'] == '宿舍楼5栋 301',
      info.get('data'))
check('/user/info 不泄漏 password_hash', 'password_hash' not in json.dumps(info), info)

up = body(requests.post(BASE + '/user/update_info', json={
    'nickname': '收尾联调同学2', 'student_no': 'FIN%sX' % TAG, 'dormitory': '宿舍楼6栋 602'}, headers=SH, timeout=10))
check('POST /user/update_info 修改成功', up['code'] == 200, up)
row = q1('SELECT nickname, student_no, dormitory FROM users WHERE id=%s', (uid,))
check('修改资料已落库', row['nickname'] == '收尾联调同学2' and row['dormitory'] == '宿舍楼6栋 602', row)
info2 = body(requests.get(BASE + '/user/info', headers=SH, timeout=10))
check('登录态保持（原 Token 仍可读回新资料）',
      info2['code'] == 200 and info2['data']['nickname'] == '收尾联调同学2', info2.get('data'))
check('原 Token 在改资料后依然有效（非强退）', info2['code'] == 200)

bad = body(requests.post(BASE + '/user/update_pwd', json={
    'old_password': 'WrongOld#1', 'new_password': STUDENT_PWD2}, headers=SH, timeout=10))
check('原密码错误时改密被拒', bad['code'] == 400, bad)
chg = body(requests.post(BASE + '/user/update_pwd', json={
    'old_password': STUDENT_PWD, 'new_password': STUDENT_PWD2}, headers=SH, timeout=10))
check('POST /user/update_pwd 修改成功', chg['code'] == 200, chg)
check('旧密码登录被拒', body(requests.post(BASE + '/user/login', json={
    'phone': STUDENT_PHONE, 'password': STUDENT_PWD}, timeout=10))['code'] == 400)
lg2 = body(requests.post(BASE + '/user/login', json={'phone': STUDENT_PHONE, 'password': STUDENT_PWD2}, timeout=10))
check('新密码可登录', lg2['code'] == 200 and lg2['data'].get('token'), lg2)
SH = {'Authorization': 'Bearer ' + lg2['data']['token']}
check('改密后密码以哈希入库', (q1('SELECT password_hash FROM users WHERE id=%s', (uid,)) or {})
      .get('password_hash', '').startswith(('scrypt:', 'pbkdf2:')))

out = body(requests.post(BASE + '/user/logout', {}, headers=SH, timeout=10))
check('POST /user/logout 返回成功', out['code'] == 200, out)

# /order/my_list 全状态筛选
public = body(requests.get(BASE + '/food/list?page_size=100', timeout=10))['data']['list']
cands = [f for f in public if f['stock'] >= 30]
check('存在可用于联调的充足库存菜品（>=2 个且库存>=30）', len(cands) >= 2, len(cands))
fa, fb = cands[0], cands[1]

requests.post(BASE + '/cart/save', json={'food_id': fa['id'], 'count': 1}, headers=SH, timeout=10)
o1 = body(requests.post(BASE + '/order/create', json={
    'receive_address': '宿舍楼6栋 602', 'remark': '收尾联调单'}, headers=SH, timeout=10))['data']
requests.post(BASE + '/cart/save', json={'food_id': fb['id'], 'count': 2}, headers=SH, timeout=10)
o2 = body(requests.post(BASE + '/order/create', json={'receive_address': '宿舍楼6栋 602'}, headers=SH, timeout=10))['data']
requests.post(BASE + '/cart/save', json={'food_id': fa['id'], 'count': 1}, headers=SH, timeout=10)
o3 = body(requests.post(BASE + '/order/create', json={'receive_address': '宿舍楼6栋 602'}, headers=SH, timeout=10))['data']
# o5：保持「待支付」态，供状态筛选验证覆盖 status=0
requests.post(BASE + '/cart/save', json={'food_id': fb['id'], 'count': 1}, headers=SH, timeout=10)
o5 = body(requests.post(BASE + '/order/create', json={'receive_address': '宿舍楼6栋 602'}, headers=SH, timeout=10))['data']
requests.post(BASE + '/order/pay', json={'order_id': o1['id']}, headers=SH, timeout=10)   # 0→1
requests.post(BASE + '/order/pay', json={'order_id': o2['id']}, headers=SH, timeout=10)   # 0→1（后续走 1→2→3 状态机）
requests.post(BASE + '/order/pay', json={'order_id': o3['id']}, headers=SH, timeout=10)   # 0→1
requests.post(BASE + '/order/cancel', json={'order_id': o3['id']}, headers=SH, timeout=10)  # →4
_ = o5  # 保留待支付态

ml = body(requests.get(BASE + '/order/my_list?page_size=50', headers=SH, timeout=10))
check('GET /order/my_list 返回列表与状态文案表', ml['code'] == 200
      and ml['data']['total'] >= 3 and len(ml['data']['status_text_map']) == 5, ml.get('data', {}).get('total'))
db_counts = {r['order_status']: r['c'] for r in qall(
    'SELECT order_status, COUNT(*) AS c FROM orders WHERE user_id=%s GROUP BY order_status', (uid,))}
filt_ok = True
detail = []
for s in range(5):
    got = body(requests.get(BASE + '/order/my_list?order_status=%d&page_size=50' % s, headers=SH, timeout=10))
    n_api = got['data']['total'] if got['code'] == 200 else -1
    n_db = db_counts.get(s, 0)
    if n_api != n_db or (got['code'] == 200 and any(x['order_status'] != s for x in got['data']['list'])):
        filt_ok = False
        detail.append('status=%d api=%s db=%s' % (s, n_api, n_db))
check('5 个状态 Tab 筛选均与数据库一致且不含他状态订单',
      filt_ok and len([1 for s in range(5) if db_counts.get(s, 0) > 0]) >= 3,
      '; '.join(detail) or db_counts)
od = body(requests.get(BASE + '/order/detail?order_id=%d' % o2['id'], headers=SH, timeout=10))
check('/order/detail 返回明细与地址', od['code'] == 200 and od['data']['receive_address'] == '宿舍楼6栋 602'
      and len(od['data']['items']) == 1, od.get('data'))
check('/order/my_list 响应不含其他用户订单',
      all(x['id'] != o2['id'] or True for x in ml['data']['list']) and ml['data']['total'] == sum(db_counts.values()),
      'api=%s db=%s' % (ml['data']['total'], sum(db_counts.values())))

# ================================================================ [3] PC 后台
print('\n[3] PC 后台全功能（补齐 e2e 未覆盖部分）')
temp_pwd = 'Fin' + uuid.uuid4().hex[:12] + '#1'
temp_pwd2 = 'Fin' + uuid.uuid4().hex[:12] + '#2'
qx('INSERT INTO admin_user (admin_name, password_hash, real_name, avatar, created_at) '
   'VALUES (%s,%s,%s,%s,NOW())',
   (TEMP_ADMIN, generate_password_hash(temp_pwd), '收尾联调管理员', 'default_user.jpg'))
al = body(requests.post(BASE + '/admin/login', json={'admin_name': TEMP_ADMIN, 'password': temp_pwd}, timeout=10))
check('临时管理员登录成功', al['code'] == 200 and al['data'].get('token'), al)
AH = {'Authorization': 'Bearer ' + al['data']['token']}

# --- 分类：新增 / 编辑 / 列表 / 删除
cat = body(requests.post(BASE + '/admin/category/save', json={
    'cat_name': '联调分类%s' % TAG, 'sort': 99, 'is_show': 1}, headers=AH, timeout=10))
check('POST /admin/category/save 新增分类', cat['code'] == 200 and cat['data'].get('id'), cat)
cid = cat['data']['id'] if cat['code'] == 200 else None
cl = body(requests.get(BASE + '/admin/category/list', headers=AH, timeout=10))
check('新增分类出现在后台分类列表', cl['code'] == 200 and any(x['id'] == cid for x in cl['data']['list']),
      [x['cat_name'] for x in cl.get('data', {}).get('list', [])])
dup = body(requests.post(BASE + '/admin/category/save', json={
    'cat_name': '联调分类%s' % TAG, 'sort': 98, 'is_show': 1}, headers=AH, timeout=10))
check('同名分类被拒（唯一性约束生效）', dup['code'] == 400, dup)
cat2 = body(requests.post(BASE + '/admin/category/save', json={
    'id': cid, 'cat_name': '联调分类%s改' % TAG, 'sort': 98, 'is_show': 1}, headers=AH, timeout=10))
check('POST /admin/category/save 编辑分类', cat2['code'] == 200
      and cat2['data']['cat_name'] == '联调分类%s改' % TAG, cat2)
check('分类改名已落库', q1('SELECT cat_name FROM food_category WHERE id=%s', (cid,))['cat_name']
      == '联调分类%s改' % TAG)

# --- 菜品：新增（下架态）/ 上架联动 / 编辑库存
common = {'cat_id': str(cid), 'food_name': '联调菜品%s' % TAG, 'price': '12.50',
          'stock': '40', 'description': '收尾联调临时菜品', 'is_sale': '0'}
nf = body(requests.post(BASE + '/admin/food/save', data=common,
                        files={'food_img': ('f.png', io.BytesIO(png_bytes()), 'image/png')},
                        headers=AH, timeout=20))
check('后台新增菜品（下架态 + 带图）成功', nf['code'] == 200, nf)
nfid = nf['data']['id'] if nf['code'] == 200 else None
nimg = nf['data']['food_img'] if nf['code'] == 200 else ''
check('food_img 为纯文件名（32位 hex + 后缀，非 URL）',
      bool(nimg) and '/' not in nimg and not nimg.startswith('http')
      and len(nimg.split('.')[0]) == 32, nimg)
check('图片文件已落盘', os.path.isfile(os.path.join(UPLOAD_DIR, nimg)))
st, ct, content = get_static(nimg)
check('新菜品图片真实 HTTP 可访问（真实浏览器路径）', st == 200 and ct.startswith('image/') and magic_ok(content),
      'status=%s ct=%s' % (st, ct))

stu_search = body(requests.get(BASE + '/food/list?keyword=' + '联调菜品%s' % TAG, timeout=10))
check('下架菜品不出现在小程序端列表（真实联动）', stu_search['code'] == 200
      and len(stu_search['data']['list']) == 0, stu_search.get('data'))
adm_search = body(requests.get(BASE + '/admin/food/list?keyword=' + '联调菜品%s' % TAG, headers=AH, timeout=10))
check('GET /admin/food/list 含下架菜品', adm_search['code'] == 200
      and adm_search['data']['total'] == 1, adm_search.get('data', {}).get('total'))

on = body(requests.post(BASE + '/admin/food/save', json={
    'id': nfid, 'cat_id': cid, 'food_name': '联调菜品%s' % TAG, 'price': '12.50',
    'stock': '40', 'description': '上架', 'is_sale': 1}, headers=AH, timeout=10))
check('后台编辑菜品上架（不传图保留原图）', on['code'] == 200 and on['data']['food_img'] == nimg,
      on.get('data', {}).get('food_img'))
stu_search2 = body(requests.get(BASE + '/food/list?keyword=' + '联调菜品%s' % TAG, timeout=10))
check('上架后小程序端立即可见（真实联动）', stu_search2['code'] == 200
      and stu_search2['data']['total'] == 1
      and stu_search2['data']['list'][0]['food_img'] == nimg, stu_search2.get('data'))

# --- 分类停用联动：菜品应从小程序端消失
cat_hide = body(requests.post(BASE + '/admin/category/save', json={
    'id': cid, 'cat_name': '联调分类%s改' % TAG, 'sort': 98, 'is_show': 0}, headers=AH, timeout=10))
check('分类停用成功', cat_hide['code'] == 200, cat_hide)
stu_search3 = body(requests.get(BASE + '/food/list?keyword=' + '联调菜品%s' % TAG, timeout=10))
check('分类停用后该菜品从小程序端隐藏（真实联动）', stu_search3['code'] == 200
      and stu_search3['data']['total'] == 0, stu_search3.get('data'))
body(requests.post(BASE + '/admin/category/save', json={
    'id': cid, 'cat_name': '联调分类%s改' % TAG, 'sort': 98, 'is_show': 1}, headers=AH, timeout=10))

# --- 公告：新增 / 编辑显示态 / 删除（含小程序端联动）
ns = body(requests.post(BASE + '/admin/notice/save', json={
    'title': '联调公告%s' % TAG, 'content': '收尾联调临时公告', 'is_show': 1}, headers=AH, timeout=10))
check('POST /admin/notice/save 新增公告', ns['code'] == 200, ns)
nid = ns['data']['id'] if ns['code'] == 200 else None
pub_n = body(requests.get(BASE + '/notice/list', timeout=10))
check('显示中的公告出现在小程序端公告列表',
      pub_n['code'] == 200 and any(x['id'] == nid for x in pub_n['data']['list']),
      [x['title'] for x in pub_n.get('data', {}).get('list', [])])
ns2 = body(requests.post(BASE + '/admin/notice/save', json={
    'id': nid, 'title': '联调公告%s改' % TAG, 'content': '改', 'is_show': 0}, headers=AH, timeout=10))
check('编辑公告为不显示', ns2['code'] == 200, ns2)
pub_n2 = body(requests.get(BASE + '/notice/list', timeout=10))
check('不显示的公告不出现在小程序端（真实联动）',
      pub_n2['code'] == 200 and not any(x['id'] == nid for x in pub_n2['data']['list']))
al_n = body(requests.get(BASE + '/admin/notice/list', headers=AH, timeout=10))
check('不显示的公告后台仍可见', al_n['code'] == 200
      and any(x['id'] == nid for x in al_n['data']['list']))
nd = body(requests.post(BASE + '/admin/notice/del', json={'id': nid}, headers=AH, timeout=10))
check('POST /admin/notice/del 删除公告', nd['code'] == 200, nd)
check('公告已从数据库删除', q1('SELECT id FROM notice WHERE id=%s', (nid,)) is None)

# --- 管理员头像 / 改密 / 注销
au = requests.post(BASE + '/admin/upload_avatar',
                   files={'avatar': ('管理头像.png', io.BytesIO(png_bytes()), 'image/png')},
                   headers=AH, timeout=15)
aub = body(au)
check('POST /admin/upload_avatar 上传成功', aub['code'] == 200 and '/' not in aub['data']['avatar'], aub)
if aub['code'] == 200:
    TEMP_FILES.append(aub['data']['avatar'])
st, ct, content = get_static(aub['data']['avatar'])
check('管理员头像真实 HTTP 可访问', st == 200 and magic_ok(content), st)
adm_pwd_bad = body(requests.post(BASE + '/admin/update_pwd', json={
    'old_password': 'wrong#1', 'new_password': temp_pwd2}, headers=AH, timeout=10))
check('管理员原密码错误被拒', adm_pwd_bad['code'] == 400, adm_pwd_bad)
adm_pwd = body(requests.post(BASE + '/admin/update_pwd', json={
    'old_password': temp_pwd, 'new_password': temp_pwd2}, headers=AH, timeout=10))
check('POST /admin/update_pwd 修改成功', adm_pwd['code'] == 200, adm_pwd)
check('管理员新密码可登录', body(requests.post(BASE + '/admin/login', json={
    'admin_name': TEMP_ADMIN, 'password': temp_pwd2}, timeout=10))['code'] == 200)
check('管理员旧密码已失效', body(requests.post(BASE + '/admin/login', json={
    'admin_name': TEMP_ADMIN, 'password': temp_pwd}, timeout=10))['code'] == 400)
aout = body(requests.post(BASE + '/admin/logout', {}, headers=AH, timeout=10))
check('POST /admin/logout 返回成功', aout['code'] == 200, aout)

# --- 订单管理筛选 + Dashboard 一致性
al3 = body(requests.post(BASE + '/admin/login', json={'admin_name': TEMP_ADMIN, 'password': temp_pwd2}, timeout=10))
AH = {'Authorization': 'Bearer ' + al3['data']['token']}
ols = body(requests.get(BASE + '/admin/order/list?order_status=1&page_size=100', headers=AH, timeout=10))
check('后台订单列表按状态筛选', ols['code'] == 200
      and all(x['order_status'] == 1 for x in ols['data']['list'])
      and 'status_text_map' in ols['data'], ols.get('data', {}).get('total'))
oday = time.strftime('%Y-%m-%d')
old = body(requests.get(BASE + '/admin/order/list?start_date=%s&end_date=%s&page_size=100' % (oday, oday),
                        headers=AH, timeout=10))
check('后台订单列表按日期筛选可访问', old['code'] == 200, old.get('data', {}).get('total'))
akw = body(requests.get(BASE + '/admin/order/list?keyword=%s' % o1['order_no'], headers=AH, timeout=10))
check('后台订单列表按订单号精确搜索', akw['code'] == 200 and akw['data']['total'] == 1, akw.get('data', {}).get('total'))
dash = body(requests.get(BASE + '/admin/dashboard', headers=AH, timeout=10))
check('Dashboard 4 卡 + 折线 7 点 + 饼图 5 状态 + 柱图非空',
      dash['code'] == 200 and set(dash['data']['cards']) >= {'total_users', 'today_orders', 'today_amount', 'on_sale_foods'}
      and len(dash['data']['order_trend']) == 7 and len(dash['data']['status_pie']) == 5
      and len(dash['data']['category_sales']) > 0, dash.get('data', {}).get('cards'))
ul = body(requests.get(BASE + '/admin/user/list?keyword=%s' % STUDENT_PHONE, headers=AH, timeout=10))
check('后台用户列表可搜索到联调学生', ul['code'] == 200 and ul['data']['total'] == 1, ul.get('data', {}).get('total'))

# ================================================================ [4] 前后台联动闭环
print('\n[4] 前后台联动闭环 + 库存一致性（真实 MySQL 对齐）')

# 4.1 PC 改状态 → 小程序同步
st_a = q1('SELECT stock FROM food WHERE id=%s', (fb['id'],))['stock']
r_receive = body(requests.post(BASE + '/admin/order/receive', json={'order_id': o2['id']}, headers=AH, timeout=10))
check('PC 接单（1→2）成功', r_receive['code'] == 200 and r_receive['data']['order_status'] == 2, r_receive)
stu_2 = body(requests.get(BASE + '/order/my_list?order_status=2&page_size=50', headers=SH, timeout=10))
check('小程序刷新后进入「配送中」Tab（状态同步）',
      stu_2['code'] == 200 and any(x['id'] == o2['id'] for x in stu_2['data']['list']), stu_2.get('data', {}).get('total'))
d2 = body(requests.get(BASE + '/order/detail?order_id=%d' % o2['id'], headers=SH, timeout=10))
check('小程序订单详情状态文案 = 配送中',
      d2['code'] == 200 and d2['data']['order_status'] == 2
      and d2['data'].get('status_text') in ('配送中', '已接单 / 配送中'), d2.get('data', {}).get('status_text'))
sales_before = q1('SELECT sales FROM food WHERE id=%s', (fb['id'],))['sales']
r_finish = body(requests.post(BASE + '/admin/order/finish', json={'order_id': o2['id']}, headers=AH, timeout=10))
check('PC 完成（2→3）成功', r_finish['code'] == 200 and r_finish['data']['order_status'] == 3, r_finish)
stu_3 = body(requests.get(BASE + '/order/my_list?order_status=3&page_size=50', headers=SH, timeout=10))
check('小程序刷新后进入「已完成」Tab（状态同步）',
      stu_3['code'] == 200 and any(x['id'] == o2['id'] for x in stu_3['data']['list']))
sales_after = q1('SELECT sales FROM food WHERE id=%s', (fb['id'],))['sales']
check('完成订单后销量按明细累加（+2）', sales_after - sales_before == 2,
      '%s -> %s' % (sales_before, sales_after))
check('订单状态已落库为 3', q1('SELECT order_status FROM orders WHERE id=%s', (o2['id'],))['order_status'] == 3)

# 4.2 小程序下单 → PC 可见
ols2 = body(requests.get(BASE + '/admin/order/list?keyword=%s' % o2['order_no'], headers=AH, timeout=10))
check('小程序产生的订单在 PC 后台可查（真实闭环）', ols2['code'] == 200 and ols2['data']['total'] == 1
      and ols2['data']['list'][0]['order_status'] == 3, ols2.get('data', {}).get('total'))
od2 = body(requests.get(BASE + '/admin/order/detail?order_id=%d' % o2['id'], headers=AH, timeout=10))
check('PC 后台订单详情含学生信息与明细',
      od2['code'] == 200 and od2['data'].get('nickname') and len(od2['data']['items']) == 1, od2.get('data'))

# 4.3 库存一致性：下单扣减 / 取消回补 / PC 与小程序读同一值
stock_before = q1('SELECT stock FROM food WHERE id=%s', (fa['id'],))['stock']
requests.post(BASE + '/cart/save', json={'food_id': fa['id'], 'count': 3}, headers=SH, timeout=10)
o4 = body(requests.post(BASE + '/order/create', json={'receive_address': '宿舍楼6栋 602'}, headers=SH, timeout=10))['data']
stock_after = q1('SELECT stock FROM food WHERE id=%s', (fa['id'],))['stock']
check('下单按数量扣减库存（-3）', stock_after == stock_before - 3, '%s -> %s' % (stock_before, stock_after))
stu_view = body(requests.get(BASE + '/food/list?page_size=100', timeout=10))['data']['list']
stu_stock = [x['stock'] for x in stu_view if x['id'] == fa['id']]
adm_view = body(requests.get(BASE + '/admin/food/list?keyword=%s' % fa['food_name'], headers=AH, timeout=10))['data']['list']
adm_stock = [x['stock'] for x in adm_view if x['id'] == fa['id']]
check('小程序端与 PC 后台读到同一库存值', stu_stock and adm_stock
      and stu_stock[0] == adm_stock[0] == stock_after, 'stu=%s adm=%s db=%s' % (stu_stock, adm_stock, stock_after))
cancel = body(requests.post(BASE + '/order/cancel', json={'order_id': o4['id']}, headers=SH, timeout=10))
check('取消待支付订单成功（0→4）', cancel['code'] == 200 and cancel['data']['order_status'] == 4, cancel)
check('取消后库存按明细回补（恢复原值）',
      q1('SELECT stock FROM food WHERE id=%s', (fa['id'],))['stock'] == stock_before)
check('取消后订单状态落库为 4', q1('SELECT order_status FROM orders WHERE id=%s', (o4['id'],))['order_status'] == 4)

# 4.4 超库存下单被拒（库存规则未被破坏）
over_food = next((f for f in public if 1 <= f['stock'] < 900), fa)
over_stock = q1('SELECT stock FROM food WHERE id=%s', (over_food['id'],))['stock']
over_n = over_stock + 1
over = body(requests.post(BASE + '/cart/save',
                          json={'food_id': over_food['id'], 'count': over_n}, headers=SH, timeout=10))
check('超库存加购被拒（数量 %d > 库存 %d）' % (over_n, over_stock),
      over['code'] == 400 and '库存' in over['msg'], over)

# 4.5 菜品删除联动
df = body(requests.post(BASE + '/admin/food/del', json={'id': nfid}, headers=AH, timeout=10))
check('后台删除菜品成功', df['code'] == 200, df)
check('菜品已从数据库删除', q1('SELECT id FROM food WHERE id=%s', (nfid,)) is None)
check('菜品图片文件已随删除清理', not os.path.isfile(os.path.join(UPLOAD_DIR, nimg)))
cat_del = body(requests.post(BASE + '/admin/category/del', json={'id': cid}, headers=AH, timeout=10))
check('分类下无菜品时可删除', cat_del['code'] == 200, cat_del)
check('分类已从数据库删除', q1('SELECT id FROM food_category WHERE id=%s', (cid,)) is None)

# ================================================================ [5] 数据库一致性
print('\n[5] 数据库一致性检查（真实 MySQL）')
bad_stock = qall('SELECT id, food_name, stock FROM food WHERE stock < 0')
check('无负库存', not bad_stock, bad_stock[:3])
orphan_item = q1('SELECT COUNT(*) AS c FROM order_item oi LEFT JOIN orders o ON o.id=oi.order_id WHERE o.id IS NULL')['c']
check('无孤儿订单明细（order_item 均能关联 orders）', orphan_item == 0, orphan_item)
orphan_cart_food = q1('SELECT COUNT(*) AS c FROM cart ct LEFT JOIN food f ON f.id=ct.food_id WHERE f.id IS NULL')['c']
check('购物车无失效菜品引用', orphan_cart_food == 0, orphan_cart_food)
orphan_cart_user = q1('SELECT COUNT(*) AS c FROM cart ct LEFT JOIN users u ON u.id=ct.user_id WHERE u.id IS NULL')['c']
check('购物车无失效用户引用', orphan_cart_user == 0, orphan_cart_user)
orphan_food_cat = q1('SELECT COUNT(*) AS c FROM food f LEFT JOIN food_category c ON c.id=f.cat_id WHERE c.id IS NULL')['c']
check('菜品均挂载到存在的分类', orphan_food_cat == 0, orphan_food_cat)
orphan_order_user = q1('SELECT COUNT(*) AS c FROM orders o LEFT JOIN users u ON u.id=o.user_id WHERE u.id IS NULL')['c']
check('订单均属于存在的用户', orphan_order_user == 0, orphan_order_user)

mismatch = qall(
    'SELECT o.id, o.order_no, o.total_price, ROUND(IFNULL(SUM(oi.food_price*oi.count),0),2) AS calc '
    'FROM orders o LEFT JOIN order_item oi ON oi.order_id=o.id '
    'GROUP BY o.id, o.order_no, o.total_price HAVING ABS(o.total_price - calc) > 0.01')
check('订单总价与明细勾稽一致（total_price = Σ 单价×数量）', not mismatch, mismatch[:3])

bad_img = qall("SELECT id, food_name, food_img FROM food WHERE food_img <> '' "
               "AND (food_img LIKE '%%/%%' OR food_img LIKE 'http%%')")
check('所有 food_img 均为纯文件名（无路径、无 URL）', not bad_img, bad_img[:3])

ref_imgs = {r['food_img'] for r in qall("SELECT food_img FROM food WHERE food_img <> ''")}
ref_imgs |= {r['avatar'] for r in qall("SELECT avatar FROM users WHERE avatar IS NOT NULL AND avatar <> ''")}
ref_imgs |= {r['avatar'] for r in qall("SELECT avatar FROM admin_user WHERE avatar IS NOT NULL AND avatar <> ''")}
not_on_disk = [f for f in sorted(ref_imgs) if not os.path.isfile(os.path.join(UPLOAD_DIR, f))]
check('数据库引用的图片文件在磁盘上全部存在（%d 个被引用）' % len(ref_imgs),
      not not_on_disk, not_on_disk[:6])

unused = [f for f in sorted(os.listdir(UPLOAD_DIR))
          if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) and f not in ref_imgs]
print('    [..]  未被数据库引用的图片文件 %d 个（含测试残留，按用户要求本阶段不删，'
      '留待最终清理清单授权）：%s' % (len(unused), ', '.join(unused[:8]) + (' ...' if len(unused) > 8 else '')))

# ================================================================ [6] 清理
print('\n[6] 清理联调数据')
cleanup()
check('联调学生数据已清理', q1('SELECT id FROM users WHERE phone=%s', (STUDENT_PHONE,)) is None)
check('临时管理员已清理', q1('SELECT id FROM admin_user WHERE admin_name=%s', (TEMP_ADMIN,)) is None)
check('临时菜品/分类/公告已清理',
      q1('SELECT id FROM food WHERE food_name LIKE %s', ('联调菜品' + TAG,)) is None
      and q1('SELECT id FROM food_category WHERE cat_name LIKE %s', ('联调分类' + TAG + '%',)) is None
      and q1('SELECT id FROM notice WHERE title LIKE %s', ('联调公告' + TAG + '%',)) is None)
check('真实管理员 admin 仍存在', q1("SELECT id FROM admin_user WHERE admin_name='admin'") is not None)
check('真实菜品数据未被破坏（>=10 道）', q1('SELECT COUNT(*) AS c FROM food')['c'] >= 10,
      q1('SELECT COUNT(*) AS c FROM food')['c'])
check('真实公告数据未被破坏（>=2 条）', q1('SELECT COUNT(*) AS c FROM notice')['c'] >= 2)

print('\n' + '=' * 78)
print('  结果：%d 项通过，%d 项失败' % (len(PASS), len(FAIL)))
if FAIL:
    for f in FAIL:
        print('   x ' + f)
print('=' * 78)
sys.exit(1 if FAIL else 0)
