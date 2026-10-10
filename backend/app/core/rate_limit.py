"""
Rate limiting configuration for EKIA using slowapi.
Provides keying by client IP and customizable route decorators.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
)
