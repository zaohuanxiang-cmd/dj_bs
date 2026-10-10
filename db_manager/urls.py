"""
URL configuration for db_manager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # 业务接口统一挂在 /api/ 下，便于前端和网关识别
    path('api/', include('instances.urls')),
]

# 开发环境下，让 Django 帮我们提供用户上传的媒体文件的访问
# 注意：这种方式只适用于开发调试，生产环境应交给 Nginx 等服务器处理
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
