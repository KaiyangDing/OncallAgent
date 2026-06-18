"""限流器:基于 slowapi,按客户端 IP 限制请求频率。"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# 全局限流器,按客户端 IP 计数(内存存储,单机适用)
limiter = Limiter(key_func=get_remote_address)
