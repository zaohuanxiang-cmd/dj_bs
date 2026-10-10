import socket

from django.db import IntegrityError
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from instances.crypto_utils import encrypt_password
from instances.models import Cluster, DbInstance, Department, InstanceDailyStat
from instances.serializers import (
    ClusterSerializer,
    DbInstanceSerializer,
    DepartmentSerializer,
    InstanceDailyStatSerializer,
)


# =====================================================================
# 部门 CRUD
# =====================================================================


class DepartmentCreateView(APIView):
    """
    新增部门接口

    继承 APIView，处理 POST 请求。
    前端需要提交：name（部门名称）、code（部门编码）。
    可选提交：remark（备注）。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        # 1. 从请求体中取出前端提交的数据
        #    request.data 是 DRF 封装好的字典，能自动兼容 JSON 和表单格式
        name = request.data.get('name')
        code = request.data.get('code')
        remark = request.data.get('remark', '')

        # 2. 校验必填项
        if not name or not code:
            return Response({'code': 0, 'msg': '部门名称、部门编码都不能为空'})

        # 3. 校验名称、编码是否已被占用
        if Department.objects.filter(name=name).exists():
            return Response({'code': 0, 'msg': '该部门名称已存在'})
        if Department.objects.filter(code=code).exists():
            return Response({'code': 0, 'msg': '该部门编码已存在'})

        # 4. 写入数据库
        dept = Department.objects.create(name=name, code=code, remark=remark or '')

        # 5. 用序列化器把对象转成 JSON 再返回给前端
        serializer = DepartmentSerializer(dept)
        return Response({'code': 1, 'msg': '新增成功', 'data': serializer.data})


class DepartmentListView(APIView):
    """
    部门列表查询接口

    继承 APIView，处理 GET 请求。
    支持按名称 / 编码模糊查询，并做分页。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        # 1. 先取出全部部门（查询集，此时还没真正查库）
        queryset = Department.objects.all()

        # 2. 从 URL 的查询参数里取出筛选条件
        #    例如 /api/departments/list/?name=研发&page=1
        name = request.query_params.get('name')
        code = request.query_params.get('code')

        # 3. 哪个条件传了，就加哪个过滤；__icontains 表示模糊查询（不区分大小写）
        if name:
            queryset = queryset.filter(name__icontains=name)
        if code:
            queryset = queryset.filter(code__icontains=code)

        # 4. 分页：URL 里取出来的都是字符串，要用 int() 转成数字
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        # 总条数一定要在切片之前统计，前端用它来算总页数
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        queryset = queryset[start:end]

        # 5. 多条数据必须加 many=True
        serializer = DepartmentSerializer(queryset, many=True)
        return Response({
            'code': 1,
            'msg': '查询成功',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'list': serializer.data,
            },
        })


class DepartmentUpdateView(APIView):
    """
    修改部门接口

    继承 APIView，处理 PUT 请求。
    前端必须提交 id；name / code / remark 传了就改，没传保持不变。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def put(self, request):
        # 1. 取出要修改的部门 id
        dept_id = request.data.get('id')
        if not dept_id:
            return Response({'code': 0, 'msg': '缺少部门 id'})

        # 2. filter().first() 找不到会返回 None，不会抛异常
        dept = Department.objects.filter(id=dept_id).first()
        if not dept:
            return Response({'code': 0, 'msg': '部门不存在'})

        name = request.data.get('name')
        code = request.data.get('code')
        remark = request.data.get('remark')

        # 3. 改名称 / 编码前，要排除自己，否则会把自己也算成“已占用”
        if name:
            if Department.objects.filter(name=name).exclude(id=dept_id).exists():
                return Response({'code': 0, 'msg': '该部门名称已存在'})
            dept.name = name
        if code:
            if Department.objects.filter(code=code).exclude(id=dept_id).exists():
                return Response({'code': 0, 'msg': '该部门编码已存在'})
            dept.code = code
        if remark is not None:
            dept.remark = remark

        # 4. 前面只是改了内存里的对象，save 才会真正写库
        dept.save()
        serializer = DepartmentSerializer(dept)
        return Response({'code': 1, 'msg': '修改成功', 'data': serializer.data})


class DepartmentDeleteView(APIView):
    """
    删除部门接口

    继承 APIView，处理 DELETE 请求。
    如果该部门下还有集群或实例（外键是 PROTECT），删除会失败并提示原因。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def delete(self, request):
        dept_id = request.data.get('id')
        if not dept_id:
            return Response({'code': 0, 'msg': '缺少部门 id'})

        dept = Department.objects.filter(id=dept_id).first()
        if not dept:
            return Response({'code': 0, 'msg': '部门不存在'})

        try:
            dept.delete()
        except IntegrityError:
            # 外键设置了 PROTECT，下面还有数据时数据库会拒绝删除
            return Response({'code': 0, 'msg': '该部门下仍有集群或实例，无法删除'})

        return Response({'code': 1, 'msg': '删除成功', 'data': {'id': dept_id}})


