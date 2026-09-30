# -*- coding: utf-8 -*-
"""上传图片的只读 HTTP 访问路由。

为什么需要这个文件
------------------
数据库只保存图片**文件名**（food.food_img / users.avatar / admin_user.avatar
均为纯文件名，不含任何路径）。文件名 → URL 的拼接由三端各自完成，且必须与
后端暴露的路径完全一致：

    backend/config.py             PUBLIC_STATIC_BASE = http://<host>:5000/static/upload/
    miniprogram/utils/config.js   STATIC_BASE        = http://<host>:5000/static/upload/
    admin-pc/src/config.js        STATIC_BASE        = http://<host>:5000/static/upload/

原先这条链路只隐式依赖 Flask 内置 static route（static_folder='static'），
存在两个问题：
  1. 一旦 static_folder / 目录结构变动，图片会全线 404，且原因不易察觉；
  2. 404 会被全局异常处理器改写成 HTTP 200 + {"code":400,"msg":"接口不存在"}，
     浏览器与小程序 <image> 无法区分「图片文件不存在」和「接口不存在」，
     反而把真实原因掩盖掉（曾导致把「文件名写错」误判为「静态路由未暴露」）。

因此这里把该契约显式化：/static/upload/<filename> → 真实上传目录中的文件。

安全约束
--------
- 仅注册 GET（Flask 自动附带 HEAD），**不提供任何写入能力**；
- 路径穿越（``../``、绝对路径、Windows 盘符）由 werkzeug 的 ``safe_join``
  直接拒绝，不会返回上传目录之外的任何文件；
- 不做目录列举，不暴露目录结构；
- 文件不存在时返回**真实 HTTP 404**（不伪装成业务 JSON）。
"""
from flask import Blueprint, current_app, send_from_directory

bp = Blueprint('static_upload', __name__)

# 上传文件名是 UUID，内容一经写入永不改变，可放心强缓存，
# 减少真机 / 弱网环境下重复拉取大图造成的加载失败。
_CACHE_SECONDS = 7 * 24 * 60 * 60


@bp.get('/static/upload/<path:filename>')
def uploaded_file(filename):
    """返回上传目录中的图片（只读）。

    目录穿越尝试（例如 ``../config.py``）会被 ``send_from_directory`` 内部
    的 ``safe_join`` 直接拒绝并抛出 404。

    文件不存在时同样抛出 404（werkzeug NotFound），由 ``utils.errors`` 的
    全局处理器转换为**真实 HTTP 404**，不再返回 HTTP 200 + JSON 业务错误。
    """
    resp = send_from_directory(current_app.config['UPLOAD_FOLDER'], filename,
                               conditional=True)
    resp.headers['Cache-Control'] = 'public, max-age=%d' % _CACHE_SECONDS
    # 图片属于公开静态资源：小程序、PC 后台、手机浏览器均可直接读取
    resp.headers['Access-Control-Allow-Origin'] = '*'
    # Content-Type 由扩展名精确决定，禁止浏览器嗅探猜测
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp
