# -*- coding: utf-8 -*-
"""菜品分类 / 菜品服务。"""
import logging
from decimal import Decimal

from werkzeug.datastructures import FileStorage

from extensions import db
from utils.errors import BizError, ParamError
from utils.uploader import delete_uploaded_image, save_uploaded_image

logger = logging.getLogger('campus_order')


# ============================================================ 分类
def category_list(only_show: bool = True) -> list:
    sql = 'SELECT id, cat_name, sort, is_show, created_at FROM food_category'
    if only_show:
        sql += ' WHERE is_show = 1'
    sql += ' ORDER BY sort ASC, id ASC'
    return db.query_all(sql) or []


def category_get(cid: int):
    return db.query_one('SELECT * FROM food_category WHERE id = %s', (cid,))


def category_save(data: dict) -> dict:
    """新增 / 编辑分类。"""
    cid = data.get('id')
    cat_name = data['cat_name']
    sort = int(data.get('sort', 0))
    is_show = int(data.get('is_show', 1))

    dup = db.query_one('SELECT id FROM food_category WHERE cat_name = %s AND id <> %s',
                       (cat_name, cid or 0))
    if dup:
        raise BizError('分类名称已存在')

    if cid:
        if not category_get(cid):
            raise BizError('分类不存在')
        db.execute('UPDATE food_category SET cat_name = %s, sort = %s, is_show = %s WHERE id = %s',
                   (cat_name, sort, is_show, cid))
    else:
        cid = db.insert(
            'INSERT INTO food_category (cat_name, sort, is_show, created_at) VALUES (%s, %s, %s, NOW())',
            (cat_name, sort, is_show)
        )
    return category_get(cid)


def category_delete(cid: int) -> None:
    """删除分类。存在关联菜品时必须拒绝，绝不产生脏数据。"""
    if not category_get(cid):
        raise BizError('分类不存在')
    used = db.query_scalar('SELECT COUNT(*) AS c FROM food WHERE cat_id = %s', (cid,), key='c')
    if used:
        raise BizError('该分类下还有 %d 个菜品，无法删除，请先移除或转移菜品' % used)
    db.execute('DELETE FROM food_category WHERE id = %s', (cid,))


# ============================================================ 菜品
def _food_row(row: dict) -> dict:
    """统一菜品输出，附带图片文件名（前端自行拼接静态基址）。"""
    if not row:
        return {}
    out = dict(row)
    if 'price' in out and out['price'] is not None:
        out['price'] = float(Decimal(str(out['price'])).quantize(Decimal('0.01')))
    return out


def food_list(cat_id=None, keyword: str = '', page: int = 1, page_size: int = 10,
              only_sale: bool = True, admin: bool = False) -> dict:
    """菜品分页列表。

    only_sale=True 用于小程序端：只返回上架菜品，且所属分类必须启用。
    admin=True 用于后台：返回全部字段与全部状态。
    """
    where = []
    args = []

    if admin:
        sql_from = 'FROM food f LEFT JOIN food_category c ON c.id = f.cat_id'
    else:
        # 小程序端：必须上架，且所属分类必须启用
        sql_from = 'FROM food f INNER JOIN food_category c ON c.id = f.cat_id'
        where.append('c.is_show = 1')
        where.append('f.is_sale = 1')

    if cat_id:
        where.append('f.cat_id = %s')
        args.append(cat_id)
    if keyword:
        where.append('(f.food_name LIKE %s OR f.description LIKE %s)')
        like = '%%%s%%' % keyword
        args.extend([like, like])

    if where:
        sql_from += ' WHERE ' + ' AND '.join(where)
    full_from = sql_from

    total = db.query_scalar('SELECT COUNT(*) AS c ' + full_from, args, key='c')
    rows = db.query_all(
        'SELECT f.id, f.cat_id, f.food_name, f.price, f.stock, f.sales, f.food_img, '
        '       f.description, f.is_sale, f.created_at, c.cat_name '
        + full_from +
        ' ORDER BY f.is_sale DESC, f.id DESC LIMIT %s OFFSET %s',
        args + [page_size, (page - 1) * page_size]
    ) or []
    return {'list': [_food_row(r) for r in rows], 'total': total}


