# -*- coding: utf-8 -*-
"""业务异常定义与全局异常处理。

核心目标：任何情况下都不得把 Flask 的 HTML 错误页返回给前端。
"""
import logging
import traceback

from flask import Response, request
from werkzeug.exceptions import HTTPException

from utils.response import CODE_BAD_REQUEST, CODE_SERVER_ERROR, CODE_UNAUTHORIZED, error

logger = logging.getLogger('campus_order')


class BizError(Exception):
    """业务异常。抛出后由全局处理器转换为统一 JSON。"""

    def __init__(self, msg='操作失败', code=CODE_BAD_REQUEST):
        super().__init__(msg)
        self.msg = msg
        self.code = code


class ParamError(BizError):
    """参数校验失败。"""

    def __init__(self, msg='参数错误'):
        super().__init__(msg, CODE_BAD_REQUEST)


class AuthError(BizError):
    """未登录 / Token 失效 / 权限不匹配。"""

    def __init__(self, msg='未登录或登录已失效'):
        super().__init__(msg, CODE_UNAUTHORIZED)


def register_error_handlers(app):
    """注册全局异常处理器。"""

    @app.errorhandler(BizError)
    def _handle_biz(exc: BizError):
        logger.info('业务异常: code=%s msg=%s', exc.code, exc.msg)
        return error(exc.msg, exc.code)

    @app.errorhandler(HTTPException)
    def _handle_http(exc: HTTPException):
        # ---- 静态资源（图片等）例外：必须保留真实 HTTP 状态码 ----
        # 全局约定是「HTTP 恒为 200，业务码放 body.code」，这对 /api/* 成立；
        # 但对静态资源会造成两个真实问题：
        #   1. 图片文件不存在时返回 HTTP 200 + JSON 文本，浏览器与小程序
        #      <image> 会把 JSON 当图片解码 → 直接破图，且无法通过状态码排查；
        #   2. msg 统一为「接口不存在」，把「图片文件不存在」误报成「接口不存在」，
        #      掩盖真实原因（曾导致误判为「静态路由未暴露」）。
        # 因此 /static/* 一律按 RFC 返回原始状态码，body 为空。
        if request.path.startswith('/static/'):
            logger.warning('静态资源不可用: %s %s', exc.code, request.path)
            return Response(status=exc.code, mimetype='text/plain; charset=utf-8')

        # 404 / 405 / 413 等一律 JSON 化
        mapping = {
            400: '请求参数错误',
            401: '未登录或登录已失效',
            403: '无访问权限',
            404: '接口不存在',
            405: '请求方法不被允许',
            413: '上传内容过大',
            415: '不支持的媒体类型',
        }
        code = CODE_UNAUTHORIZED if exc.code == 401 else CODE_BAD_REQUEST
        msg = mapping.get(exc.code, exc.description or '请求异常')
        logger.warning('HTTP 异常: %s %s', exc.code, msg)
        return error(msg, code)

    @app.errorhandler(Exception)
    def _handle_any(exc: Exception):
        logger.error('服务异常: %s\n%s', exc, traceback.format_exc())
        return error('服务异常，请稍后再试', CODE_SERVER_ERROR)
