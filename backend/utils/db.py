# -*- coding: utf-8 -*-
"""数据库访问层。

设计要点：
1. 基于 PyMySQL + 轻量连接池，避免每个请求新建 TCP 连接。
2. HTTP 请求内使用 Flask ``g`` 缓存连接，保证「同一请求同一事务」。
3. 全部 SQL 一律使用参数化占位符 ``%s``，从根本上杜绝 SQL 注入。
4. 提供 ``transaction()`` 上下文管理器，异常自动 ROLLBACK。
5. 提供 ``raw_connection()`` 供后台线程（APScheduler）使用，不依赖 Flask 上下文。
"""
import logging
import threading
from contextlib import contextmanager
from queue import Empty, Queue

import pymysql
from flask import g
from pymysql.cursors import DictCursor

logger = logging.getLogger('campus_order')


class ConnectionPool:
    """极简线程安全连接池。连接使用完毕归还，不可用时自动重建。"""

    def __init__(self, conn_kwargs: dict, max_size: int = 16, name: str = 'pool'):
        self._kwargs = dict(conn_kwargs)
        self._max = max(1, int(max_size))
        self._name = name
        self._pool = Queue(maxsize=self._max)
        self._lock = threading.Lock()
        self._created = 0
        self._acquired = 0

    def _create(self):
        conn = pymysql.connect(cursorclass=DictCursor, autocommit=False, **self._kwargs)
        return conn

    def acquire(self):
        # 1) 优先复用空闲连接
        try:
            conn = self._pool.get_nowait()
            try:
                conn.ping(reconnect=True)
                with self._lock:
                    self._acquired += 1
                return conn
            except Exception:
                with self._lock:
                    self._created = max(0, self._created - 1)
                try:
                    conn.close()
                except Exception:
                    pass
        except Empty:
            pass

        # 2) 未达上限则新建
        with self._lock:
            if self._created < self._max:
                self._created += 1
                allowed = True
            else:
                allowed = False
        if allowed:
            try:
                conn = self._create()
                with self._lock:
                    self._acquired += 1
                return conn
            except Exception:
                with self._lock:
                    self._created = max(0, self._created - 1)
                raise

        # 3) 池满则等待归还
        conn = self._pool.get(timeout=15)
        try:
            conn.ping(reconnect=True)
        except Exception:
            with self._lock:
                self._created = max(0, self._created - 1)
            try:
                conn.close()
            except Exception:
                pass
            return self.acquire()
        with self._lock:
            self._acquired += 1
        return conn

    def release(self, conn, broken: bool = False):
        if conn is None:
            return
        with self._lock:
            self._acquired = max(0, self._acquired - 1)
        if broken:
            with self._lock:
                self._created = max(0, self._created - 1)
            try:
                conn.close()
            except Exception:
                pass
            return
        try:
            self._pool.put_nowait(conn)
        except Exception:
            with self._lock:
                self._created = max(0, self._created - 1)
            try:
                conn.close()
            except Exception:
                pass

    def close_all(self):
        while True:
            try:
                conn = self._pool.get_nowait()
            except Empty:
                break
            try:
                conn.close()
            except Exception:
                pass
        with self._lock:
            self._created = 0

    def stats(self):
        with self._lock:
            return {'name': self._name, 'created': self._created,
                    'acquired': self._acquired, 'max': self._max, 'idle': self._pool.qsize()}


class Database:
    """数据库门面对象。"""

    def __init__(self):
        self.pool = None
        self.config = None

    # ------------------------------------------------------------------ 初始化
    def init_app(self, app):
        self.config = app.config
        conn_kwargs = {
            'host': app.config['DB_HOST'],
            'port': app.config['DB_PORT'],
            'user': app.config['DB_USER'],
            'password': app.config['DB_PASSWORD'],
            'database': app.config['DB_NAME'],
            'charset': app.config['DB_CHARSET'],
        }
        self.pool = ConnectionPool(conn_kwargs, max_size=app.config['DB_POOL_SIZE'],
                                   name=app.config['DB_NAME'])
        app.extensions['db'] = self

    def reconfigure(self, database: str):
        """切换数据库（测试用）。"""
        if self.pool:
            self.pool.close_all()
        self.pool = ConnectionPool({
            'host': self.config['DB_HOST'],
            'port': self.config['DB_PORT'],
            'user': self.config['DB_USER'],
            'password': self.config['DB_PASSWORD'],
            'database': database,
            'charset': self.config['DB_CHARSET'],
        }, max_size=self.config['DB_POOL_SIZE'], name=database)

    # ------------------------------------------------------------------ 连接管理
    def _conn(self):
        conn = getattr(g, '_db_conn', None)
        if conn is None:
            conn = self.pool.acquire()
            g._db_conn = conn
        return conn

    def close_request_conn(self, exc):
        """teardown_appcontext 回调。无异常则提交，有异常则回滚。"""
        conn = getattr(g, '_db_conn', None)
        if conn is None:
            return
        g._db_conn = None
        broken = False
        try:
            if exc is None:
                conn.commit()
            else:
                conn.rollback()
        except Exception:
            broken = True
            try:
                conn.rollback()
            except Exception:
                pass
        self.pool.release(conn, broken=broken)

    @contextmanager
    def raw_connection(self):
        """后台线程使用：with db.raw_connection() as conn: ..."""
        conn = self.pool.acquire()
        broken = False
        try:
            yield conn
        except Exception:
            broken = True
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self.pool.release(conn, broken=broken)

    @contextmanager
    def transaction(self):
        """事务上下文。异常自动 ROLLBACK 并向上抛出。"""
        conn = self._conn()
        try:
            conn.begin()
        except Exception:
            pass
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

    # ------------------------------------------------------------------ 查询封装
    def query_all(self, sql, args=None, conn=None):
        cur_conn = conn or self._conn()
        with cur_conn.cursor() as cur:
            cur.execute(sql, args) if args else cur.execute(sql)
            return cur.fetchall()

    def query_one(self, sql, args=None, conn=None):
        cur_conn = conn or self._conn()
        with cur_conn.cursor() as cur:
            cur.execute(sql, args) if args else cur.execute(sql)
            return cur.fetchone()

    def query_scalar(self, sql, args=None, conn=None, key=None):
        row = self.query_one(sql, args, conn)
        if not row:
            return None
        if key is not None:
            return row.get(key)
        return list(row.values())[0]

    def execute(self, sql, args=None, conn=None):
        """执行写语句，返回受影响行数。"""
        cur_conn = conn or self._conn()
        with cur_conn.cursor() as cur:
            cur.execute(sql, args) if args else cur.execute(sql)
            return cur.rowcount

    def insert(self, sql, args=None, conn=None):
        """执行插入，返回自增主键。"""
        cur_conn = conn or self._conn()
        with cur_conn.cursor() as cur:
            cur.execute(sql, args) if args else cur.execute(sql)
            return cur.lastrowid

    def execute_many(self, sql, seq, conn=None):
        cur_conn = conn or self._conn()
        with cur_conn.cursor() as cur:
            cur.executemany(sql, seq)
            return cur.rowcount


# 全局单例
db = Database()
