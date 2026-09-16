import logging
import os

import fastapi
import httpx

logger = logging.getLogger(__name__)

SESSION_EXPIRED_DETAIL = 'Your session has expired or is invalid. Please sign in again.'
DEFAULT_USER_SERVICE_URL = 'https://users.kpndataregistry.org'
DEFAULT_USER_GROUP = 'gwas-ce'


def user_service_url() -> str:
    return os.getenv('USER_SERVICE_URL', DEFAULT_USER_SERVICE_URL).rstrip('/')


def user_group() -> str:
    return os.getenv('USER_GROUP', DEFAULT_USER_GROUP)


def log_user_service_config(log: logging.Logger = logger) -> None:
    """Log which user service and group this process verifies tokens against.

    The group must match the one the frontend was built with
    (NUXT_PUBLIC_USER_GROUP); a mismatch makes every verify fail with
    'Token was not issued for group'. Surfacing the resolved values in the
    startup log is the cheapest way to catch that.
    """
    group = user_group()
    url = user_service_url()
    log.info('User service: %s, verify group: %s', url, group)
    if 'USER_GROUP' not in os.environ:
        log.warning('USER_GROUP is not set; defaulting to %r', DEFAULT_USER_GROUP)


def auth_failure_exception(response: httpx.Response) -> fastapi.HTTPException:
    """Translate a failed user-service verify response into an HTTPException.

    Always 401 to the client so callers treat it uniformly as a sign-in
    problem, but carry the user service's actual reason (group mismatch,
    non-membership) instead of a bare 'Invalid token'.
    """
    if response.status_code == 401:
        detail = SESSION_EXPIRED_DETAIL
    else:
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = body.get('error') or body.get('detail') or 'Invalid token'
            else:
                detail = 'Invalid token'
        except ValueError:
            detail = 'Invalid token'
    logger.warning('User service verify rejected: status=%s detail=%s',
                   response.status_code, detail)
    return fastapi.HTTPException(status_code=401, detail=detail)
