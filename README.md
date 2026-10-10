# 数据库实例管理系统（Django 笔试题方案 A）

企业内部数据库实例管理平台，支持部门 / 集群 / 实例三级模型管理，提供 TCP 端口主动探测、密码自动轮换加密、每日多维统计和请求耗时监控等能力。

---

## 技术栈

| 类别 | 技术 | 版本 |
| --- | --- | --- |
| 语言 | Python | 3.12 |
| Web 框架 | Django | 6.0.6 |
| API 框架 | Django REST Framework | 3.17.1 |
| 认证 | djangorestframework-simplejwt | 5.5.1 |
| 异步任务 | Celery | 5.5.3 |
| 数据库 | MySQL（PyMySQL 驱动） | 5.7+ / 8.0 |
| 缓存 / 消息队列 | Redis | 6.0+ |
| 加密 | cryptography (Fernet) | 46.0.2 |
| 跨域 | django-cors-headers | 4.9.0 |

---

## 环境要求

- Python 3.10+（开发使用 3.12.9）
- MySQL 5.7 或 8.0，需提前创建数据库 `my_db_manager`
- Redis 6.0+，默认端口 6380（缓存用 1 号库，Celery broker 用 2 号库，result 用 3 号库）

---

## 快速开始

### 1. 克隆项目并进入目录

```bash
git clone <仓库地址>
cd dj_bs
```

### 2. 创建并激活虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置密钥和数据库

复制环境变量模板，在项目根目录生成 `.env`，并填入本机的 `DJANGO_SECRET_KEY` 和 `DB_PASSWORD`。`.env` 已加入忽略列表，不会提交到仓库。

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

```env
DJANGO_SECRET_KEY=替换成一段随机密钥
DB_NAME=my_db_manager
DB_USER=root
DB_PASSWORD=替换成数据库密码
DB_HOST=127.0.0.1
DB_PORT=3306
```

`db_manager/settings.py` 启动时读取这些变量。`DJANGO_SECRET_KEY` 同时用于会话和实例密码加密，更换后已入库的密文将无法解密。数据库 `my_db_manager` 需要提前在 MySQL 中创建。

同时确认 Redis 地址（默认 `127.0.0.1:6380`，写在 `db_manager/settings.py`）：

```python
CACHES = {'default': {'LOCATION': 'redis://127.0.0.1:6380/1'}}
CELERY_BROKER_URL = 'redis://127.0.0.1:6380/2'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6380/3'
```

### 5. 执行数据库迁移

```bash
python manage.py migrate
```

### 6. 创建管理员账号（可选，用于登录 admin 后台）

```bash
python manage.py createsuperuser
```

### 7. 启动开发服务器

```bash
python manage.py runserver 0.0.0.0:8000
```

服务启动后访问：
- API 根路径：`http://127.0.0.1:8000/api/`
- Admin 后台：`http://127.0.0.1:8000/admin/`

---

## 启动 Celery（异步任务 + 周期任务）

需要同时启动 **worker**（执行任务）和 **beat**（定时调度），各开一个终端窗口。

### 终端 1：启动 Celery Worker

```bash
# Windows
celery -A db_manager worker --loglevel=info --pool=solo

# macOS / Linux
celery -A db_manager worker --loglevel=info
```

> Windows 下必须加 `--pool=solo`，否则 worker 无法正常执行任务。

### 终端 2：启动 Celery Beat（定时调度器）

```bash
celery -A db_manager beat --loglevel=info
```

### 周期任务说明

| 任务 | 调度时间 | 功能 |
| --- | --- | --- |
| `rotate_instance_passwords` | 每天 00:00 / 12:00（每 12 小时） | 随机轮换所有实例密码，Fernet 加密落库 |
| `stat_instances_daily` | 每天 00:00 | 按部门 / 集群 / 部门×集群三维度统计实例数量并写入统计表 |

---

## API 接口列表

所有业务接口统一挂在 `/api/` 前缀下。

### 部门管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/departments/create/` | 新增部门 |
| GET | `/api/departments/list/` | 部门列表（支持 name/code 模糊查询、分页） |
| PUT | `/api/departments/update/` | 修改部门 |
| DELETE | `/api/departments/delete/` | 删除部门（下有集群/实例时拒绝） |

