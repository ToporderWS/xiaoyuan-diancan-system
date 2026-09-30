# -*- coding: utf-8 -*-
"""购物车接口（10~12）。全部需要学生 Token，user_id 一律取自 Token。"""
from flask import Blueprint

from services import cart_service
from utils.auth import current_user_id, student_required
from utils.response import success
from utils.validators import get_json, require_int

bp = Blueprint('cart', __name__, url_prefix='/api/cart')


@bp.get('/list')
@student_required
def cart_list():
    """10. GET /api/cart/list"""
    uid = current_user_id()
    items = cart_service.cart_list(uid)
    total_amount = sum(float(i['subtotal']) for i in items if i['valid'])
    return success({
        'list': items,
        'total_count': sum(int(i['count']) for i in items),
        'valid_count': sum(int(i['count']) for i in items if i['valid']),
        'total_amount': round(total_amount, 2),
    })


@bp.post('/save')
@student_required
def cart_save():
    """11. POST /api/cart/save  {food_id, count}

    count 为「本次增加的数量」；若购物车已存在该菜品则累加。
    """
    data = get_json()
    food_id = require_int(data, 'food_id', label='菜品ID', min_val=1)
    count = require_int(data, 'count', label='数量', min_val=1, max_val=999)
    item = cart_service.cart_save(current_user_id(), food_id, count)
    return success(item, '已加入购物车')


@bp.post('/del')
@student_required
def cart_delete():
    """12. POST /api/cart/del  {cart_id}"""
    data = get_json()
    cart_id = require_int(data, 'cart_id', label='购物车ID', min_val=1)
    cart_service.cart_delete(current_user_id(), cart_id)
    return success(None, '已从购物车移除')
