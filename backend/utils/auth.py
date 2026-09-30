# -*- coding: utf-8 -*-
"""JWT 鉴权与密码哈希。

规则：
- 身份写在 JWT Payload（id / role / exp），数据库不增加 role 字段。
- role=0 学生，role=1 管理员。
- 学生 Token 只能访问学生接口，管理员 Token 只能访问管理员接口。
"""
import datetime as _dt
import functools
import logging

import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from utils.errors import AuthError
from utils.response import CODE_UNAUTHORIZED, error

logger = logging.getLogger('campus_order')

ROLE_STUDENT = 0
ROLE_ADMIN = 1

_ROLE_NAME = {ROLE_STUDENT: '学生', ROLE_ADMIN: '管理员'}


# --------------------------------------------------------------------- 密码安全
def hash_password(raw: str) -> str:
    """生成密码哈希。数据库中只允许存储该哈希。"""
    return generate_password_hash(str(raw))


def verify_password(password_hash: str, raw: str) -> bool:
    """校验密码。"""
    if not password_hash:
        return False
    try:
        return check_password_hash(password_hash, str(raw))
    except Exception:
        return False


# --------------------------------------------------------------------- Token
def generate_token(uid: int, role: int) -> str:
    """签发 JWT。"""
    if role == ROLE_ADMIN:
        minutes = current_app.config['JWT_ADMIN_EXPIRE_MINUTES']
    else:
        minutes = current_app.config['JWT_STUDENT_EXPIRE_MINUTES']
    now = _dt.datetime.utcnow()
    payload = {
        'id': int(uid),
        'role': int(role),
        'iat': now,
        'exp': now + _dt.timedelta(minutes=minutes),
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET'],
                      algorithm=current_app.config['JWT_ALGORITHM'])


def decode_token(token: str) -> dict:
    """解析 JWT，失败统一抛 AuthError。"""
    try:
        return jwt.decode(token, current_app.config['JWT_SECRET'],
                          algorithms=[current_app.config['JWT_ALGORITHM']])
    except jwt.ExpiredSignatureError:
        raise AuthError('登录已过期，请重新登录')
    except jwt.InvalidTokenError:
        raise AuthError('登录凭证无效，请重新登录')


def extract_token() -> str:
    """从 Authorization: Bearer {token} 中提取 Token。"""
    header = request.headers.get('Authorization', '') or ''
    header = header.strip()
    if not header:
        raise AuthError('未登录，请先登录')
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise AuthError('登录凭证格式错误')
    token = parts[1].strip()
    if not token:
        raise AuthError('登录凭证为空')
    return token


def _current_payload():
    payload = getattr(g, '_jwt_payload', None)
    if payload is None:
        payload = decode_token(extract_token())
        g._jwt_payload = payload
    return payload


def current_user_id() -> int:
    """当前登录主体 ID（学生或管理员）。"""
    return int(_current_payload().get('id'))


def current_role() -> int:
    return int(_current_payload().get('role', -1))


def jwt_required(role: int):
    """角色化鉴权装饰器。role 与学生/管理员身份严格绑定。"""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            payload = _current_payload()
            token_role = payload.get('role')
            if token_role != role:
                raise AuthError('当前登录身份无权访问该接口（需要%s权限）' % _ROLE_NAME.get(role, '未知'))
            uid = payload.get('id')
            if not uid:
                raise AuthError('登录凭证缺少用户标识')
            return fn(*args, **kwargs)

        return wrapper

    return decorator


student_required = jwt_required(ROLE_STUDENT)
admin_required = jwt_required(ROLE_ADMIN)


def optional_token_payload():
    """可选鉴权：有 Token 就解析，没有返回 None（用于无需 Token 的浏览接口）。"""
    header = request.headers.get('Authorization', '')
    if not header.strip():
        return None
    try:
        return decode_token(extract_token())
    except AuthError:
        return None


def unauthorized_response(msg='未登录或登录已失效'):
    return error(msg, CODE_UNAUTHORIZED)
