import asyncio
import logging
import re
from urllib.parse import urlparse

import aiohttp

from .user_agents import random_headers

logger = logging.getLogger(__name__)

DEADLINE_JS_URL = 'https://pengumuman-snbt.snpmb.id/deadline.js'
ALLOWED_GCS_HOST = 'storage.googleapis.com'


def is_safe_gcs_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == 'https' and parsed.hostname == ALLOWED_GCS_HOST
    except Exception:
        return False


async def fetch_deadline_js(session: aiohttp.ClientSession) -> str:
    timeout = aiohttp.ClientTimeout(total=15)
    async with session.get(DEADLINE_JS_URL, headers=random_headers(), timeout=timeout) as resp:
        resp.raise_for_status()
        return await resp.text()


def extract_dataurl(js_text: str) -> str | None:
    m = re.search(r"dataurl\s*=\s*'([^']+)'", js_text)
    if m:
        return m.group(1)
    return None


async def check_bucket_accessible(session: aiohttp.ClientSession, url: str) -> bool:
    if not is_safe_gcs_url(url):
        logger.warning("Blocked SSRF attempt to non-GCS URL: %s", url)
        return False

    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=10), headers=random_headers()) as resp:
            return resp.status == 200
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.debug("Bucket %s not accessible: %s", url, e)
        return False
