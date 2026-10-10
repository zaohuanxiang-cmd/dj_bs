from django.contrib import admin

from instances.models import Department, Cluster, DbInstance, InstanceDailyStat


# Register your models here.


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'created_at']
    search_fields = ['name', 'code']


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'department', 'created_at']
    search_fields = ['name']
    list_filter = ['department']


@admin.register(DbInstance)
class DbInstanceAdmin(admin.ModelAdmin):
    # 后台列表不要展示密文字段，避免误把敏感信息拷出去
    list_display = [
        'id', 'name', 'host', 'port', 'department', 'cluster',
        'username', 'password_updated_at', 'is_active',
    ]
    search_fields = ['name', 'host', 'username']
    list_filter = ['department', 'cluster', 'is_active', 'db_type']


@admin.register(InstanceDailyStat)
class InstanceDailyStatAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'stat_date', 'dimension', 'department', 'cluster', 'instance_count',
    ]
    list_filter = ['stat_date', 'dimension']
