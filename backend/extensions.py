# -*- coding: utf-8 -*-
"""扩展对象统一出口（避免循环导入）。"""
from utils.db import db  # noqa: F401

__all__ = ['db']
