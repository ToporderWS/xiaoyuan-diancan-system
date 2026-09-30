# -*- coding: utf-8 -*-
"""管理员接口（18~28 + 最小必要补充接口）。

所有接口（login 除外）均要求管理员 Token。
学生 Token 调用一律返回 code=401。
"""
from flask import Blueprint, current_app, request

from services import (admin_service, cart_service, food_service, notice_service,
                      order_service, user_service)
from utils.auth import ROLE_ADMIN, admin_required, current_user_id, generate_token
from utils.response import success
from utils.validators import (clamp_keyword, get_json, optional_int, optional_str, parse_page,
                              require_bool_int, require_decimal, require_int,
                              require_password, require_str)

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def _body():
    """兼容 JSON 与 multipart/form-data（菜品新增/编辑需要带图上传）。"""
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form.to_dict()
        if request.files:
            data['__files__'] = request.files
        return data
    return get_json()


def _file_of(data, *names):
    files = data.get('__files__')
    if not files:
        return None
    for n in names:
        if n in files:
            return files[n]
    return None


# =============================================================== 18. 登录
@bp.post('/login')
def login():
    """18. POST /api/admin/login  {admin_name, password}"""
    data = get_json()
    admin_name = require_str(data, 'admin_name', max_len=50, label='管理员账号')
    password = require_str(data, 'password', max_len=64, label='密码')
    admin = admin_service.login(admin_name, password)
    token = generate_token(admin['id'], ROLE_ADMIN)
    return success({
        'token': token,
        'admin_id': admin['id'],
        'admin_name': admin['admin_name'],
        'real_name': admin['real_name'],
        'avatar': admin['avatar'],
    }, '登录成功')


# =============================================================== 19. Dashboard
@bp.get('/dashboard')
@admin_required
def dashboard():
    """19. GET /api/admin/dashboard —— 全部为真实数据库聚合，无 Mock。"""
    return success(order_service.dashboard())


# =============================================================== 20. 学生用户
@bp.get('/user/list')
@admin_required
def user_list():
    """20. GET /api/admin/user/list  query: keyword / page / page_size（只读）"""
    keyword = clamp_keyword(request.args)
    page, page_size = parse_page(request.args, 10, 100)
    result = user_service.admin_list(keyword, page, page_size)
    return success({
        'list': result['list'],
        'total': result['total'],
        'page': page,
        'page_size': page_size,
        'pages': (int(result['total']) + page_size - 1) // page_size,
    })


# =============================================================== 21. 分类
@bp.post('/category/save')
@admin_required
def category_save():
    """21a. POST /api/admin/category/save  {id?, cat_name, sort, is_show}"""
    data = get_json()
    payload = {
        'id': optional_int(data, 'id', default=None, label='分类ID', min_val=1),
        'cat_name': require_str(data, 'cat_name', max_len=50, label='分类名称'),
        'sort': optional_int(data, 'sort', default=0, label='排序'),
        'is_show': require_bool_int(data, 'is_show', label='是否启用', default=1),
    }
    return success(food_service.category_save(payload), '保存成功')


@bp.post('/category/del')
@admin_required
def category_del():
    """21b. POST /api/admin/category/del  {id}"""
    data = get_json()
    cid = require_int(data, 'id', label='分类ID', min_val=1)
    food_service.category_delete(cid)
    return success(None, '删除成功')


@bp.get('/category/list')
@admin_required
def category_list():
    """补充 1. GET /api/admin/category/list —— 后台分类下拉/列表（含禁用项）"""
    return success({'list': food_service.category_list(only_show=False)})


# =============================================================== 22. 菜品
@bp.post('/food/save')
@admin_required
def food_save():
    """22a. POST /api/admin/food/save

    支持 application/json；也支持 multipart/form-data 直接携带菜品图片，
    字段名：food_img（兼容 file / image）。无需额外的菜品图片上传接口。
    """
    data = _body()
    payload = {
        'id': optional_int(data, 'id', default=None, label='菜品ID', min_val=1),
        'cat_id': require_int(data, 'cat_id', label='分类ID', min_val=1),
        'food_name': require_str(data, 'food_name', max_len=100, label='菜品名称'),
        'price': require_decimal(data, 'price', label='单价'),
        'stock': require_int(data, 'stock', label='库存', min_val=0),
        'description': optional_str(data, 'description', max_len=2000, label='描述'),
        'is_sale': require_bool_int(data, 'is_sale', label='是否上架', default=1),
    }
    file = _file_of(data, 'food_img', 'file', 'image')
    return success(food_service.food_save(payload, current_app.config['UPLOAD_FOLDER'], file),
                   '保存成功')


@bp.post('/food/del')
@admin_required
def food_del():
    """22b. POST /api/admin/food/del  {id}"""
    data = get_json()
    fid = require_int(data, 'id', label='菜品ID', min_val=1)
    food_service.food_delete(fid, current_app.config['UPLOAD_FOLDER'])
    return success(None, '删除成功')


@bp.get('/food/list')
@admin_required
def food_list():
    """补充 2. GET /api/admin/food/list

    query: cat_id / keyword / page / page_size（含下架菜品）
    """
    cat_id = optional_int(request.args, 'cat_id', default=None, label='分类ID', min_val=1)
    keyword = clamp_keyword(request.args)
    page, page_size = parse_page(request.args, 10, 100)
    result = food_service.food_list(cat_id=cat_id, keyword=keyword, page=page,
                                    page_size=page_size, admin=True)
    return success({
        'list': result['list'],
        'total': result['total'],
        'page': page,
        'page_size': page_size,
        'pages': (int(result['total']) + page_size - 1) // page_size,
    })


