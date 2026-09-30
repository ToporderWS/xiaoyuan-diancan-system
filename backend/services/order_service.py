# -*- coding: utf-8 -*-
"""订单服务 —— 系统核心。

覆盖业务约束：
- 下单：当前购物车全部有效商品结算（不做部分勾选），全流程数据库事务
- 库存：SELECT ... FOR UPDATE 行级锁 + 条件扣减双重保障，绝对禁止超卖
- 金额：一律使用 Decimal 计算，金额与单价全部以后端数据库为准
- 状态机：0→1→2→3，0/1→4；其余迁移一律 400
- 取消：恢复库存，重复取消不重复恢复
- 销量：管理员完成订单（2→3）时按明细累加，事务处理，重复完成不重复累加
"""
import datetime as _dt
import logging
import random
from decimal import Decimal

from flask import current_app

from extensions import db
from services import cart_service
from utils.errors import BizError

logger = logging.getLogger('campus_order')

S0_PENDING_PAY = 0
S1_PENDING_ACCEPT = 1
S2_DELIVERING = 2
S3_FINISHED = 3
S4_CANCELED = 4

STATUS_TEXT = {
    0: '待支付',
    1: '待接单',
    2: '配送中',
    3: '已完成',
    4: '已取消',
}

# 允许被取消的状态（学生侧）
CANCELABLE = (S0_PENDING_PAY, S1_PENDING_ACCEPT)


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.01'))


def _gen_order_no(conn=None) -> str:
    """生成全局唯一订单号：CO + yyyymmddHHMMSS + 4位随机 + 3位序号。"""
    for _ in range(20):
        candidate = 'CO%s%04d%03d' % (
            _dt.datetime.now().strftime('%Y%m%d%H%M%S'),
            random.randint(0, 9999),
            random.randint(0, 999),
        )
        exist = db.query_one('SELECT id FROM orders WHERE order_no = %s', (candidate,), conn=conn)
        if not exist:
            return candidate
    raise BizError('订单号生成失败，请重试')


# --------------------------------------------------------------------- 内部工具
def _lock_order(conn, order_id: int):
    """加行级锁读取订单。"""
    return db.query_one('SELECT * FROM orders WHERE id = %s FOR UPDATE', (order_id,), conn=conn)


def _restore_stock(conn, order_id: int) -> int:
    """按订单明细恢复库存（一次 SQL 完成，天然幂等控制由状态检查保证）。"""
    sql = (
        'UPDATE food f '
        'INNER JOIN (SELECT food_id, SUM(`count`) AS cnt FROM order_item '
        '            WHERE order_id = %s GROUP BY food_id) t ON t.food_id = f.id '
        'SET f.stock = f.stock + t.cnt'
    )
    return db.execute(sql, (order_id,), conn=conn)


def _add_sales(conn, order_id: int) -> int:
    """按订单明细累加销量。"""
    sql = (
        'UPDATE food f '
        'INNER JOIN (SELECT food_id, SUM(`count`) AS cnt FROM order_item '
        '            WHERE order_id = %s GROUP BY food_id) t ON t.food_id = f.id '
        'SET f.sales = f.sales + t.cnt'
    )
    return db.execute(sql, (order_id,), conn=conn)


def _attach_items(orders: list) -> list:
    """批量附加订单明细，避免 N+1 查询。"""
    if not orders:
        return []
    ids = [int(o['id']) for o in orders]
    placeholders = ','.join(['%s'] * len(ids))
    # LEFT JOIN food 仅用于补充当前菜品图片（菜品被删除时返回空字符串，不影响快照数据）
    items = db.query_all(
        'SELECT oi.id, oi.order_id, oi.food_id, oi.food_name, oi.food_price, oi.`count`, '
        '       oi.created_at, IFNULL(f.food_img, \'\') AS food_img '
        'FROM order_item oi LEFT JOIN food f ON f.id = oi.food_id '
        'WHERE oi.order_id IN (' + placeholders + ') ORDER BY oi.id ASC', ids
    ) or []
    bucket = {}
    for it in items:
        it['food_price'] = float(_money(it['food_price']))
        it['count'] = int(it['count'])
        it['subtotal'] = float((_money(it['food_price']) * it['count']).quantize(Decimal('0.01')))
        bucket.setdefault(int(it['order_id']), []).append(it)
    for o in orders:
        o['items'] = bucket.get(int(o['id']), [])
    return orders