# =====================================================================
# 集群 CRUD
# =====================================================================


class ClusterCreateView(APIView):
    """
    新增集群接口

    前端需要提交：name（集群名称）、department（所属部门 id）。
    可选提交：remark。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        name = request.data.get('name')
        department_id = request.data.get('department')
        remark = request.data.get('remark', '')

        if not name or not department_id:
            return Response({'code': 0, 'msg': '集群名称、所属部门都不能为空'})

        # 先确认部门真实存在，避免写入一条指向空部门的脏数据
        department = Department.objects.filter(id=department_id).first()
        if not department:
            return Response({'code': 0, 'msg': '所属部门不存在'})

        # 同一个部门下集群名称不能重复（模型里 unique_together 也做了约束）
        if Cluster.objects.filter(department=department, name=name).exists():
            return Response({'code': 0, 'msg': '该部门下已存在同名集群'})

        cluster = Cluster.objects.create(
            name=name,
            department=department,
            remark=remark or '',
        )
        serializer = ClusterSerializer(cluster)
        return Response({'code': 1, 'msg': '新增成功', 'data': serializer.data})


class ClusterListView(APIView):
    """
    集群列表查询接口

    支持按名称模糊查询、按部门 id 精确过滤，并做分页。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        queryset = Cluster.objects.select_related('department').all()

        name = request.query_params.get('name')
        department_id = request.query_params.get('department')

        if name:
            queryset = queryset.filter(name__icontains=name)
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        queryset = queryset[start:end]

        serializer = ClusterSerializer(queryset, many=True)
        return Response({
            'code': 1,
            'msg': '查询成功',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'list': serializer.data,
            },
        })


class ClusterUpdateView(APIView):
    """
    修改集群接口

    前端必须提交 id；name / department / remark 传了就改。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def put(self, request):
        cluster_id = request.data.get('id')
        if not cluster_id:
            return Response({'code': 0, 'msg': '缺少集群 id'})

        cluster = Cluster.objects.filter(id=cluster_id).first()
        if not cluster:
            return Response({'code': 0, 'msg': '集群不存在'})

        name = request.data.get('name')
        department_id = request.data.get('department')
        remark = request.data.get('remark')

        # 如果传了新部门，先校验部门是否存在
        if department_id:
            department = Department.objects.filter(id=department_id).first()
            if not department:
                return Response({'code': 0, 'msg': '所属部门不存在'})
            cluster.department = department

        if name:
            cluster.name = name
        if remark is not None:
            cluster.remark = remark

        # 保存前再检查“同部门同名”是否冲突，exclude 掉自己
        if Cluster.objects.filter(
            department=cluster.department, name=cluster.name
        ).exclude(id=cluster_id).exists():
            return Response({'code': 0, 'msg': '该部门下已存在同名集群'})

        cluster.save()
        serializer = ClusterSerializer(cluster)
        return Response({'code': 1, 'msg': '修改成功', 'data': serializer.data})


class ClusterDeleteView(APIView):
    """
    删除集群接口

    集群下还有实例时不允许删除。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def delete(self, request):
        cluster_id = request.data.get('id')
        if not cluster_id:
            return Response({'code': 0, 'msg': '缺少集群 id'})

        cluster = Cluster.objects.filter(id=cluster_id).first()
        if not cluster:
            return Response({'code': 0, 'msg': '集群不存在'})

        try:
            cluster.delete()
        except IntegrityError:
            return Response({'code': 0, 'msg': '该集群下仍有实例，无法删除'})

        return Response({'code': 1, 'msg': '删除成功', 'data': {'id': cluster_id}})


