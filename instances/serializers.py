from rest_framework import serializers

from instances.models import Department, Cluster, DbInstance, InstanceDailyStat


class DepartmentSerializer(serializers.ModelSerializer):
    """
    部门序列化器

    ModelSerializer 会根据模型自动生成字段，
    我们只需要在 Meta 里指定模型和要返回的字段即可。
    作用：把 Department 对象（或查询集）转换成可以返回给前端的 JSON 数据。
    """

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'remark', 'created_at', 'updated_at']


class ClusterSerializer(serializers.ModelSerializer):
    """
    集群序列化器

    department 返回外键 id；额外提供 department_name，列表页不用再查一次部门。
    """
    # source='department.name' 表示从这个外键对象上取 name 字段
    # read_only=True 表示这个字段只用于输出，前端提交时不用传
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Cluster
        fields = [
            'id', 'name', 'department', 'department_name',
            'remark', 'created_at', 'updated_at',
        ]


class DbInstanceSerializer(serializers.ModelSerializer):
    """
    数据库实例序列化器

    注意：绝不要把 password_encrypted 或明文密码返回给前端。
    只返回账号、密码更新时间等非敏感信息。
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    cluster_name = serializers.CharField(source='cluster.name', read_only=True)

    class Meta:
        model = DbInstance
        fields = [
            'id', 'name', 'host', 'port', 'db_type',
            'department', 'department_name',
            'cluster', 'cluster_name',
            'username', 'password_updated_at', 'is_active',
            'remark', 'created_at', 'updated_at',
        ]


class InstanceDailyStatSerializer(serializers.ModelSerializer):
    """
    日统计序列化器
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    cluster_name = serializers.CharField(source='cluster.name', read_only=True)

    class Meta:
        model = InstanceDailyStat
        fields = [
            'id', 'stat_date', 'dimension',
            'department', 'department_name',
            'cluster', 'cluster_name',
            'instance_count', 'created_at',
        ]
