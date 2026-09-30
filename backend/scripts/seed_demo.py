# -*- coding: utf-8 -*-
"""可选：写入演示菜品与公告（幂等，可重复执行）。

用途：让刚建好的系统立刻可点餐、可联调、可验收。
说明：本脚本写入的是真实业务数据（非 Mock），仅在显式执行时生效。

用法：
    python scripts/seed_demo.py
    python scripts/seed_demo.py --reset     # 先清空菜品与公告再写入
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql                                       # noqa: E402
from pymysql.cursors import DictCursor               # noqa: E402

from config import Config                            # noqa: E402

# (分类名, 菜名, 价格, 库存, 描述)
FOODS = [
    ('早餐', '小笼包套餐', '6.00', 120, '现蒸小笼包 6 只，配豆浆一杯'),
    ('早餐', '手抓饼加蛋', '5.50', 80, '现做手抓饼加鸡蛋，酥脆可口'),
    ('快餐', '红烧牛肉饭', '15.00', 60, '慢炖牛腩配时蔬，附例汤'),
    ('快餐', '香辣鸡腿饭', '15.00', 80, '香煎鸡腿配米饭，微辣'),
    ('快餐', '番茄炒蛋盖饭', '12.00', 70, '家常番茄炒蛋，酸甜开胃'),
    ('面食', '红烧牛肉面', '12.00', 100, '秘制牛骨汤底，牛腩软糯'),
    ('面食', '酸辣粉', '9.00', 90, '重庆风味，酸辣爽口'),
    ('饮品', '招牌奶茶', '8.00', 150, '现泡红茶 + 鲜奶，可选糖度'),
    ('饮品', '柠檬茶', '6.00', 120, '手打柠檬，清爽解腻'),
    ('小吃', '蒜蓉小龙虾（小份）', '28.00', 30, '每日限量供应'),
    ('小吃', '香酥鸡米花', '7.00', 100, '现炸鸡米花，外酥里嫩'),
    ('小吃', '烤肠', '4.00', 0, '今日已售罄，明日请早'),
]

NOTICES = [
    ('校园食堂今日上新，欢迎选购', '本店今日新增小笼包套餐、酸辣粉等新品，欢迎同学们品尝。'),
    ('营业时间调整通知', '自本周起，二楼档口营业时间调整为 07:00 - 20:30，请合理安排点餐时间。'),
]

IMG_EXTS = ('.jpg', '.jpeg', '.png', '.webp')


def match_uploaded_image(upload_folder: str, food_name: str) -> str:
    """若 static/upload/ 下存在与菜名同名的真实图片文件，则返回其文件名，否则返回空串。

    例如把 `烤肠.jpg` 放进 backend/static/upload/，再执行本脚本，
    该菜品会自动关联到 `烤肠.jpg`（返回文件名，数据库只存文件名）。

    之所以不再像旧版那样直接写入 'food-default.jpg'：
    该占位图只能由前端在「未设置图片 / 图片字段为空 / 加载失败」时兜底，
    不应作为真实值写进数据库，否则所有菜品会永远显示同一张占位图。
    """
    if not upload_folder or not os.path.isdir(upload_folder):
        return ''
    for ext in IMG_EXTS:
        candidate = food_name + ext
        if os.path.isfile(os.path.join(upload_folder, candidate)):
            return candidate
    return ''


def main():
    parser = argparse.ArgumentParser(description='写入演示菜品与公告')
    parser.add_argument('--reset', action='store_true', help='先清空 food / notice 再写入')
    args = parser.parse_args()

    conn = pymysql.connect(host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER,
                           password=Config.DB_PASSWORD, database=Config.DB_NAME,
                           charset=Config.DB_CHARSET, cursorclass=DictCursor, autocommit=False)
    upload_folder = Config.UPLOAD_FOLDER
    created_food = 0
    linked_img = 0
    created_notice = 0
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, cat_name FROM food_category')
            cat_map = {r['cat_name']: r['id'] for r in cur.fetchall()}
            missing = [c for c in {f[0] for f in FOODS} if c not in cat_map]
            if missing:
                print('[错误] 缺少分类：%s，请先执行 database.sql' % '、'.join(missing))
                return 1

            if args.reset:
                cur.execute('SET FOREIGN_KEY_CHECKS = 0')
                cur.execute('DELETE FROM food')
                cur.execute('DELETE FROM notice')
                cur.execute('SET FOREIGN_KEY_CHECKS = 1')
                print('[清理] 已清空 food / notice')

            for cat_name, name, price, stock, desc in FOODS:
                cur.execute('SELECT id FROM food WHERE food_name = %s AND cat_id = %s',
                            (name, cat_map[cat_name]))
                if cur.fetchone():
                    continue
                food_img = match_uploaded_image(upload_folder, name)
                if food_img:
                    linked_img += 1
                cur.execute(
                    'INSERT INTO food (cat_id, food_name, price, stock, sales, food_img, '
                    'description, is_sale, created_at) VALUES (%s,%s,%s,%s,0,%s,%s,1,NOW())',
                    (cat_map[cat_name], name, price, stock, food_img, desc))
                created_food += 1

            for title, content in NOTICES:
                cur.execute('SELECT id FROM notice WHERE title = %s', (title,))
                if cur.fetchone():
                    continue
                cur.execute('INSERT INTO notice (title, content, publish_time, is_show) '
                            'VALUES (%s, %s, NOW(), 1)', (title, content))
                created_notice += 1

            cur.execute('SELECT COUNT(*) AS c FROM food')
            food_total = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) AS c FROM notice')
            notice_total = cur.fetchone()['c']
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print('[错误] 写入失败：%s' % exc)
        return 1
    finally:
        conn.close()

    print('[完成] 新增菜品 %d 个（现有 %d，其中自动关联真实图片 %d 个），新增公告 %d 条（现有 %d）'
          % (created_food, food_total, linked_img, created_notice, notice_total))
    print('       未关联图片的菜品 food_img 为空，由小程序/后台按「未设置图片」规则显示兜底占位图。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
