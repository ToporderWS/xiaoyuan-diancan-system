# -*- coding: utf-8 -*-
"""学生订单接口（13~17、17A）。"""
from flask import Blueprint, request

from services import order_service
from utils.auth import current_user_id, student_required
from utils.response import success
from utils.validators import get_json, optional_int, optional_str, parse_page, require_int, require_str

bp = Blueprint('order', __name__, url_prefix='/api/order')


@bp.post('/create')
@student_required
def create_order():
    """13. POST /api/order/create  {receive_address, remark}

    冻结契约：结算当前购物车全部有效商品，不做部分勾选结算。
    """
    data = get_json()
    address = require_str(data, 'receive_address', max_len=120, label='收货地址')
    remark = optional_str(data, 'remark', max_len=200, label='备注')
    order = order_service.create_order(current_user_id(), address, remark)
    return success(order, '下单成功')


@bp.get('/my_list')
@student_required
def my_list():
    """14. GET /api/order/my_list  query: order_status / page / page_size"""
    status = optional_int(request.args, 'order_status', default=None,
                          label='订单状态', min_val=0, max_val=4)
    page, page_size = parse_page(request.args, 10, 100)
    result = order_service.my_orders(current_user_id(), status, page, page_size)
    return success({
        'list': result['list'],
        'total': result['total'],
        'page': page,
        'page_size': page_size,
        'pages': (int(result['total']) + page_size - 1) // page_size,
        'status_text_map': order_service.STATUS_TEXT,
    })


@bp.get('/detail')
@student_required
def detail():
    """15. GET /api/order/detail?order_id=1"""
    order_id = require_int(request.args, 'order_id', label='订单ID', min_val=1)
    return success(order_service.order_detail(current_user_id(), order_id))


@bp.post('/cancel')
@student_required
def cancel():
    """16. POST /api/order/cancel  {order_id}

    仅 0 / 1 可取消；取消后按明细恢复库存，重复取消不会重复恢复。
    """
    data = get_json()
    order_id = require_int(data, 'order_id', label='订单ID', min_val=1)
    return success(order_service.cancel_order(current_user_id(), order_id), '订单已取消')


@bp.post('/pay')
@student_required
def pay():
    """17A. POST /api/order/pay  {order_id}

    【模拟支付】仅允许 0 → 1，并写入 pay_time。
    本接口不接入真实微信支付，前端 UI 必须明确标注「模拟支付」。
    """
    data = get_json()
    order_id = require_int(data, 'order_id', label='订单ID', min_val=1)
    return success(order_service.pay_order(current_user_id(), order_id), '模拟支付成功')