def _shape_order(row: dict) -> dict:
    if not row:
        return {}
    out = dict(row)
    out['total_price'] = float(_money(out.get('total_price') or 0))
    out['order_status'] = int(out.get('order_status') or 0)
    out['status_text'] = STATUS_TEXT.get(out['order_status'], '未知')
    out['can_pay'] = out['order_status'] == S0_PENDING_PAY
    out['can_cancel'] = out['order_status'] in CANCELABLE
    return out


# --------------------------------------------------------------------- 创建订单
def create_order(user_id: int, receive_address: str, remark: str) -> dict:
    """冻结契约：对「当前登录学生购物车中的全部商品」结算。"""
    address = (receive_address or '').strip()
    if not address:
        raise BizError('收货地址不能为空')
    if len(address) > 120:
        raise BizError('收货地址长度不能超过120个字符')
    remark = (remark or '').strip()
    if len(remark) > 200:
        raise BizError('备注长度不能超过200个字符')

    with db.transaction() as conn:
        # 1) 取购物车（user_id 来自 Token，前端无法指定）
        carts = db.query_all(
            'SELECT id, food_id, `count` FROM cart WHERE user_id = %s ORDER BY food_id ASC',
            (user_id,), conn=conn
        ) or []
        # 3) 空购物车拒绝
        if not carts:
            raise BizError('购物车为空，无法下单')

        # 4) 数量合法性（兜底：数据库 CHECK 已保证 count>0）
        for c in carts:
            if int(c['count']) <= 0:
                raise BizError('购物车中存在非法数量，请刷新后重试')

        food_ids = sorted({int(c['food_id']) for c in carts})
        ph = ','.join(['%s'] * len(food_ids))

        # 5) 锁定相关菜品（按 id 升序加锁，避免并发死锁）
        foods = db.query_all(
            'SELECT id, cat_id, food_name, price, stock, is_sale FROM food '
            'WHERE id IN (' + ph + ') ORDER BY id ASC FOR UPDATE',
            food_ids, conn=conn
        ) or []
        food_map = {int(f['id']): f for f in foods}

        # 6) 检查菜品存在
        missing = [fid for fid in food_ids if fid not in food_map]
        if missing:
            raise BizError('购物车中有菜品已被删除，请刷新购物车后重试')

        # 7) 检查分类启用
        cat_ids = sorted({int(f['cat_id']) for f in foods})
        cph = ','.join(['%s'] * len(cat_ids))
        cats = db.query_all(
            'SELECT id, is_show FROM food_category WHERE id IN (' + cph + ')', cat_ids, conn=conn
        ) or []
        cat_map = {int(c['id']): int(c['is_show']) for c in cats}
        for f in foods:
            if cat_map.get(int(f['cat_id']), 0) != 1:
                raise BizError('菜品「%s」所属分类已停用，请先移除' % f['food_name'])

        # 8) 检查菜品上架 + 9) 检查库存
        for f in foods:
            if int(f['is_sale']) != 1:
                raise BizError('菜品「%s」已下架，请先移除' % f['food_name'])
            need = sum(int(c['count']) for c in carts if int(c['food_id']) == int(f['id']))
            if int(f['stock']) < need:
                raise BizError('菜品「%s」库存不足（剩余 %d，需要 %d）'
                               % (f['food_name'], int(f['stock']), need))

        # 10) 后端使用数据库 price + 11) Decimal 计算金额
        total = Decimal('0.00')
        item_rows = []
        for c in carts:
            f = food_map[int(c['food_id'])]
            price = _money(f['price'])
            cnt = int(c['count'])
            total += price * cnt
            item_rows.append((int(f['id']), f['food_name'], price, cnt))
        total = _money(total)

        # 12) 唯一订单号
        order_no = _gen_order_no(conn)

        # 13) 创建订单（order_status 由后端决定，前端无法干预）
        order_id = db.insert(
            'INSERT INTO orders (order_no, user_id, total_price, receive_address, remark, '
            'order_status, pay_time, finish_time, created_at) '
            'VALUES (%s, %s, %s, %s, %s, %s, NULL, NULL, NOW())',
            (order_no, user_id, total, address, remark, S0_PENDING_PAY), conn=conn
        )

        # 14) 创建明细快照
        db.execute_many(
            'INSERT INTO order_item (order_id, food_id, food_name, food_price, `count`, created_at) '
            'VALUES (%s, %s, %s, %s, %s, NOW())',
            [(order_id, fid, name, price, cnt) for fid, name, price, cnt in item_rows],
            conn=conn
        )

        # 15) 扣库存（条件更新 + FOR UPDATE 双保险，杜绝超卖）
        for fid, name, price, cnt in item_rows:
            affected = db.execute(
                'UPDATE food SET stock = stock - %s WHERE id = %s AND stock >= %s',
                (cnt, fid, cnt), conn=conn
            )
            if affected != 1:
                raise BizError('菜品「%s」库存不足，下单失败' % name)

        # 16) 清空本次结算的购物车
        cart_ids = [int(c['id']) for c in carts]
        cph2 = ','.join(['%s'] * len(cart_ids))
        db.execute('DELETE FROM cart WHERE user_id = %s AND id IN (' + cph2 + ')',
                   [user_id] + cart_ids, conn=conn)

        # 17) COMMIT —— 由 transaction() 上下文完成

    order = db.query_one('SELECT * FROM orders WHERE id = %s', (order_id,))
    return _shape_order(_attach_items([order])[0])