# =============================================================== 23~25. 订单
@bp.get('/order/list')
@admin_required
def order_list():
    """23. GET /api/admin/order/list

    query: order_status / keyword / start_date / end_date / page / page_size
    """
    status = optional_int(request.args, 'order_status', default=None,
                          label='订单状态', min_val=0, max_val=4)
    keyword = clamp_keyword(request.args)
    start_date = (request.args.get('start_date') or '').strip()[:10]
    end_date = (request.args.get('end_date') or '').strip()[:10]
    page, page_size = parse_page(request.args, 10, 100)
    result = order_service.admin_order_list(status, keyword, start_date, end_date, page, page_size)
    return success({
        'list': result['list'],
        'total': result['total'],
        'page': page,
        'page_size': page_size,
        'pages': (int(result['total']) + page_size - 1) // page_size,
        'status_text_map': order_service.STATUS_TEXT,
    })


@bp.get('/order/detail')
@admin_required
def order_detail():
    """补充 3. GET /api/admin/order/detail?order_id=1"""
    order_id = require_int(request.args, 'order_id', label='订单ID', min_val=1)
    return success(order_service.admin_order_detail(order_id))


@bp.post('/order/receive')
@admin_required
def order_receive():
    """24. POST /api/admin/order/receive  {order_id} —— 仅允许 1 → 2"""
    data = get_json()
    order_id = require_int(data, 'order_id', label='订单ID', min_val=1)
    return success(order_service.admin_transition(order_id, 1, 2), '接单成功')


@bp.post('/order/finish')
@admin_required
def order_finish():
    """25. POST /api/admin/order/finish  {order_id} —— 仅允许 2 → 3，并累加销量"""
    data = get_json()
    order_id = require_int(data, 'order_id', label='订单ID', min_val=1)
    return success(order_service.admin_transition(order_id, 2, 3, with_sales=True), '订单已完成')


# =============================================================== 26. 公告
@bp.post('/notice/save')
@admin_required
def notice_save():
    """26a. POST /api/admin/notice/save  {id?, title, content, is_show}"""
    data = get_json()
    payload = {
        'id': optional_int(data, 'id', default=None, label='公告ID', min_val=1),
        'title': require_str(data, 'title', max_len=200, label='公告标题'),
        'content': optional_str(data, 'content', max_len=5000, label='公告内容'),
        'is_show': require_bool_int(data, 'is_show', label='是否显示', default=1),
    }
    return success(notice_service.save(payload), '保存成功')


@bp.post('/notice/del')
@admin_required
def notice_del():
    """26b. POST /api/admin/notice/del  {id}"""
    data = get_json()
    nid = require_int(data, 'id', label='公告ID', min_val=1)
    notice_service.delete(nid)
    return success(None, '删除成功')


@bp.get('/notice/list')
@admin_required
def notice_list():
    """补充 4. GET /api/admin/notice/list  query: keyword / page / page_size"""
    keyword = clamp_keyword(request.args)
    page, page_size = parse_page(request.args, 10, 100)
    result = notice_service.admin_list(keyword, page, page_size)
    return success({
        'list': result['list'],
        'total': result['total'],
        'page': page,
        'page_size': page_size,
        'pages': (int(result['total']) + page_size - 1) // page_size,
    })


# =============================================================== 购物车查看
@bp.get('/cart/list')
@admin_required
def cart_list():
    """补充 5. GET /api/admin/cart/list —— 只读。

    query: keyword / page / page_size
    本版本不提供管理员修改学生购物车的接口（原需求未授权）。
    """
    keyword = clamp_keyword(request.args)
    page, page_size = parse_page(request.args, 10, 100)
    result = cart_service.admin_cart_list(keyword, page, page_size)
    return success({
        'list': result['list'],
        'total': result['total'],
        'page': page,
        'page_size': page_size,
        'pages': (int(result['total']) + page_size - 1) // page_size,
    })


# =============================================================== 27~28. 个人中心
@bp.get('/info')
@admin_required
def admin_info():
    """补充 6. GET /api/admin/info"""
    return success(admin_service.info(current_user_id()))


@bp.post('/upload_avatar')
@admin_required
def upload_avatar():
    """补充 7. POST /api/admin/upload_avatar （multipart/form-data，字段名 avatar）

    仅允许修改头像。admin_name 不提供修改入口（原需求未授权）。
    """
    file = request.files.get('avatar') or request.files.get('file')
    admin = admin_service.update_avatar(current_user_id(), file,
                                       current_app.config['UPLOAD_FOLDER'])
    return success({'avatar': admin['avatar']}, '头像上传成功')


@bp.post('/update_pwd')
@admin_required
def update_pwd():
    """27. POST /api/admin/update_pwd  {old_password, new_password}"""
    data = get_json()
    old_password = require_str(data, 'old_password', max_len=64, label='原密码')
    new_password = require_password(data, 'new_password', label='新密码')
    admin_service.update_password(current_user_id(), old_password, new_password)
    return success(None, '密码修改成功，请重新登录')


@bp.post('/logout')
@admin_required
def logout():
    """28. POST /api/admin/logout

    V1.0：数据库结构冻结（无 Token 黑名单表），服务端不做 JWT 吊销，
    由前端清除本地 admin_token。
    """
    return success(None, '已退出登录')