# =====================================================================
# 数据库实例 CRUD
# =====================================================================


class InstanceCreateView(APIView):
    """
    新增数据库实例接口

    前端需要提交：name、host、port、cluster、username、password。
    department 可以不传：不传时自动使用集群所属部门。
    密码会在入库前加密，数据库里只保存密文。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        name = request.data.get('name')
        host = request.data.get('host')
        port = request.data.get('port', 3306)
        db_type = request.data.get('db_type', 'mysql')
        cluster_id = request.data.get('cluster')
        department_id = request.data.get('department')
        username = request.data.get('username')
        password = request.data.get('password')
        remark = request.data.get('remark', '')

        if not name or not host or not cluster_id or not username or not password:
            return Response({'code': 0, 'msg': '实例名称、主机、集群、账号、密码都不能为空'})

        cluster = Cluster.objects.filter(id=cluster_id).first()
        if not cluster:
            return Response({'code': 0, 'msg': '所属集群不存在'})

        # 部门：优先用前端传的；没传就跟集群走，避免部门和集群对不上
        if department_id:
            department = Department.objects.filter(id=department_id).first()
            if not department:
                return Response({'code': 0, 'msg': '所属部门不存在'})
        else:
            department = cluster.department

        if DbInstance.objects.filter(cluster=cluster, name=name).exists():
            return Response({'code': 0, 'msg': '该集群下已存在同名实例'})

        # 端口要转成整数，前端 JSON 里可能是字符串
        try:
            port = int(port)
        except (TypeError, ValueError):
            return Response({'code': 0, 'msg': '端口必须是数字'})

        inst = DbInstance.objects.create(
            name=name,
            host=host,
            port=port,
            db_type=db_type or 'mysql',
            department=department,
            cluster=cluster,
            username=username,
            # 关键：明文密码只在内存里停留这一瞬间，入库的是密文
            password_encrypted=encrypt_password(password),
            password_updated_at=timezone.now(),
            remark=remark or '',
        )
        serializer = DbInstanceSerializer(inst)
        return Response({'code': 1, 'msg': '新增成功', 'data': serializer.data})


class InstanceListView(APIView):
    """
    实例列表查询接口

    支持按名称 / 主机模糊查询，按部门、集群精确过滤，并做分页。
    返回结果不含密码明文，也不含密文。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        queryset = DbInstance.objects.select_related('department', 'cluster').all()

        name = request.query_params.get('name')
        host = request.query_params.get('host')
        department_id = request.query_params.get('department')
        cluster_id = request.query_params.get('cluster')

        if name:
            queryset = queryset.filter(name__icontains=name)
        if host:
            queryset = queryset.filter(host__icontains=host)
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        queryset = queryset[start:end]

        serializer = DbInstanceSerializer(queryset, many=True)
        return Response({
            'code': 1,
            'msg': '查询成功',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'list': serializer.data,
            },
        })


