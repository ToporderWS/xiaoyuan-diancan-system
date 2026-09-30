# -*- coding: utf-8 -*-
"""参数校验工具。所有外部输入必须经过本模块校验后才可进入业务层。"""
import re
from decimal import Decimal, InvalidOperation

from utils.errors import ParamError

PHONE_RE = re.compile(r'^1[3-9]\d{9}$')
# 仅允许中英文、数字、下划线，长度 3-20
ACCOUNT_RE = re.compile(r'^[A-Za-z0-9_]{3,20}$')

MAX_MONEY = Decimal('99999999.99')


def get_json() -> dict:
    """安全获取 JSON body。

    注意：不直接使用 request.get_json()，避免 Content-Type 缺失时抛 415。
    """
    from flask import request
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict() if request.form else {}
    if not isinstance(data, dict):
        raise ParamError('请求体格式错误，应为 JSON 对象')
    return data


def require_str(data: dict, key: str, min_len: int = 1, max_len: int = 255,
                label: str = None, allow_empty: bool = False) -> str:
    """必填字符串。"""
    label = label or key
    val = data.get(key)
    if val is None:
        raise ParamError('%s不能为空' % label)
    val = str(val).strip()
    if not val:
        if allow_empty:
            return ''
        raise ParamError('%s不能为空' % label)
    if len(val) < min_len:
        raise ParamError('%s长度不能少于%d个字符' % (label, min_len))
    if len(val) > max_len:
        raise ParamError('%s长度不能超过%d个字符' % (label, max_len))
    return val


def optional_str(data: dict, key: str, max_len: int = 255, default: str = '',
                 label: str = None) -> str:
    label = label or key
    val = data.get(key)
    if val is None:
        return default
    val = str(val).strip()
    if len(val) > max_len:
        raise ParamError('%s长度不能超过%d个字符' % (label, max_len))
    return val


def require_phone(data: dict, key: str = 'phone', label: str = '手机号') -> str:
    val = require_str(data, key, max_len=20, label=label)
    if not PHONE_RE.match(val):
        raise ParamError('手机号格式不正确')
    return val


def require_account(data: dict, key: str, label: str) -> str:
    val = require_str(data, key, max_len=50, label=label)
    if not ACCOUNT_RE.match(val):
        raise ParamError('%s只能包含字母、数字、下划线，长度3-20位' % label)
    return val


def require_password(data: dict, key: str = 'password', label: str = '密码',
                     min_len: int = 6, max_len: int = 64) -> str:
    val = data.get(key)
    if val is None or str(val) == '':
        raise ParamError('%s不能为空' % label)
    val = str(val)
    if len(val) < min_len:
        raise ParamError('%s长度不能少于%d位' % (label, min_len))
    if len(val) > max_len:
        raise ParamError('%s长度不能超过%d位' % (label, max_len))
    return val


def require_int(data: dict, key: str, label: str = None, min_val: int = None,
                max_val: int = None) -> int:
    label = label or key
    val = data.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ParamError('%s不能为空' % label)
    try:
        num = int(str(val).strip())
    except (TypeError, ValueError):
        raise ParamError('%s必须为整数' % label)
    if min_val is not None and num < min_val:
        raise ParamError('%s不能小于%d' % (label, min_val))
    if max_val is not None and num > max_val:
        raise ParamError('%s不能大于%d' % (label, max_val))
    return num


def optional_int(data: dict, key: str, default=None, label: str = None,
                 min_val: int = None, max_val: int = None):
    label = label or key
    val = data.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        return default
    try:
        num = int(str(val).strip())
    except (TypeError, ValueError):
        raise ParamError('%s必须为整数' % label)
    if min_val is not None and num < min_val:
        raise ParamError('%s不能小于%d' % (label, min_val))
    if max_val is not None and num > max_val:
        raise ParamError('%s不能大于%d' % (label, max_val))
    return num


def require_decimal(data: dict, key: str, label: str = None,
                    min_val: Decimal = Decimal('0'), max_val: Decimal = MAX_MONEY) -> Decimal:
    """必填金额。禁止 float，一律使用 Decimal。"""
    label = label or key
    val = data.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ParamError('%s不能为空' % label)
    try:
        num = Decimal(str(val).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ParamError('%s必须为合法数字' % label)
    if not num.is_finite():
        raise ParamError('%s必须为合法数字' % label)
    num = num.quantize(Decimal('0.01'))
    if num < min_val:
        raise ParamError('%s不能小于%s' % (label, min_val))
    if num > max_val:
        raise ParamError('%s不能大于%s' % (label, max_val))
    return num


def require_bool_int(data: dict, key: str, label: str = None, default: int = None) -> int:
    label = label or key
    val = data.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        if default is not None:
            return default
        raise ParamError('%s不能为空' % label)
    if isinstance(val, bool):
        return 1 if val else 0
    try:
        num = int(str(val).strip())
    except (TypeError, ValueError):
        raise ParamError('%s必须为0或1' % label)
    if num not in (0, 1):
        raise ParamError('%s必须为0或1' % label)
    return num


def parse_page(args, default_size: int = 10, max_size: int = 100):
    """解析分页参数。"""
    page_raw = args.get('page', '1')
    size_raw = args.get('page_size', str(default_size))
    try:
        page = int(page_raw)
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(size_raw)
    except (TypeError, ValueError):
        size = default_size
    page = max(1, page)
    size = max(1, min(size, max_size))
    return page, size


def clamp_keyword(args, key: str = 'keyword', max_len: int = 50) -> str:
    """关键字过滤：去除首尾空白并限制长度，避免超长输入拖垮 LIKE 查询。"""
    val = (args.get(key) or '').strip()
    return val[:max_len]
