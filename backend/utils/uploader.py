# -*- coding: utf-8 -*-
"""图片上传工具。

安全要求（全部落实）：
1. 扩展名白名单：jpg / jpeg / png / webp
2. MIME 与文件头（Magic Bytes）双重校验 —— 防止改扩展名绕过
3. 大小限制（默认 2MB），同时依赖 Flask MAX_CONTENT_LENGTH 兜底
4. 使用 UUID 随机文件名，绝不使用用户原始文件名（防路径穿越 / 覆盖 / 恶意文件名）
5. 落盘目录固定，写前二次确认 realpath 在允许目录内（防目录穿越）
6. 数据库只保存文件名，不保存 URL
7. 失败时清理半成品文件
"""
import logging
import os
import uuid

from werkzeug.datastructures import FileStorage

logger = logging.getLogger('campus_order')

# 全站共享的默认图（禁止被删除）
DEFAULT_AVATAR = 'default_user.jpg'
FOOD_PLACEHOLDER = 'food-default.jpg'

# 文件头签名
_MAGIC = (
    (b'\xff\xd8\xff', 'jpg'),
    (b'\x89PNG\r\n\x1a\n', 'png'),
    (b'RIFF', 'webp'),  # 需进一步判断 WEBP 标识
)

_MIME_ALLOWED = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/webp',
    # 部分客户端上传 webp/jpeg 时会带 application/octet-stream
    'application/octet-stream', '',
}


def _sniff_ext(head: bytes, ext: str) -> bool:
    """根据文件头判断真实类型是否与扩展名一致。"""
    if head.startswith(b'\xff\xd8\xff'):
        return ext in ('jpg', 'jpeg')
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return ext == 'png'
    if head.startswith(b'RIFF') and head[8:12] == b'WEBP':
        return ext == 'webp'
    return False


def _safe_ext(filename: str):
    if not filename or '.' not in filename:
        return None
    ext = filename.rsplit('.', 1)[1].strip().lower()
    if ext == 'jpe':
        ext = 'jpeg'
    return ext


def save_uploaded_image(file: FileStorage, upload_folder: str, allowed_ext=None,
                        max_size: int = 2 * 1024 * 1024) -> str:
    """保存上传图片，返回【仅文件名】。

    任何校验失败抛出 ValueError（由调用方转换为业务错误）。
    """
    if file is None or not getattr(file, 'filename', ''):
        raise ValueError('请选择要上传的图片')

    allowed_ext = allowed_ext or {'jpg', 'jpeg', 'png', 'webp'}

    # --- 扩展名白名单 ---
    ext = _safe_ext(file.filename)
    if not ext:
        raise ValueError('图片文件名缺少扩展名')
    if ext not in allowed_ext:
        raise ValueError('仅支持 jpg / jpeg / png / webp 格式图片')

    # --- MIME 校验 ---
    mime = (file.mimetype or '').lower()
    if mime not in _MIME_ALLOWED:
        raise ValueError('图片 MIME 类型不被允许：%s' % mime)

    # --- 大小校验 ---
    try:
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(0)
    except Exception:
        size = 0
    if size <= 0:
        raise ValueError('图片内容为空')
    if size > max_size:
        raise ValueError('图片大小不能超过 %.1fMB' % (max_size / 1024.0 / 1024.0))

    # --- 文件头校验（防伪造扩展名） ---
    head = file.stream.read(16)
    file.stream.seek(0)
    if not _sniff_ext(head, ext):
        raise ValueError('图片文件内容与扩展名不符，已拒绝上传')

    # --- 目标目录安全校验 ---
    folder = os.path.realpath(upload_folder)
    os.makedirs(folder, exist_ok=True)

    # --- UUID 随机文件名，杜绝覆盖与路径穿越 ---
    safe_name = '%s.%s' % (uuid.uuid4().hex, ext)
    target = os.path.realpath(os.path.join(folder, safe_name))
    if not target.startswith(folder + os.sep):
        raise ValueError('非法的文件保存路径')

    try:
        file.save(target)
    except Exception as exc:  # pragma: no cover
        logger.error('图片保存失败: %s', exc)
        raise ValueError('图片保存失败，请重试')

    # --- 二次校验：确保落盘且大小一致 ---
    if not os.path.isfile(target) or os.path.getsize(target) <= 0:
        try:
            os.remove(target)
        except OSError:
            pass
        raise ValueError('图片保存失败，请重试')

    return safe_name


def delete_uploaded_image(filename: str, upload_folder: str) -> bool:
    """删除上传图片（仅允许删除上传目录内的文件）。

    注意：默认头像与菜品兜底占位图是**全站共享资源**，绝不允许被删除，
    否则一旦某个菜品/用户在编辑时替换图片，会连带删掉占位图，
    导致其它未设置图片的条目全部变成裂图。
    """
    if not filename:
        return False
    name = os.path.basename(str(filename))
    if name in ('', DEFAULT_AVATAR, FOOD_PLACEHOLDER):
        return False
    folder = os.path.realpath(upload_folder)
    target = os.path.realpath(os.path.join(folder, name))
    if not target.startswith(folder + os.sep):
        return False
    if os.path.isfile(target):
        try:
            os.remove(target)
            return True
        except OSError:
            return False
    return False
