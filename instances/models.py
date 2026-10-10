from django.db import models


# Create your models here.


class Department(models.Model):
    """
    部门表

    企业内部组织维度，实例可以挂在某个部门下，
    每天 00:00 的统计任务会按部门汇总实例数量。
    """
    name = models.CharField(max_length=64, unique=True, verbose_name='部门名称')
    code = models.CharField(max_length=32, unique=True, verbose_name='部门编码')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '部门'
        verbose_name_plural = verbose_name
        ordering = ['-id']
        db_table = 't_department'


class Cluster(models.Model):
    """
    集群表

    一个部门下可以有多个数据库集群（例如：订单库主从集群、日志集群）。
    实例必须归属某个集群，统计任务也会按集群维度汇总数量。
    """
    name = models.CharField(max_length=64, verbose_name='集群名称')
    # PROTECT：部门下还有集群时不允许直接删部门，避免把关联数据弄乱
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='clusters',
        verbose_name='所属部门',
    )
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '集群'
        verbose_name_plural = verbose_name
        ordering = ['-id']
        db_table = 't_cluster'
        # 同一个部门下，集群名称不能重复
        unique_together = ('department', 'name')


class DbInstance(models.Model):
    """
    数据库实例表

    真正要管理的对象：一台（或一组）数据库的连接信息。
    账号密码属于敏感字段，password_encrypted 只存密文，明文不会入库。
    """
    name = models.CharField(max_length=64, verbose_name='实例名称')
    host = models.CharField(max_length=128, verbose_name='主机地址')
    port = models.IntegerField(default=3306, verbose_name='端口')
    db_type = models.CharField(max_length=32, default='mysql', verbose_name='数据库类型')
    # 实例同时记录部门和集群，方便按两个维度查询和统计
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='instances',
        verbose_name='所属部门',
    )
    cluster = models.ForeignKey(
        Cluster,
        on_delete=models.PROTECT,
        related_name='instances',
        verbose_name='所属集群',
    )
    username = models.CharField(max_length=64, verbose_name='登录账号')
    # 加密后的密码（Fernet 密文），列表接口不会把明文返回给前端
    password_encrypted = models.TextField(verbose_name='加密密码')
    # 最近一次轮换 / 修改密码的时间，便于核对 12 小时周期任务是否生效
    password_updated_at = models.DateTimeField(null=True, blank=True, verbose_name='密码更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return f'{self.name}({self.host}:{self.port})'

    class Meta:
        verbose_name = '数据库实例'
        verbose_name_plural = verbose_name
        ordering = ['-id']
        db_table = 't_db_instance'
        # 同一集群下，实例名称不能重复
        unique_together = ('cluster', 'name')


class InstanceDailyStat(models.Model):
    """
    实例数量日统计表

    每天 00:00 由 Celery 任务写入：
    - dimension=department     只按部门汇总（cluster 为空）
    - dimension=cluster        只按集群汇总
    - dimension=dept_cluster   部门 × 集群交叉汇总
    """
    DIMENSION_CHOICES = (
        ('department', '按部门'),
        ('cluster', '按集群'),
        ('dept_cluster', '部门×集群'),
    )

    stat_date = models.DateField(verbose_name='统计日期')
    dimension = models.CharField(max_length=32, choices=DIMENSION_CHOICES, verbose_name='统计维度')
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='daily_stats',
        verbose_name='部门',
    )
    cluster = models.ForeignKey(
        Cluster,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='daily_stats',
        verbose_name='集群',
    )
    instance_count = models.IntegerField(default=0, verbose_name='实例数量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='写入时间')

    def __str__(self):
        return f'{self.stat_date}-{self.dimension}-{self.instance_count}'

    class Meta:
        verbose_name = '实例日统计'
        verbose_name_plural = verbose_name
        ordering = ['-stat_date', '-id']
        db_table = 't_instance_daily_stat'