# --------------------------------------------------------------------- 模拟支付
def pay_order(user_id: int, order_id: int) -> dict:
    """模拟支付：仅允许 0 → 1，并写入 pay_time。

    幂等 / 安全：
    - 订单必须属于当前学生（前端无法传入 user_id）
    - 已取消不能支付；已支付不能重复支付
    - 超过 15 分钟仍未支付的订单，此处同样执行超时取消（与定时任务一致），不可支付
    """
    with db.transaction() as conn:
        order = db.query_one(
            'SELECT * FROM orders WHERE id = %s AND user_id = %s FOR UPDATE',
            (order_id, user_id), conn=conn
        )
        if not order:
            raise BizError('订单不存在或无权操作')

        status = int(order['order_status'])
        if status == S4_CANCELED:
            raise BizError('订单已取消，无法支付')
        if status >= S1_PENDING_ACCEPT:
            raise BizError('订单已支付，请勿重复支付')
        if status != S0_PENDING_PAY:
            raise BizError('订单当前状态不允许支付')

        # 超时兜底：与 APScheduler 使用同一阈值，保证语义一致
        timeout_min = current_app.config['ORDER_TIMEOUT_MINUTES']
        created = order.get('created_at')
        if created and _dt.datetime.now() - created >= _dt.timedelta(minutes=timeout_min):
            db.execute('UPDATE orders SET order_status = %s WHERE id = %s AND order_status = %s',
                       (S4_CANCELED, order_id, S0_PENDING_PAY), conn=conn)
            _restore_stock(conn, order_id)
            raise BizError('订单已超过%d分钟未支付，已自动取消' % timeout_min)

        affected = db.execute(
            'UPDATE orders SET order_status = %s, pay_time = NOW() '
            'WHERE id = %s AND order_status = %s',
            (S1_PENDING_ACCEPT, order_id, S0_PENDING_PAY), conn=conn
        )
        if affected != 1:
            raise BizError('订单状态已变化，支付失败，请刷新后重试')

    row = db.query_one('SELECT * FROM orders WHERE id = %s', (order_id,))
    return _shape_order(_attach_items([row])[0])


# --------------------------------------------------------------------- 取消订单
def cancel_order(user_id: int, order_id: int, operator: str = 'student') -> dict:
    """取消订单：0/1 可取消，恢复库存；重复取消不会再次恢复。"""
    with db.transaction() as conn:
        order = _lock_order(conn, order_id)
        if not order:
            raise BizError('订单不存在')
        if operator == 'student' and int(order['user_id']) != int(user_id):
            raise BizError('订单不存在或无权操作')

        status = int(order['order_status'])
        if status == S4_CANCELED:
            raise BizError('订单已取消，请勿重复取消')
        if status not in CANCELABLE:
            raise BizError('当前订单状态（%s）不允许取消' % STATUS_TEXT.get(status, '未知'))

        affected = db.execute(
            'UPDATE orders SET order_status = %s WHERE id = %s AND order_status = %s',
            (S4_CANCELED, order_id, status), conn=conn
        )
        if affected != 1:
            raise BizError('订单状态已变化，取消失败，请刷新后重试')

        # 恢复库存（一次 SQL）
        _restore_stock(conn, order_id)

    row = db.query_one('SELECT * FROM orders WHERE id = %s', (order_id,))
    return _shape_order(_attach_items([row])[0])


