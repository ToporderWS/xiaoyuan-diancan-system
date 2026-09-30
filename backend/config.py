# -*- coding: utf-8 -*-
"""全局配置。所有可变参数集中在此，禁止在业务代码中散落硬编码。"""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 backend/.env（存在时才生效）
load_dotenv(os.path.join(BASE_DIR, '.env'))


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


class Config:
    """基础配置（生产 / 开发共用）。"""

    BASE_DIR = BASE_DIR

    # ---------------- Flask ----------------
    SECRET_KEY = os.getenv('SECRET_KEY', os.getenv('JWT_SECRET', 'campus-order-secret-key'))
    JSON_AS_ASCII = False
    # 禁止 Flask 返回 HTML 错误页（统一由错误处理器转为 JSON）
    PROPAGATE_EXCEPTIONS = False
    TRAP_HTTP_EXCEPTIONS = False

    # ---------------- MySQL ----------------
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = _int('DB_PORT', 3306)
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
    DB_NAME = os.getenv('DB_NAME', 'campus_order')
    DB_POOL_SIZE = _int('DB_POOL_SIZE', 16)
    DB_CHARSET = 'utf8mb4'

    # ---------------- JWT ----------------
    JWT_SECRET = os.getenv('JWT_SECRET', 'campus-order-jwt-secret-please-change')
    JWT_ALGORITHM = 'HS256'
    JWT_STUDENT_EXPIRE_MINUTES = _int('JWT_STUDENT_EXPIRE_MINUTES', 1440)
    JWT_ADMIN_EXPIRE_MINUTES = _int('JWT_ADMIN_EXPIRE_MINUTES', 720)

    # ---------------- 业务 ----------------
    ORDER_TIMEOUT_MINUTES = _int('ORDER_TIMEOUT_MINUTES', 15)
    SCHEDULER_SCAN_INTERVAL = _int('SCHEDULER_SCAN_INTERVAL', 60)
    ENABLE_SCHEDULER = _bool('ENABLE_SCHEDULER', True)

    # ---------------- 上传 ----------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'upload')
    UPLOAD_URL_PREFIX = '/static/upload/'
    MAX_UPLOAD_SIZE = _int('MAX_UPLOAD_SIZE', 2 * 1024 * 1024)  # 2MB
    ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png', 'webp'}
    DEFAULT_AVATAR = 'default_user.jpg'

    # ---------------- 对外地址（集中配置） ----------------
    # 开发环境：填当前电脑的实际局域网 IP（小程序模拟器 / 真机必须用局域网 IP，
    #           127.0.0.1 只能被本机自身访问）。
    # 生产环境：只需把 PUBLIC_API_BASE / PUBLIC_STATIC_BASE 换成 HTTPS 域名，
    #           业务代码无需改动（前端同样只改各自 config 中的两个常量）。
    SERVER_PORT = _int('SERVER_PORT', 5000)
    PUBLIC_API_BASE = os.getenv('PUBLIC_API_BASE', 'http://192.168.0.103:5000/api')
    PUBLIC_STATIC_BASE = os.getenv('PUBLIC_STATIC_BASE', 'http://192.168.0.103:5000/static/upload/')

    # ---------------- 分页 ----------------
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    # ---------------- 角色 ----------------
    ROLE_STUDENT = 0
    ROLE_ADMIN = 1

    # ---------------- 订单状态 ----------------
    ORDER_PENDING_PAY = 0      # 待支付
    ORDER_PENDING_ACCEPT = 1   # 待接单
    ORDER_DELIVERING = 2       # 已接单 / 配送中
    ORDER_FINISHED = 3         # 已完成
    ORDER_CANCELED = 4         # 已取消

    # 合法状态迁移（含取消）
    ORDER_TRANSITIONS = {
        0: {1, 4},
        1: {2, 4},
        2: {3},
        3: set(),
        4: set(),
    }


class TestConfig(Config):
    """pytest 专用配置：独立测试库 + 关闭定时任务 + 关闭跨域限制。"""

    TESTING = True
    DB_NAME = os.getenv('TEST_DB_NAME', 'campus_order_test')
    ENABLE_SCHEDULER = False
    JWT_SECRET = 'test-jwt-secret-for-campus-order-suite-2026'
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'upload_test')
    WTF_CSRF_ENABLED = False


CONFIG_MAP = {
    'development': Config,
    'production': Config,
    'testing': TestConfig,
    'default': Config,
}


def get_config(name: str = None):
    name = name or os.getenv('FLASK_ENV', 'development')
    return CONFIG_MAP.get(name, Config)