class InstanceUpdateView(APIView):
    """
    修改实例接口

    前端必须提交 id。
    如果传了 password，会重新加密后覆盖旧密文，并刷新 password_updated_at。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def put(self, request):
        inst_id = request.data.get('id')
        if not inst_id:
            return Response({'code': 0, 'msg': '缺少实例 id'})

        inst = DbInstance.objects.filter(id=inst_id).first()
        if not inst:
            return Response({'code': 0, 'msg': '实例不存在'})

        name = request.data.get('name')
        host = request.data.get('host')
        port = request.data.get('port')
        db_type = request.data.get('db_type')
        cluster_id = request.data.get('cluster')
        department_id = request.data.get('department')
        username = request.data.get('username')
        password = request.data.get('password')
        is_active = request.data.get('is_active')
        remark = request.data.get('remark')

        if cluster_id:
            cluster = Cluster.objects.filter(id=cluster_id).first()
            if not cluster:
                return Response({'code': 0, 'msg': '所属集群不存在'})
            inst.cluster = cluster
            # 换集群时，如果没单独传部门，部门跟着新集群走
            if not department_id:
                inst.department = cluster.department

        if department_id:
            department = Department.objects.filter(id=department_id).first()
            if not department:
                return Response({'code': 0, 'msg': '所属部门不存在'})
            inst.department = department

        if name:
            inst.name = name
        if host:
            inst.host = host
        if port is not None:
            try:
                inst.port = int(port)
            except (TypeError, ValueError):
                return Response({'code': 0, 'msg': '端口必须是数字'})
        if db_type:
            inst.db_type = db_type
        if username:
            inst.username = username
        if remark is not None:
            inst.remark = remark
        if is_active is not None:
            # 前端可能传 true/false，也可能传字符串 "true"
            inst.is_active = str(is_active).lower() in ('1', 'true', 'yes')

        # 只有真正传了新密码时才轮换，避免把旧密文覆盖成空
        if password:
            inst.password_encrypted = encrypt_password(password)
            inst.password_updated_at = timezone.now()

        if DbInstance.objects.filter(
            cluster=inst.cluster, name=inst.name
        ).exclude(id=inst_id).exists():
            return Response({'code': 0, 'msg': '该集群下已存在同名实例'})

        inst.save()
        serializer = DbInstanceSerializer(inst)
        return Response({'code': 1, 'msg': '修改成功', 'data': serializer.data})


class InstanceDeleteView(APIView):
    """
    删除实例接口
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def delete(self, request):
        inst_id = request.data.get('id')
        if not inst_id:
            return Response({'code': 0, 'msg': '缺少实例 id'})

        inst = DbInstance.objects.filter(id=inst_id).first()
        if not inst:
            return Response({'code': 0, 'msg': '实例不存在'})

        inst.delete()
        return Response({'code': 1, 'msg': '删除成功', 'data': {'id': inst_id}})


class InstanceProbeView(APIView):
    """
    主动探测 API：检测某个实例的 TCP 端口是否可达

    继承 APIView，处理 POST 请求。
    用法一：传 id，使用库里该实例的 host / port
    用法二：直接传 host + port，不依赖库里是否已有记录

    实现方式：用 socket 尝试连接目标 IP:端口，能在超时时间内连上就视为可达。
    这是“探测型 API”，不会去登录数据库，只检查网络层端口通不通。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        inst_id = request.data.get('id')
        host = request.data.get('host')
        port = request.data.get('port')
        # 超时时间（秒），防止探测卡死整个请求
        timeout = request.data.get('timeout', 3)

        # 传了 id 就以数据库记录为准
        if inst_id:
            inst = DbInstance.objects.filter(id=inst_id).first()
            if not inst:
                return Response({'code': 0, 'msg': '实例不存在'})
            host = inst.host
            port = inst.port

        if not host or not port:
            return Response({'code': 0, 'msg': '请提供实例 id，或同时提供 host 和 port'})

        try:
            port = int(port)
            timeout = float(timeout)
        except (TypeError, ValueError):
            return Response({'code': 0, 'msg': 'port / timeout 必须是数字'})

        reachable = False
        error_msg = ''
        try:
            # create_connection 会同时处理 IPv4/IPv6 解析和 TCP 三次握手
            # 连接成功说明端口是开着的；失败或超时说明不可达
            with socket.create_connection((host, port), timeout=timeout):
                reachable = True
        except OSError as exc:
            # 例如：连接被拒绝、超时、DNS 解析失败
            error_msg = str(exc)

        return Response({
            'code': 1,
            'msg': '探测完成',
            'data': {
                'host': host,
                'port': port,
                'reachable': reachable,          # True = TCP 可达
                'error': error_msg,              # 不可达时的原因，可达时为空
            },
        })


# =====================================================================
# 日统计查询
# =====================================================================


class StatListView(APIView):
    """
    实例数量日统计查询接口

    数据由 Celery 每天 00:00 写入。
    支持按日期、维度、部门、集群过滤。
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        queryset = InstanceDailyStat.objects.select_related('department', 'cluster').all()

        stat_date = request.query_params.get('stat_date')
        dimension = request.query_params.get('dimension')
        department_id = request.query_params.get('department')
        cluster_id = request.query_params.get('cluster')

        if stat_date:
            queryset = queryset.filter(stat_date=stat_date)
        if dimension:
            queryset = queryset.filter(dimension=dimension)
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        queryset = queryset[start:end]

        serializer = InstanceDailyStatSerializer(queryset, many=True)
        return Response({
            'code': 1,
            'msg': '查询成功',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'list': serializer.data,
            },
        })