### 集群管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/clusters/create/` | 新增集群 |
| GET | `/api/clusters/list/` | 集群列表（支持名称模糊、部门过滤、分页） |
| PUT | `/api/clusters/update/` | 修改集群 |
| DELETE | `/api/clusters/delete/` | 删除集群（下有实例时拒绝） |

### 数据库实例管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/instances/create/` | 新增实例（密码自动加密入库） |
| GET | `/api/instances/list/` | 实例列表（支持名称/主机模糊、部门/集群过滤、分页） |
| PUT | `/api/instances/update/` | 修改实例（传 password 时重新加密并刷新更新时间） |
| DELETE | `/api/instances/delete/` | 删除实例 |
| POST | `/api/instances/probe/` | TCP 端口探测（传 id 或 host+port） |

### 统计查询

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/stats/list/` | 日统计列表（支持日期/维度/部门/集群过滤、分页） |

### 通用分页参数

所有 list 接口支持：
- `page`：页码，默认 1
- `page_size`：每页条数，默认 10

### 响应格式

```json
{
  "code": 1,
  "msg": "操作成功",
  "data": { ... }
}
```

`code=1` 表示成功，`code=0` 表示失败，失败原因见 `msg`。

---

## 项目结构

```
dj_bs/
├── db_manager/              # 项目配置目录
│   ├── __init__.py          # 加载 Celery app
│   ├── celery.py            # Celery 配置 + 周期任务时间表
│   ├── settings.py          # Django 全局配置
│   ├── urls.py              # 根路由（/api/ + /admin/）
│   ├── asgi.py              # ASGI 入口
│   └── wsgi.py              # WSGI 入口
├── instances/               # 业务应用：实例管理
│   ├── migrations/          # 数据库迁移
│   │   └── 0001_initial.py  # 初始建表迁移
│   ├── admin.py             # Admin 后台注册
│   ├── apps.py              # 应用配置
│   ├── crypto_utils.py      # Fernet 加解密工具
│   ├── models.py            # 数据模型（部门/集群/实例/日统计）
│   ├── serializers.py       # DRF 序列化器
│   ├── tasks.py             # Celery 异步/周期任务
│   ├── tests.py             # 单元测试
│   ├── urls.py              # 业务路由
│   └── views.py             # 视图（CRUD + TCP探测 + 统计查询）
├── middleware/              # 自定义中间件
│   └── timing.py            # 请求耗时统计中间件
├── static/                  # 静态文件
├── templates/               # 模板文件
├── logs/                    # 日志目录（自动创建）
├── manage.py                # Django 命令行入口
├── requirements.txt         # Python 依赖清单
└── README.md                # 本文件
```

---

## 核心设计说明

### 敏感字段加密

实例密码使用 **Fernet 对称加密**，密钥由 Django `SECRET_KEY` 经 SHA256 派生。明文密码仅在内存中短暂存在，数据库只存密文；列表接口和 Admin 后台均不返回密码字段。

### 外键删除保护

`Cluster` 和 `DbInstance` 对 `Department` / `Cluster` 的外键均使用 `on_delete=PROTECT`，删除父对象时若存在子数据，数据库会拒绝删除并返回友好提示。

### 请求耗时监控

`RequestTimingMiddleware` 对每个请求计时，将耗时（毫秒）写入响应头 `X-Request-Duration-ms`，同时记录到日志 `logs/db_manager.log`。

### 日统计幂等性

每日统计任务执行时先删除当天已有记录再重新写入，支持手动补跑，不会产生重复数据。

---

## 注意事项

1. **开发环境配置**：当前 `DEBUG=True`、`ALLOWED_HOSTS=['*']`、`CORS_ALLOW_ALL_ORIGINS=True`，仅适用于开发调试，生产部署前必须修改。
2. **SECRET_KEY**：写在本机 `.env` 的 `DJANGO_SECRET_KEY` 中，不要提交到仓库。生产环境请使用独立的随机密钥。
3. **密码轮换范围**：轮换任务仅更新本系统记录的密码密文，不会连接真实数据库执行 `ALTER USER`。
4. **Redis 端口**：项目默认使用 6380 端口（非默认 6379），请确认 Redis 实际监听端口。
5. **Windows Celery**：Windows 下启动 worker 必须加 `--pool=solo` 参数。
