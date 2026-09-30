# -*- coding: utf-8 -*-
"""公告接口（17，公开浏览）。"""
from flask import Blueprint

from services import notice_service
from utils.response import success

bp = Blueprint('notice', __name__, url_prefix='/api/notice')


@bp.get('/list')
def notice_list():
    """17. GET /api/notice/list —— 无需 Token，只返回 is_show=1。"""
    return success({'list': notice_service.public_list(limit=20)})
