# -*- coding: utf-8 -*-
"""统一 API 返回格式。

所有接口一律返回：
    {"code": 200, "msg": "文本", "data": {}}

约定：
    200 = 成功
    400 = 参数错误 / 业务错误
    401 = 未登录 / Token 失效 / 权限不匹配
    500 = 服务异常
"""
from datetime import date, datetime
from decimal import Decimal

from flask import jsonify

CODE_SUCCESS = 200
CODE_BAD_REQUEST = 400
CODE_UNAUTHORIZED = 401
CODE_SERVER_ERROR = 500


def _default(obj):
    """JSON 序列化兜底：Decimal / datetime / date 均转为可读字符串或数值。"""
    if isinstance(obj, Decimal):
        # 金额统一保留两位小数字符串，避免前端浮点误差
        return float(obj.quantize(Decimal('0.01')))
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    if isinstance(obj, bytes):
        return obj.decode('utf-8', 'replace')
    if isinstance(obj, set):
        return list(obj)
    raise TypeError('Object of type %s is not JSON serializable' % type(obj).__name__)


def _dumps(payload: dict, http_status: int = 200):
    """HTTP 状态码恒为 200，业务状态码放在 body.code，便于前端统一处理。

    使用 json.dumps + default=_default，以支持 Decimal / datetime / date。
    """
    import json
    body = json.dumps(payload, ensure_ascii=False, default=_default)
    resp = jsonify()
    resp.data = body.encode('utf-8')
    resp.status_code = http_status
    resp.mimetype = 'application/json; charset=utf-8'
    return resp


def success(data=None, msg='操作成功'):
    """成功返回。data 为空时统一返回 {}。"""
    return _dumps({'code': CODE_SUCCESS, 'msg': msg, 'data': {} if data is None else data})


def error(msg='操作失败', code=CODE_BAD_REQUEST, data=None):
    """业务错误返回。"""
    return _dumps({'code': code, 'msg': msg, 'data': {} if data is None else data})


def page_data(items, total, page, page_size):
    """分页数据结构。"""
    return {
        'list': items,
        'total': int(total),
        'page': int(page),
        'page_size': int(page_size),
        'pages': (int(total) + int(page_size) - 1) // int(page_size) if page_size else 0,
    }
