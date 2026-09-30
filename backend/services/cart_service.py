# -*- coding: utf-8 -*-
"""购物车服务。购物车数据实时读写 MySQL，不做本地缓存。"""
import logging
from decimal import Decimal

from extensions import db
from utils.errors import BizError, ParamError

logger = logging.getLogger('campus_order')


def _shape(row: dict) -> dict:
    """补充派生字段：小计、是否可选、无效原因。"""
    count = int(row.get('count') or 0)
    price = Decimal(str(row.get('price') or 0))
    stock = row.get('stock')
    is_sale = int(row.get('is_sale') or 0)
    cat_show = int(row.get('cat_show') or 0)

    out = dict(row)
    out['price'] = float(price.quantize(Decimal('0.01')))
    out['subtotal'] = float((price * count).quantize(Decimal('0.01')))
    out['stock'] = int(stock) if stock is not None else 0
    out['count'] = count

    reason = ''
    if not is_sale:
        reason = '菜品已下架'
    elif not cat_show:
        reason = '所属分类已停用'
    elif stock is not None and count > int(stock):
        reason = '库存不足（剩余 %d）' % int(stock)
    elif stock is not None and int(stock) <= 0:
        reason = '已售罄'
    out['invalid_reason'] = reason
    out['valid'] = (reason == '')
    return out


_BASE_SELECT = (
    'SELECT c.id, c.user_id, c.food_id, c.count, c.created_at, '
    '       f.food_name, f.price, f.stock, f.food_img, f.is_sale, '
    '       fc.is_show AS cat_show, fc.cat_name '
    'FROM cart c '
    'INNER JOIN food f ON f.id = c.food_id '
    'LEFT JOIN food_category fc ON fc.id = f.cat_id '
)


def cart_list(user_id: int) -> list:
    """当前学生购物车。"""
    rows = db.query_all(_BASE_SELECT + 'WHERE c.user_id = %s ORDER BY c.id DESC', (user_id,)) or []
    return [_shape(r) for r in rows]


def cart_save(user_id: int, food_id: int, count: int) -> dict:
    """加入购物车 / 修改数量。

    规则：数量必须 >=1，且「最终数量」不得超过当前库存。
    前端无法指定 user_id，user_id 一律取自 JWT。
    """
    if count <= 0:
        raise ParamError('数量必须大于 0')

    food = db.query_one(
        'SELECT f.id, f.food_name, f.price, f.stock, f.is_sale, fc.is_show AS cat_show '
        'FROM food f LEFT JOIN food_category fc ON fc.id = f.cat_id WHERE f.id = %s',
        (food_id,)
    )
    if not food:
        raise BizError('菜品不存在')
    if not int(food.get('is_sale') or 0):
        raise BizError('该菜品已下架')
    if not int(food.get('cat_show') or 0):
        raise BizError('该菜品所属分类已停用')

    stock = int(food.get('stock') or 0)
    if stock <= 0:
        raise BizError('该菜品已售罄')

    exist = db.query_one('SELECT id, count FROM cart WHERE user_id = %s AND food_id = %s',
                         (user_id, food_id))
    final_count = count if not exist else int(exist['count']) + count

    if final_count > stock:
        raise BizError('库存不足，当前库存 %d，购物车数量 %d' % (stock, final_count))

    if exist:
        db.execute('UPDATE cart SET count = %s WHERE id = %s AND user_id = %s',
                   (final_count, exist['id'], user_id))
        cart_id = exist['id']
    else:
        cart_id = db.insert(
            'INSERT INTO cart (user_id, food_id, count, created_at) VALUES (%s, %s, %s, NOW())',
            (user_id, food_id, final_count)
        )

    row = db.query_one(_BASE_SELECT + 'WHERE c.id = %s AND c.user_id = %s', (cart_id, user_id))
    return _shape(row)


def cart_delete(user_id: int, cart_id: int) -> None:
    """删除购物车条目。带 user_id 条件，杜绝越权删除他人购物车。"""
    row = db.query_one('SELECT id FROM cart WHERE id = %s AND user_id = %s', (cart_id, user_id))
    if not row:
        raise BizError('购物车记录不存在或无权操作')
    db.execute('DELETE FROM cart WHERE id = %s AND user_id = %s', (cart_id, user_id))


def cart_count(user_id: int) -> int:
    return int(db.query_scalar('SELECT IFNULL(SUM(count),0) AS c FROM cart WHERE user_id = %s',
                               (user_id,), key='c') or 0)


def admin_cart_list(keyword: str, page: int, page_size: int) -> dict:
    """管理员只读查看学生购物车。本版本不提供管理员修改入口。"""
    where, args = '', []
    if keyword:
        where = ' WHERE u.nickname LIKE %s OR u.phone LIKE %s OR u.student_no LIKE %s ' \
                'OR f.food_name LIKE %s'
        like = '%%%s%%' % keyword
        args = [like, like, like, like]

    base = ('FROM cart c '
            'INNER JOIN users u ON u.id = c.user_id '
            'INNER JOIN food f ON f.id = c.food_id '
            'LEFT JOIN food_category fc ON fc.id = f.cat_id')
    total = db.query_scalar('SELECT COUNT(*) AS c ' + base + where, args, key='c')
    rows = db.query_all(
        'SELECT c.id, c.user_id, c.food_id, c.count, c.created_at, '
        '       u.nickname, u.phone, u.student_no, '
        '       f.food_name, f.price, f.stock, f.food_img, f.is_sale, '
        '       IFNULL(fc.is_show, 0) AS cat_show, fc.cat_name '
        + base + where +
        ' ORDER BY c.id DESC LIMIT %s OFFSET %s',
        args + [page_size, (page - 1) * page_size]
    ) or []
    return {'list': [_shape(r) for r in rows], 'total': total}
