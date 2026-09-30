# -*- coding: utf-8 -*-
"""管理员服务。"""
import logging

from werkzeug.datastructures import FileStorage

from extensions import db
from utils.auth import hash_password, verify_password
from utils.errors import BizError, ParamError
from utils.uploader import save_uploaded_image

logger = logging.getLogger('campus_order')

PUBLIC_FIELDS = ('id', 'admin_name', 'real_name', 'avatar', 'created_at')


def _public(row: dict) -> dict:
    if not row:
        return {}
    return {k: row.get(k) for k in PUBLIC_FIELDS if k in row}


def get_by_name(admin_name: str):
    return db.query_one('SELECT * FROM admin_user WHERE admin_name = %s', (admin_name,))


def get_by_id(aid: int):
    return db.query_one('SELECT * FROM admin_user WHERE id = %s', (aid,))


def login(admin_name: str, password: str) -> dict:
    row = get_by_name(admin_name)
    if not row or not verify_password(row.get('password_hash'), password):
        raise BizError('管理员账号或密码错误')
    return _public(row)


def info(aid: int) -> dict:
    row = get_by_id(aid)
    if not row:
        raise BizError('管理员不存在')
    return _public(row)


def update_password(aid: int, old_password: str, new_password: str) -> None:
    row = get_by_id(aid)
    if not row:
        raise BizError('管理员不存在')
    if not verify_password(row.get('password_hash'), old_password):
        raise BizError('原密码不正确')
    if old_password == new_password:
        raise BizError('新密码不能与原密码相同')
    db.execute('UPDATE admin_user SET password_hash = %s WHERE id = %s',
               (hash_password(new_password), aid))


def update_avatar(aid: int, file: FileStorage, upload_folder: str) -> dict:
    try:
        filename = save_uploaded_image(file, upload_folder)
    except ValueError as exc:
        raise ParamError(str(exc))
    db.execute('UPDATE admin_user SET avatar = %s WHERE id = %s', (filename, aid))
    return info(aid)
