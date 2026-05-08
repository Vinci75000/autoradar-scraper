"""Sentry initialization for autoradar-scraper.

Usage at the top of any entry point:
    from sentry_init import init_sentry
    init_sentry()

Reads SENTRY_DSN_SCRAPER from environment. If absent, this is a no-op
(useful for dev/test). Safe to call multiple times. Skips during pytest.
"""

import os

_initialized = False


def init_sentry() -> bool:
    """Initialize Sentry SDK if SENTRY_DSN_SCRAPER is set.

    Returns True if Sentry was initialized, False if no-op.
    """
    global _initialized
    if _initialized:
        return True

    # Skip during pytest runs to avoid polluting Sentry with test events
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False

    dsn = os.environ.get("SENTRY_DSN_SCRAPER")
    if not dsn:
        return False

    import sentry_sdk

    environment = os.environ.get("SENTRY_ENVIRONMENT", "production")
    release = os.environ.get("GITHUB_SHA", "local")
    component = os.environ.get("SENTRY_COMPONENT", "scraper")

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=0.0,
        send_default_pii=False,
        attach_stacktrace=True,
    )
    sentry_sdk.set_tag("component", component)

    _initialized = True
    return True
