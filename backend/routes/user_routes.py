# -*- coding: utf-8 -*-
"""学生用户相关接口（8 组原始接口中的 1~7）。"""
from flask import Blueprint, current_app, request

from services import user_service
from utils.auth import current_user_id, generate_token, ROLE_STUDENT, student_required
from utils.response import success
from utils.validators import (get_json, optional_str, require_password, require_phone,
                              require_str)

bp = Blueprint('user', __name__, url_prefix='/api/user')


@bp.post('/register')
def register():
    """1. POST /api/user/register"""
    data = get_json()
    nickname = require_str(data, 'nickname', max_len=50, label='昵称')
    phone = require_phone(data)
    password = require_password(data)
    student_no = optional_str(data, 'student_no', max_len=30, label='学号')
    dormitory = optional_str(data, 'dormitory', max_len=100, label='宿舍')
    user = user_service.register({
        'nickname': nickname, 'phone': phone, 'password': password,
        'student_no': student_no, 'dormitory': dormitory,
    })
    return success(user, '注册成功')


@bp.post('/login')
def login():
    """2. POST /api/user/login"""
    data = get_json()
    phone = require_phone(data)
    password = require_str(data, 'password', max_len=64, label='密码')
    user = user_service.login(phone, password)
    token = generate_token(user['id'], ROLE_STUDENT)
    return success({
        'token': token,
        'user_id': user['id'],
        'nickname': user['nickname'],
        'phone': user['phone'],
        'avatar': user['avatar'],
        'student_no': user['student_no'],
        'dormitory': user['dormitory'],
    }, '登录成功')


@bp.get('/info')
@student_required
def info():
    """3. GET /api/user/info"""
    uid = current_user_id()
    user = user_service.get_by_id(uid)
    return success({k: user.get(k) for k in
                    ('id', 'phone', 'nickname', 'avatar', 'student_no', 'dormitory', 'created_at')})


@bp.post('/update_info')
@student_required
def update_info():
    """4. POST /api/user/update_info"""
    data = get_json()
    nickname = require_str(data, 'nickname', max_len=50, label='昵称')
    student_no = optional_str(data, 'student_no', max_len=30, label='学号')
    dormitory = optional_str(data, 'dormitory', max_len=100, label='宿舍')
    return success(user_service.update_info(current_user_id(), nickname, student_no, dormitory),
                   '修改成功')


@bp.post('/update_pwd')
@student_required
def update_pwd():
    """5. POST /api/user/update_pwd"""
    data = get_json()
    old_password = require_str(data, 'old_password', max_len=64, label='原密码')
    new_password = require_password(data, 'new_password', label='新密码')
    user_service.update_password(current_user_id(), old_password, new_password)
    return success(None, '密码修改成功，请重新登录')


@bp.post('/upload_avatar')
@student_required
def upload_avatar():
    """6. POST /api/user/upload_avatar （multipart/form-data，字段名 avatar）"""
    file = request.files.get('avatar') or request.files.get('file')
    user = user_service.update_avatar(current_user_id(), file,
                                      current_app.config['UPLOAD_FOLDER'])
    return success({'avatar': user['avatar']}, '头像上传成功')


@bp.post('/logout')
@student_required
def logout():
    """7. POST /api/user/logout

    V1.0 说明：数据库结构冻结（无 Token 黑名单表），logout 为客户端行为，
    后端仅返回成功，由前端清除本地 student_token。
    详见 README「登出说明」。
    """
    return success(None, '已退出登录')
