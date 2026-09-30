# -*- coding: utf-8 -*-
"""《校园点餐管理系统》Flask 后端入口。

启动：
    python app.py
或：
    flask --app app run --host 0.0.0.0 --port 5000
"""
import logging
import os
import sys

from flask import Flask
from flask_cors import CORS

# 保证以 `python app.py` 直接运行时可以按 backend/ 为根导入包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config                      # noqa: E402
from extensions import db                          # noqa: E402
from routes import register_blueprints             # noqa: E402
from scheduler import init_scheduler, shutdown_scheduler  # noqa: E402
from utils.errors import register_error_handlers   # noqa: E402
from utils.response import success                 # noqa: E402


def _setup_logging(app):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    app.logger.setLevel(logging.INFO)


def create_app(config_name=None) -> Flask:
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(get_config(config_name))
    app.json.ensure_ascii = False
    # 上传体积上限（略大于业务上限，便于在业务层给出友好提示）
    app.config['MAX_CONTENT_LENGTH'] = app.config['MAX_UPLOAD_SIZE'] + 512 * 1024

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    _setup_logging(app)

    # 跨域：小程序与 PC 后台均为独立源
    CORS(app,
         resources={r'/api/*': {'origins': '*'}},
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'OPTIONS'],
         supports_credentials=False)

    # 数据库
    db.init_app(app)

    # 统一异常处理（保证永不返回 Flask HTML 错误页）
    register_error_handlers(app)

    # 请求结束统一提交/回滚并归还连接
    app.teardown_appcontext(db.close_request_conn)

    # 路由
    register_blueprints(app)

    # ------------------------------------------------------------ 非业务辅助接口
    @app.get('/')
    def index():
        """服务信息（非业务接口，仅用于确认服务可用）。"""
        return success({
            'service': '校园点餐管理系统 API',
            'version': '1.0.0',
            'api_base': app.config['PUBLIC_API_BASE'],
            'static_base': app.config['PUBLIC_STATIC_BASE'],
        }, '服务运行中')

    @app.get('/api/health')
    def health():
        """健康检查（非业务接口），同时校验数据库连通性。"""
        db_ok = True
        db_msg = 'ok'
        try:
            db.query_scalar('SELECT 1 AS c', key='c')
        except Exception as exc:
            db_ok = False
            db_msg = str(exc)
        return success({
            'status': 'UP' if db_ok else 'DOWN',
            'database': db_msg,
            'database_name': app.config['DB_NAME'],
        })

    # 定时任务（同一平台只允许一个实例运行）
    if not app.config.get('TESTING'):
        init_scheduler(app)

    return app


app = create_app()


if __name__ == '__main__':
    cfg = app.config
    print('=' * 68)
    print('  校园点餐管理系统 · Flask 后端')
    print('  监听地址 : http://0.0.0.0:%d' % cfg['SERVER_PORT'])
    print('  API 基础 : %s' % cfg['PUBLIC_API_BASE'])
    print('  图片基础 : %s' % cfg['PUBLIC_STATIC_BASE'])
    print('  数据库   : %s@%s:%d/%s' % (cfg['DB_USER'], cfg['DB_HOST'], cfg['DB_PORT'], cfg['DB_NAME']))
    print('  上传目录 : %s' % cfg['UPLOAD_FOLDER'])
    print('  定时任务 : %s（每 %ds 扫描，超时 %d 分钟自动取消）' % (
        '开启' if cfg['ENABLE_SCHEDULER'] else '关闭',
        cfg['SCHEDULER_SCAN_INTERVAL'], cfg['ORDER_TIMEOUT_MINUTES']))
    print('=' * 68)
    try:
        # 关闭 reloader，避免调度器被启动两次
        app.run(host='0.0.0.0', port=cfg['SERVER_PORT'], debug=False, use_reloader=False,
                threaded=True)
    finally:
        shutdown_scheduler()
