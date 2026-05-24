import asyncio
import logging

import aiohttp

from .discovery import fetch_deadline_js, extract_dataurl, check_bucket_accessible

logger = logging.getLogger(__name__)


async def watch(session: aiohttp.ClientSession, poll_interval: int = 30) -> str | None:
    logger.info("Watching %s every %ds for accessible GCS bucket ...", "deadline.js", poll_interval)

    while True:
        try:
            js = await fetch_deadline_js(session)
            url = extract_dataurl(js)

            if url:
                logger.info("Found dataurl: %s", url)
                if await check_bucket_accessible(session, url):
                    logger.info("Bucket is accessible")
                    return url
            else:
                logger.debug("No dataurl found in deadline.js")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning("Error while watching deadline.js: %s", e)

        logger.info("Bucket not accessible, retrying in %ds ...", poll_interval)
        await asyncio.sleep(poll_interval)
