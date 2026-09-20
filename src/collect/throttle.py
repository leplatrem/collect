import logging
import time
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.translation import gettext as _


logger = logging.getLogger(__name__)


def client_ip(request) -> str:
    """
    Address of the client, as seen through the trusted reverse proxies.
    """
    remote_addr = request.META.get("REMOTE_ADDR", "")
    num_proxies = settings.THROTTLE_NUM_PROXIES
    if num_proxies <= 0:
        return remote_addr

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    addresses = [a.strip() for a in forwarded.split(",") if a.strip()]
    if len(addresses) < num_proxies:
        # Fewer hops than configured: the request did not come through the
        # expected proxies, the header cannot be trusted.
        return remote_addr
    return addresses[-num_proxies]


def client_key(request) -> str:
    """
    Identify the caller: by user when logged in, by IP otherwise.
    """
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return f"ip:{client_ip(request)}"


def parse_rate(rate: str) -> tuple[int, int]:
    """Turn a "<requests>/<seconds>" rate into a (limit, period) pair."""
    limit, _, period = rate.partition("/")
    return int(limit), int(period)


def is_throttled(request, scope: str, rate: str) -> bool:
    """
    Count this request, and tell whether the caller went over the limit.
    """
    limit, period = parse_rate(rate)
    if limit <= 0 or period <= 0:  # Disabled.
        return False

    window = int(time.time()) // period
    key = f"throttle:{scope}:{window}:{client_key(request)}"
    try:
        count = cache.incr(key)
    except ValueError:
        # First request of this window.
        cache.set(key, 1, period)
        count = 1
    return count > limit


def throttle(scope: str, rate_setting: str, methods=("POST",)):
    """
    Refuse requests from a caller that sends too many of them.

    `rate_setting` is the *name* of the setting holding the rate, so that it
    stays configurable without reloading the URLconf.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method in methods:
                rate = getattr(settings, rate_setting)
                if is_throttled(request, scope, rate):
                    logger.warning(
                        "Throttled %s request on %s from %s",
                        request.method,
                        request.path,
                        client_key(request),
                    )
                    response = HttpResponse(_("Too Many Requests"), status=429)
                    _limit, period = parse_rate(rate)
                    response["Retry-After"] = str(period)
                    return response
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
