# -*- coding: utf-8 -*-
"""APScheduler 定时任务：15 分钟未支付订单自动取消 + 恢复库存。

设计要点：
- 纯数据库驱动：每次扫描都重新从数据库读取超时订单，进程重启后依旧生效。
- 平台只启动一个实例，避免多进程重复执行（见 app.py）。
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger('campus_order')

_scheduler = None


def _job(app):
    """定时任务体。"""
    with app.app_context():
        try:
            from services.order_service import auto_cancel_expired_orders
            count = auto_cancel_expired_orders()
            if count:
                logger.info('[scheduler] 自动取消超时未支付订单 %d 笔', count)
        except Exception as exc:  # 任务异常不得导致调度器退出
            logger.error('[scheduler] 执行超时取消任务失败: %s', exc, exc_info=True)


def init_scheduler(app):
    """初始化并启动调度器。

    通过 app.config['ENABLE_SCHEDULER'] 控制（pytest 下自动关闭）。
    """
    global _scheduler
    if not app.config.get('ENABLE_SCHEDULER', True):
        logger.info('[scheduler] 已按配置关闭')
        return None

    interval = int(app.config.get('SCHEDULER_SCAN_INTERVAL', 60))
    timeout_min = int(app.config.get('ORDER_TIMEOUT_MINUTES', 15))

    _scheduler = BackgroundScheduler(timezone='Asia/Shanghai', daemon=True)
    _scheduler.add_job(
        func=lambda: _job(app),
        trigger='interval',
        seconds=interval,
        id='auto_cancel_expired_orders',
        name='超时未支付订单自动取消（%d分钟）' % timeout_min,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    # 启动后立即执行一次，避免重启后必须等到下一个扫描周期
    _job(app)
    logger.info('[scheduler] 已启动：每 %ds 扫描一次，超时阈值 %d 分钟', interval, timeout_min)
    return _scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