# --------------------------------------------------------------------- 学生查询
def my_orders(user_id: int, order_status=None, page: int = 1, page_size: int = 10) -> dict:
    where = ' WHERE o.user_id = %s'
    args = [user_id]
    if order_status is not None:
        where += ' AND o.order_status = %s'
        args.append(int(order_status))

    total = db.query_scalar('SELECT COUNT(*) AS c FROM orders o' + where, args, key='c')
    rows = db.query_all(
        'SELECT o.* FROM orders o' + where + ' ORDER BY o.id DESC LIMIT %s OFFSET %s',
        args + [page_size, (page - 1) * page_size]
    ) or []
    rows = [_shape_order(o) for o in rows]
    _attach_items(rows)
    return {'list': rows, 'total': total, 'status_text_map': STATUS_TEXT}


def order_detail(user_id: int, order_id: int) -> dict:
    row = db.query_one('SELECT * FROM orders WHERE id = %s AND user_id = %s', (order_id, user_id))
    if not row:
        raise BizError('订单不存在或无权查看')
    return _shape_order(_attach_items([row])[0])


# --------------------------------------------------------------------- 管理员操作
def admin_order_list(order_status=None, keyword: str = '', start_date: str = '',
                     end_date: str = '', page: int = 1, page_size: int = 10) -> dict:
    where = []
    args = []
    if order_status is not None and str(order_status) != '':
        where.append('o.order_status = %s')
        args.append(int(order_status))
    if keyword:
        where.append('(o.order_no LIKE %s OR u.nickname LIKE %s OR u.phone LIKE %s)')
        like = '%%%s%%' % keyword
        args.extend([like, like, like])
    if start_date:
        where.append('o.created_at >= %s')
        args.append(start_date + ' 00:00:00')
    if end_date:
        where.append('o.created_at <= %s')
        args.append(end_date + ' 23:59:59')

    base = 'FROM orders o INNER JOIN users u ON u.id = o.user_id'
    sql_where = (' WHERE ' + ' AND '.join(where)) if where else ''

    total = db.query_scalar('SELECT COUNT(*) AS c ' + base + sql_where, args, key='c')
    rows = db.query_all(
        'SELECT o.*, u.nickname, u.phone, u.student_no, u.dormitory '
        + base + sql_where + ' ORDER BY o.id DESC LIMIT %s OFFSET %s',
        args + [page_size, (page - 1) * page_size]
    ) or []
    rows = [_shape_order(o) for o in rows]
    _attach_items(rows)
    return {'list': rows, 'total': total, 'status_text_map': STATUS_TEXT}


def admin_order_detail(order_id: int) -> dict:
    row = db.query_one(
        'SELECT o.*, u.nickname, u.phone, u.student_no, u.dormitory '
        'FROM orders o INNER JOIN users u ON u.id = o.user_id WHERE o.id = %s', (order_id,)
    )
    if not row:
        raise BizError('订单不存在')
    return _shape_order(_attach_items([row])[0])


def admin_transition(order_id: int, from_status: int, to_status: int, with_sales: bool = False) -> dict:
    """管理员状态迁移（接单 1→2 / 完成 2→3），严格校验状态机。"""
    with db.transaction() as conn:
        order = _lock_order(conn, order_id)
        if not order:
            raise BizError('订单不存在')

        cur = int(order['order_status'])
        if cur == to_status:
            raise BizError('订单已是「%s」状态，请勿重复操作' % STATUS_TEXT.get(to_status, ''))
        if cur != from_status:
            raise BizError('当前订单状态为「%s」，不允许该操作'
                           % STATUS_TEXT.get(cur, '未知'))

        if to_status == S3_FINISHED:
            affected = db.execute(
                'UPDATE orders SET order_status = %s, finish_time = NOW() '
                'WHERE id = %s AND order_status = %s',
                (S3_FINISHED, order_id, S2_DELIVERING), conn=conn
            )
        else:
            affected = db.execute(
                'UPDATE orders SET order_status = %s WHERE id = %s AND order_status = %s',
                (to_status, order_id, from_status), conn=conn
            )
        if affected != 1:
            raise BizError('订单状态已变化，操作失败，请刷新后重试')

        # 销量在 2→3 时累加，且仅在本次真正完成时执行一次
        if with_sales:
            _add_sales(conn, order_id)

    row = db.query_one('SELECT * FROM orders WHERE id = %s', (order_id,))
    return _shape_order(_attach_items([row])[0])


