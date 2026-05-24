import asyncio
import json
import logging
import random
import xmltodict
from collections.abc import AsyncIterator, Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor

import aiohttp

from .config import Config
from .user_agents import random_headers

logger = logging.getLogger(__name__)


class GCSFetcher:

    def __init__(
        self,
        config: Config,
        session: aiohttp.ClientSession,
        on_page: Callable[[int, str], Awaitable[None]] | None = None,
        on_dwg: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> None:
        self.config = config
        self.session = session
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        self._executor = ThreadPoolExecutor()
        self._on_page = on_page
        self._on_dwg = on_dwg
        self._page_seq = 0

    def __del__(self) -> None:
        self._executor.shutdown(wait=False)

    async def list_dwg_key_batches(self) -> AsyncIterator[list[str]]:
        params: dict[str, str] = {'maxResults': str(self.config.page_size)}
        next_marker: str | None = None
        accumulated: list[str] = []
        page_count = 0

        while True:
            if next_marker:
                params['marker'] = next_marker

            async with self.session.get(self.config.storage_url, params=params, headers=random_headers()) as resp:
                resp.raise_for_status()
                text = await resp.text()

            self._page_seq += 1
            if self._on_page:
                await self._on_page(self._page_seq, text)

            loop = asyncio.get_running_loop()
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
                    await asyncio.sleep(random.uniform(0.2, 0.8))
                    async with self.session.get(url, headers=random_headers()) as resp:
                        text = await resp.text()

                        if resp.status >= 400:
                            if 400 <= resp.status < 500 and resp.status != 429:
                                logger.warning("Client error %d for %s, not retrying", resp.status, key)
                                return None
                            resp.raise_for_status()

                        if self._on_dwg:
                            await self._on_dwg(key, text)
                        return json.loads(text)
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON for %s: %s", key, e)
                return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.config.max_retries - 1:
                    logger.warning("Failed to fetch %s after %d attempts: %s", key, self.config.max_retries, e)
                    return None
                logger.debug("Retry %d/%d for %s: %s", attempt + 1, self.config.max_retries, key, e)
                await asyncio.sleep(2 ** attempt)
