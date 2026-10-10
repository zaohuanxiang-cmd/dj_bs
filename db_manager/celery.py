"""
Celery 应用入口

worker 负责真正执行任务，beat 负责按时间表把任务丢给 worker。
启动命令见项目 README。
"""
import os

from celery import Celery
from celery.schedules import crontab

# 让 Celery 使用 Django 的配置文件
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'db_manager.settings')

# 创建 Celery 实例，名字一般和项目名保持一致
app = Celery('db_manager')

# 从 Django settings 里读取以 CELERY_ 开头的配置
# 例如 CELERY_BROKER_URL 会变成 broker_url
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各个 app 下的 tasks.py
app.autodiscover_tasks()

# 时区和 Django 保持一致（东八区）
app.conf.timezone = 'Asia/Shanghai'
app.conf.enable_utc = False

# ==================== 周期任务时间表（Celery Beat）====================
# 不依赖 django-celery-beat 数据库，直接写在代码里，部署更简单
app.conf.beat_schedule = {
    # 每隔 12 小时轮换一次所有实例的账号密码，并加密落库
    # crontab(minute=0, hour='*/12') 表示每天 00:00 和 12:00 各执行一次
    'rotate-instance-passwords-every-12-hours': {
        'task': 'instances.tasks.rotate_instance_passwords',
        'schedule': crontab(minute=0, hour='*/12'),
    },
    # 每天 00:00 按部门和集群维度统计实例数量，写入统计表
    'stat-instances-daily-at-midnight': {
        'task': 'instances.tasks.stat_instances_daily',
        'schedule': crontab(minute=0, hour=0),
    },
}
