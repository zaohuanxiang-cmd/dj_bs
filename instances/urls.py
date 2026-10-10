from django.urls import path

from instances.views import (
    DepartmentCreateView, DepartmentListView, DepartmentUpdateView, DepartmentDeleteView,
    ClusterCreateView, ClusterListView, ClusterUpdateView, ClusterDeleteView,
    InstanceCreateView, InstanceListView, InstanceUpdateView, InstanceDeleteView,
    InstanceProbeView, StatListView,
)

# 这里配置 instances 应用自己的路由
# 每条 path 把一个 URL 地址映射到一个视图
urlpatterns = [
    # ---------- 部门 CRUD ----------
    path('departments/create/', DepartmentCreateView.as_view(), name='department_create'),
    path('departments/list/', DepartmentListView.as_view(), name='department_list'),
    path('departments/update/', DepartmentUpdateView.as_view(), name='department_update'),
    path('departments/delete/', DepartmentDeleteView.as_view(), name='department_delete'),

    # ---------- 集群 CRUD ----------
    path('clusters/create/', ClusterCreateView.as_view(), name='cluster_create'),
    path('clusters/list/', ClusterListView.as_view(), name='cluster_list'),
    path('clusters/update/', ClusterUpdateView.as_view(), name='cluster_update'),
    path('clusters/delete/', ClusterDeleteView.as_view(), name='cluster_delete'),

    # ---------- 实例 CRUD + TCP 探测 ----------
    path('instances/create/', InstanceCreateView.as_view(), name='instance_create'),
    path('instances/list/', InstanceListView.as_view(), name='instance_list'),
    path('instances/update/', InstanceUpdateView.as_view(), name='instance_update'),
    path('instances/delete/', InstanceDeleteView.as_view(), name='instance_delete'),
    # 主动探测某个实例的 TCP 端口是否可达
    path('instances/probe/', InstanceProbeView.as_view(), name='instance_probe'),

    # ---------- 日统计查询 ----------
    path('stats/list/', StatListView.as_view(), name='stat_list'),
]
