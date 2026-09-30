# -*- coding: utf-8 -*-
"""路由注册。"""
from routes.admin_routes import bp as admin_bp
from routes.cart_routes import bp as cart_bp
from routes.food_routes import bp as food_bp
from routes.notice_routes import bp as notice_bp
from routes.order_routes import bp as order_bp
from routes.static_routes import bp as static_bp
from routes.user_routes import bp as user_bp

# static_bp 显式声明 /static/upload/<filename> → 真实上传目录（只读），
# 使「图片文件名 → 可访问 URL」成为明确契约，而非隐式依赖 Flask static_folder。
ALL_BLUEPRINTS = (static_bp, user_bp, food_bp, cart_bp, order_bp, notice_bp, admin_bp)


def register_blueprints(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
