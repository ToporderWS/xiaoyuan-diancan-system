# -*- coding: utf-8 -*-
"""菜品 / 分类（学生端公开浏览）接口（8、9）。"""
from flask import Blueprint, request

from services import food_service
from utils.response import success
from utils.validators import clamp_keyword, optional_int, parse_page

bp = Blueprint('food', __name__, url_prefix='/api/food')


@bp.get('/category/list')
def category_list():
    """8. GET /api/food/category/list —— 无需 Token。"""
    return success({'list': food_service.category_list(only_show=True)})


@bp.get('/list')
def food_list():
    """9. GET /api/food/list —— 无需 Token。

    支持 query：cat_id / keyword / page / page_size
    """
    cat_id = optional_int(request.args, 'cat_id', default=None, label='分类ID', min_val=1)
    keyword = clamp_keyword(request.args)
    page, page_size = parse_page(request.args, 10, 100)
    result = food_service.food_list(cat_id=cat_id, keyword=keyword,
                                    page=page, page_size=page_size,
                                    only_sale=True, admin=False)
    return success({
        'list': result['list'],
        'total': result['total'],
        'page': page,
        'page_size': page_size,
        'pages': (int(result['total']) + page_size - 1) // page_size,
    })
