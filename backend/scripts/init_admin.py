# -*- coding: utf-8 -*-
"""管理员初始化脚本。

用法：
    # 交互式（推荐，密码不回显）
    python scripts/init_admin.py

    # 非交互式
    python scripts/init_admin.py --admin-name admin --password Admin@123456 --real-name 系统管理员

    # 已存在时重置密码
    python scripts/init_admin.py --admin-name admin --password 新密码 --force

说明：
- 密码仅以 Werkzeug 哈希形式写入数据库，脚本与 SQL 中均不保留明文密码。
- 账号需要满足：字母/数字/下划线，长度 3-20 位。
"""
import argparse
import getpass
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash  # noqa: E402
from pymysql.cursors import DictCursor                # noqa: E402
import pymysql                                        # noqa: E402

from config import Config                             # noqa: E402

ACCOUNT_RE = re.compile(r'^[A-Za-z0-9_]{3,20}$')


def connect(database: str):
    return pymysql.connect(
        host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER,
        password=Config.DB_PASSWORD, database=database,
        charset=Config.DB_CHARSET, cursorclass=DictCursor, autocommit=True,
    )


def main():
    parser = argparse.ArgumentParser(description='初始化 / 重置管理员账号')
    parser.add_argument('--admin-name', default='admin', help='管理员账号（默认 admin）')
    parser.add_argument('--password', default=None, help='管理员密码（不传则交互输入）')
    parser.add_argument('--real-name', default='系统管理员', help='真实姓名')
    parser.add_argument('--avatar', default='default_user.jpg', help='头像文件名')
    parser.add_argument('--force', action='store_true', help='账号已存在时重置密码')
    args = parser.parse_args()

    if not ACCOUNT_RE.match(args.admin_name):
        print('[错误] 管理员账号只能包含字母、数字、下划线，长度 3-20 位')
        return 1

    password = args.password
    if not password:
        if not sys.stdin.isatty():
            print('[错误] 非交互环境下必须通过 --password 传入密码')
            return 1
        password = getpass.getpass('请输入管理员密码（不少于6位）: ')
        confirm = getpass.getpass('请再次输入以确认: ')
        if password != confirm:
            print('[错误] 两次输入的密码不一致')
            return 1
    if len(password) < 6:
        print('[错误] 密码长度不能少于 6 位')
        return 1

    try:
        conn = connect(Config.DB_NAME)
    except Exception as exc:
        print('[错误] 无法连接数据库 %s：%s' % (Config.DB_NAME, exc))
        print('       请先执行 database.sql 建库，并确认 backend/.env 中的数据库配置。')
        return 1

    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM admin_user WHERE admin_name = %s', (args.admin_name,))
            row = cur.fetchone()
            pwd_hash = generate_password_hash(password)
            if row:
                if args.force:
                    cur.execute(
                        'UPDATE admin_user SET password_hash = %s, real_name = %s, avatar = %s '
                        'WHERE id = %s',
                        (pwd_hash, args.real_name, args.avatar, row['id'])
                    )
                    print('[完成] 管理员 %s 的密码已重置' % args.admin_name)
                else:
                    print('[跳过] 管理员 %s 已存在（如需重置密码请加 --force）' % args.admin_name)
            else:
                cur.execute(
                    'INSERT INTO admin_user (admin_name, password_hash, real_name, avatar, '
                    'created_at) VALUES (%s, %s, %s, %s, NOW())',
                    (args.admin_name, pwd_hash, args.real_name, args.avatar)
                )
                print('[完成] 已创建管理员：%s' % args.admin_name)
            cur.execute('SELECT id, admin_name, real_name, avatar, created_at FROM admin_user '
                        'WHERE admin_name = %s', (args.admin_name,))
            info = cur.fetchone()
            print('        账号: %s' % info['admin_name'])
            print('        姓名: %s' % info['real_name'])
            print('        创建: %s' % info['created_at'])
            print('        （数据库中仅保存密码哈希，不保存明文）')
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
