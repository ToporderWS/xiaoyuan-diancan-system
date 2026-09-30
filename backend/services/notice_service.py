# -*- coding: utf-8 -*-
"""公告服务。"""
import logging

from extensions import db
from utils.errors import BizError

logger = logging.getLogger('campus_order')


def public_list(limit: int = 20) -> list:
    """小程序只读取 is_show=1，按 publish_time DESC。"""
    rows = db.query_all(
        'SELECT id, title, content, publish_time, is_show FROM notice '
        'WHERE is_show = 1 ORDER BY publish_time DESC, id DESC LIMIT %s', (int(limit),)
    ) or []
    return rows


def admin_list(keyword: str = '', page: int = 1, page_size: int = 10) -> dict:
    where, args = '', []
    if keyword:
        where = ' WHERE title LIKE %s OR content LIKE %s'
        like = '%%%s%%' % keyword
        args = [like, like]
    total = db.query_scalar('SELECT COUNT(*) AS c FROM notice' + where, args, key='c')
    rows = db.query_all(
        'SELECT id, title, content, publish_time, is_show FROM notice' + where +
        ' ORDER BY publish_time DESC, id DESC LIMIT %s OFFSET %s',
        args + [page_size, (page - 1) * page_size]
    ) or []
    return {'list': rows, 'total': total}


def get(nid: int):
    return db.query_one('SELECT * FROM notice WHERE id = %s', (nid,))


def save(data: dict) -> dict:
    nid = data.get('id')
    title = data['title']
    content = data.get('content', '') or ''
    is_show = int(data.get('is_show', 1))

    if nid:
        if not get(nid):
            raise BizError('公告不存在')
        db.execute('UPDATE notice SET title = %s, content = %s, is_show = %s WHERE id = %s',
                   (title, content, is_show, nid))
    else:
        nid = db.insert(
            'INSERT INTO notice (title, content, publish_time, is_show) VALUES (%s, %s, NOW(), %s)',
            (title, content, is_show)
        )
    return get(nid)


def toggle_show(nid: int, is_show: int) -> dict:
    if not get(nid):
        raise BizError('公告不存在')
    db.execute('UPDATE notice SET is_show = %s WHERE id = %s', (int(is_show), nid))
    return get(nid)


def delete(nid: int) -> None:
    if not get(nid):
        raise BizError('公告不存在')
    db.execute('DELETE FROM notice WHERE id = %s', (nid,))
