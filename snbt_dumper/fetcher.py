import asyncio
import json
import logging
import xmltodict
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor

import aiohttp

from .config import Config

logger = logging.getLogger(__name__)


class GCSFetcher:

    def __init__(self, config: Config, session: aiohttp.ClientSession) -> None:
        self.config = config
        self.session = session
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        self._executor = ThreadPoolExecutor()

    async def list_dwg_key_batches(self) -> AsyncIterator[list[str]]:
        params: dict[str, str] = {'maxResults': str(self.config.page_size)}
        next_marker: str | None = None
        accumulated: list[str] = []
        page_count = 0

        while True:
            if next_marker:
                params['marker'] = next_marker

            async with self.session.get(self.config.storage_url, params=params) as resp:
                resp.raise_for_status()
                text = await resp.text()

            loop = asyncio.get_event_loop()
            dictxml = await loop.run_in_executor(self._executor, xmltodict.parse, text)

            contents = dictxml.get('ListBucketResult', {}).get('Contents', []) or []
            keys = [data['Key'] for data in contents if data['Key'].endswith('.dwg')]
            accumulated.extend(keys)
            page_count += 1

            if page_count >= self.config.page_batch_size:
                logger.info("Collected %d keys across %d pages", len(accumulated), page_count)
                yield accumulated
                accumulated = []
                page_count = 0

            next_marker = dictxml.get('ListBucketResult', {}).get('NextMarker')
            if not next_marker:
                break

        if accumulated:
            logger.info("Final batch: %d keys", len(accumulated))
            yield accumulated

    async def fetch_dwg_data(self, key: str) -> dict | None:
        url = self.config.storage_url + key
        for attempt in range(self.config.max_retries):
            try:
                async with self.semaphore:
                    async with self.session.get(url, headers={'Accept': 'application/json'}) as resp:
                        resp.raise_for_status()
                        text = await resp.text()
                        return json.loads(text)
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    logger.warning("Failed to fetch %s after %d attempts: %s", key, self.config.max_retries, e)
                    return None
                logger.debug("Retry %d/%d for %s: %s", attempt + 1, self.config.max_retries, key, e)
                await asyncio.sleep(2 ** attempt)