# --------------------------------------------------------------------- 定时任务
def auto_cancel_expired_orders() -> int:
    """扫描并取消超时未支付订单。

    完全基于数据库状态判断，程序重启后依然生效（禁止纯内存 Timer）。
    """
    timeout_min = current_app.config['ORDER_TIMEOUT_MINUTES']
    rows = db.query_all(
        'SELECT id FROM orders WHERE order_status = %s '
        'AND created_at <= DATE_SUB(NOW(), INTERVAL %s MINUTE)',
        (S0_PENDING_PAY, timeout_min)
    ) or []

    canceled = 0
    for r in rows:
        oid = int(r['id'])
        try:
            with db.transaction() as conn:
                order = _lock_order(conn, oid)
                if not order:
                    continue
                # 二次验证：加锁后再判断，避免与用户支付/取消动作冲突
                if int(order['order_status']) != S0_PENDING_PAY:
                    continue
                created = order.get('created_at')
                if not created or _dt.datetime.now() - created < _dt.timedelta(minutes=timeout_min):
                    continue
                affected = db.execute(
                    'UPDATE orders SET order_status = %s WHERE id = %s AND order_status = %s',
                    (S4_CANCELED, oid, S0_PENDING_PAY), conn=conn
                )
                if affected != 1:
                    continue
                _restore_stock(conn, oid)
                canceled += 1
        except Exception as exc:  # 单笔失败不影响其它订单
            logger.error('自动取消订单 %s 失败: %s', oid, exc)
    if canceled:
        logger.info('本次自动取消超时未支付订单 %d 笔', canceled)
    return canceled


# --------------------------------------------------------------------- Dashboard
def dashboard() -> dict:
    total_users = int(db.query_scalar('SELECT COUNT(*) AS c FROM users', key='c') or 0)
    today_orders = int(db.query_scalar(
        'SELECT COUNT(*) AS c FROM orders WHERE DATE(created_at) = CURDATE()', key='c') or 0)
    today_amount = db.query_scalar(
        'SELECT IFNULL(SUM(total_price), 0) AS s FROM orders '
        'WHERE DATE(created_at) = CURDATE() AND order_status IN (1,2,3)', key='s')
    on_sale_foods = int(db.query_scalar(
        'SELECT COUNT(*) AS c FROM food WHERE is_sale = 1', key='c') or 0)

    # 最近 7 天订单数（含无数据的日期，全部由数据库计算，无 Mock）
    raw = db.query_all(
        'SELECT DATE(created_at) AS d, COUNT(*) AS c FROM orders '
        'WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) '
        'GROUP BY DATE(created_at)'
    ) or []
    day_map = {r['d'].strftime('%Y-%m-%d'): int(r['c']) for r in raw}
    trend = []
    today = _dt.date.today()
    for i in range(6, -1, -1):
        day = today - _dt.timedelta(days=i)
        key = day.strftime('%Y-%m-%d')
        trend.append({'date': key, 'label': day.strftime('%m-%d'), 'count': day_map.get(key, 0)})

    # 分类销量
    from services.food_service import category_sales_stat
    cat_sales = category_sales_stat()

    # 订单状态占比
    raw_status = db.query_all(
        'SELECT order_status, COUNT(*) AS c FROM orders GROUP BY order_status') or []
    status_map = {int(r['order_status']): int(r['c']) for r in raw_status}
    status_pie = []
    for st in (0, 1, 2, 3, 4):
        status_pie.append({
            'status': st,
            'name': STATUS_TEXT[st],
            'value': status_map.get(st, 0),
        })

    pending_accept = int(db.query_scalar(
        'SELECT COUNT(*) AS c FROM orders WHERE order_status = 1', key='c') or 0)

    return {
        'cards': {
            'total_users': total_users,
            'today_orders': today_orders,
            'today_amount': float(_money(today_amount or 0)),
            'on_sale_foods': on_sale_foods,
            'pending_accept_orders': pending_accept,
        },
        'order_trend': trend,
        'category_sales': cat_sales,
        'status_pie': status_pie,
    }