def food_get(fid: int):
    return db.query_one(
        'SELECT f.*, c.cat_name FROM food f LEFT JOIN food_category c ON c.id = f.cat_id '
        'WHERE f.id = %s', (fid,))


def food_save(data: dict, upload_folder: str, file: FileStorage = None) -> dict:
    """新增 / 编辑菜品（支持 multipart 直接上传图片）。"""
    fid = data.get('id')
    cat_id = int(data['cat_id'])
    food_name = data['food_name']
    price = data['price']          # Decimal，已由校验层保证 >= 0
    stock = int(data['stock'])
    description = data.get('description', '') or ''
    is_sale = int(data.get('is_sale', 1))

    if price < 0:
        raise ParamError('price 不能为负数')
    if stock < 0:
        raise ParamError('stock 不能为负数')

    cat = category_get(cat_id)
    if not cat:
        raise BizError('所属分类不存在')

    dup = db.query_one('SELECT id FROM food WHERE food_name = %s AND cat_id = %s AND id <> %s',
                       (food_name, cat_id, fid or 0))
    if dup:
        raise BizError('该分类下已存在同名菜品')

    new_img = None
    if file is not None and getattr(file, 'filename', ''):
        try:
            new_img = save_uploaded_image(file, upload_folder)
        except ValueError as exc:
            raise ParamError(str(exc))

    if fid:
        old = food_get(fid)
        if not old:
            raise BizError('菜品不存在')
        if new_img:
            db.execute(
                'UPDATE food SET cat_id=%s, food_name=%s, price=%s, stock=%s, food_img=%s, '
                'description=%s, is_sale=%s WHERE id=%s',
                (cat_id, food_name, price, stock, new_img, description, is_sale, fid)
            )
            if old.get('food_img') and old['food_img'] != new_img:
                delete_uploaded_image(old['food_img'], upload_folder)
        else:
            db.execute(
                'UPDATE food SET cat_id=%s, food_name=%s, price=%s, stock=%s, '
                'description=%s, is_sale=%s WHERE id=%s',
                (cat_id, food_name, price, stock, description, is_sale, fid)
            )
    else:
        fid = db.insert(
            'INSERT INTO food (cat_id, food_name, price, stock, sales, food_img, description, '
            'is_sale, created_at) VALUES (%s, %s, %s, %s, 0, %s, %s, %s, NOW())',
            (cat_id, food_name, price, stock, new_img or '', description, is_sale)
        )
    return _food_row(food_get(fid))


def food_delete(fid: int, upload_folder: str = None) -> None:
    """删除菜品。

    注意：被订单快照引用的菜品不设置外键（order_item.food_id 无 FK，保留历史快照），
    因此删除菜品不会破坏历史订单数据；购物车关联行由 FK ON DELETE CASCADE 自动清理。
    """
    row = food_get(fid)
    if not row:
        raise BizError('菜品不存在')
    db.execute('DELETE FROM food WHERE id = %s', (fid,))
    if upload_folder and row.get('food_img'):
        delete_uploaded_image(row['food_img'], upload_folder)


def category_sales_stat() -> list:
    """分类销量统计（Dashboard 柱状图）。

    数据源：已支付及以后订单（status 1/2/3）的明细快照，按分类聚合。
    使用 LEFT JOIN，保证菜品被删除后历史销量仍然计入。
    """
    rows = db.query_all(
        'SELECT IFNULL(c.cat_name, "已删除分类") AS cat_name, '
        '       IFNULL(SUM(oi.count), 0) AS sales '
        'FROM order_item oi '
        'INNER JOIN orders o ON o.id = oi.order_id '
        'LEFT JOIN food f ON f.id = oi.food_id '
        'LEFT JOIN food_category c ON c.id = f.cat_id '
        'WHERE o.order_status IN (1, 2, 3) '
        'GROUP BY c.cat_name ORDER BY sales DESC'
    ) or []
    return [{'cat_name': r['cat_name'], 'sales': int(r['sales'])} for r in rows]
