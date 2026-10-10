# 启动 Django 时一并加载 Celery 应用，保证 @shared_task 能找到 broker
from .celery import app as celery_app

__all__ = ('celery_app',)
