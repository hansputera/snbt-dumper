import logging
import re

from .user_agents import random_headers

logger = logging.getLogger(__name__)

DEADLINE_JS_URL = 'https://pengumuman-snbt.snpmb.id/deadline.js'


async def fetch_deadline_js(session) -> str:
    async with session.get(DEADLINE_JS_URL, headers=random_headers()) as resp:
        resp.raise_for_status()
        return await resp.text()


def extract_dataurl(js_text: str) -> str | None:
    m = re.search(r"dataurl\s*=\s*'([^']+)'", js_text)
    if m:
        return m.group(1)
    return None


async def check_bucket_accessible(session, url: str) -> bool:
    try:
        async with session.head(url, timeout=10, headers=random_headers()) as resp:
            return resp.status == 200
    except Exception as e:
        logger.debug("Bucket %s not accessible: %s", url, e)
        return False
