"""
请求耗时统计中间件

Django 中间件会包在视图外面：请求进来先经过这里，视图处理完再回到这里。
我们在进入视图前记下开始时间，出来后再算差值，就能得到本次请求耗了多久。
"""
import logging
import time

# 使用项目统一的 logger 名称，日志会同时打到控制台和 logs/ 目录
logger = logging.getLogger('db_manager')


class RequestTimingMiddleware:
    """
    统计每个请求的处理耗时。

    做了两件事：
    1. 把耗时（毫秒）写进响应头 X-Request-Duration-ms，方便前端或 Postman 直接看到
    2. 把方法、路径、状态码、耗时写进日志，方便排查慢接口
    """

    def __init__(self, get_response):
        # Django 启动时调用一次，get_response 指向“下一个中间件 / 最终视图”
        self.get_response = get_response

    def __call__(self, request):
        # 1. 请求刚进来时记下当前时间（单位：秒，带小数）
        start = time.perf_counter()

        # 2. 把请求交给后面的中间件和视图去处理，拿到响应对象
        response = self.get_response(request)

        # 3. 视图处理完后，再记一次时间，相减得到耗时
        #    乘 1000 转成毫秒，保留 2 位小数，读起来更直观
        duration_ms = (time.perf_counter() - start) * 1000

        # 4. 把耗时写进响应头（自定义响应头一般用 X- 开头）
        response['X-Request-Duration-ms'] = f'{duration_ms:.2f}'

        # 5. 写一条 INFO 日志：方法、路径、状态码、耗时
        #    例如：[GET] /api/departments/list/ -> 200  12.35ms
        logger.info(
            '[%s] %s -> %s  %.2fms',
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )

        return response
