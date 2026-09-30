# -*- coding: utf-8 -*-
"""学生用户服务。"""
import logging

from werkzeug.datastructures import FileStorage

from extensions import db
from utils.auth import hash_password, verify_password
from utils.errors import BizError, ParamError
from utils.uploader import save_uploaded_image

logger = logging.getLogger('campus_order')

# 对外输出字段白名单 —— 绝不允许把 password_hash 返回给前端
PUBLIC_FIELDS = ('id', 'phone', 'nickname', 'avatar', 'student_no', 'dormitory', 'created_at')


def _public(row: dict) -> dict:
    if not row:
        return {}
    return {k: row.get(k) for k in PUBLIC_FIELDS if k in row}


def get_by_phone(phone: str):
    return db.query_one('SELECT * FROM users WHERE phone = %s', (phone,))


def get_by_id(uid: int):
    return db.query_one('SELECT * FROM users WHERE id = %s', (uid,))


def register(data: dict) -> dict:
    """注册学生账号。"""
    phone = data['phone']
    if get_by_phone(phone):
        raise BizError('该手机号已注册，请直接登录')

    password_hash = hash_password(data['password'])
    uid = db.insert(
        'INSERT INTO users (phone, password_hash, nickname, avatar, student_no, dormitory, created_at) '
        'VALUES (%s, %s, %s, %s, %s, %s, NOW())',
        (phone, password_hash, data['nickname'], 'default_user.jpg',
         data.get('student_no', ''), data.get('dormitory', ''))
    )
    return _public(get_by_id(uid))


def login(phone: str, password: str) -> dict:
    """登录校验。返回用户公开信息，密码错误一律同一提示（不泄露账号是否存在）。"""
    row = get_by_phone(phone)
    if not row or not verify_password(row.get('password_hash'), password):
        raise BizError('手机号或密码错误')
    return _public(row)


def update_info(uid: int, nickname: str, student_no: str, dormitory: str) -> dict:
    db.execute(
        'UPDATE users SET nickname = %s, student_no = %s, dormitory = %s WHERE id = %s',
        (nickname, student_no, dormitory, uid)
    )
    return _public(get_by_id(uid))


def update_password(uid: int, old_password: str, new_password: str) -> None:
    row = get_by_id(uid)
    if not row:
        raise BizError('用户不存在')
    if not verify_password(row.get('password_hash'), old_password):
        raise BizError('原密码不正确')
    if old_password == new_password:
        raise BizError('新密码不能与原密码相同')
    db.execute('UPDATE users SET password_hash = %s WHERE id = %s',
               (hash_password(new_password), uid))


def update_avatar(uid: int, file: FileStorage, upload_folder: str) -> dict:
    try:
        filename = save_uploaded_image(file, upload_folder)
    except ValueError as exc:
        raise ParamError(str(exc))
    db.execute('UPDATE users SET avatar = %s WHERE id = %s', (filename, uid))
    return _public(get_by_id(uid))


def admin_list(keyword: str, page: int, page_size: int) -> dict:
    """管理员查看学生用户列表（只读）。"""
    where, args = '', []
    if keyword:
        where = ' WHERE nickname LIKE %s OR phone LIKE %s OR student_no LIKE %s OR dormitory LIKE %s'
        like = '%%%s%%' % keyword
        args = [like, like, like, like]

    total = db.query_scalar('SELECT COUNT(*) AS c FROM users' + where, args, key='c')
    rows = db.query_all(
        'SELECT id, phone, nickname, avatar, student_no, dormitory, created_at '
        'FROM users' + where + ' ORDER BY id DESC LIMIT %s OFFSET %s',
        args + [page_size, (page - 1) * page_size]
    ) or []
    return {'list': [_public(r) for r in rows], 'total': total}
