# -*- coding: utf-8 -*-
"""定时任务包。"""
from scheduler.order_scheduler import init_scheduler, shutdown_scheduler  # noqa: F401

__all__ = ['init_scheduler', 'shutdown_scheduler']
