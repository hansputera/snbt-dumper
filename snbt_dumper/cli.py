import argparse
import asyncio
import logging
from datetime import datetime

import aiohttp
from tqdm import tqdm

from .config import Config
from .fetcher import GCSFetcher
from .models import SnbtRecord
from .storage import StorageWriter

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dump SNBT announcement data from Google Cloud Storage to CSV and SQLite."
    )
    parser.add_argument(
        "--storage-url",
        default=Config.storage_url,
        help="Google Cloud Storage bucket URL (default: %(default)s)",
    )
    parser.add_argument(
        "--output", "-o",
        default=Config.output_prefix,
        help="Output file prefix (default: %(default)s)",
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=Config.max_concurrent,
        help="Max concurrent HTTP requests (default: %(default)s)",
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=Config.page_batch_size,
        help="Number of listing pages to accumulate before processing (default: %(default)s)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=Config.page_size,
        help="Results per bucket listing page (max 1000, default: %(default)s)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=Config.max_retries,
        help="Max retry attempts per failed DWG download (default: %(default)s)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        storage_url=args.storage_url,
        output_prefix=args.output,
        max_concurrent=args.concurrency,
        page_batch_size=args.batch_size,
        page_size=args.page_size,
        max_retries=args.retries,
    )


async def run(config: Config) -> None:
    start = datetime.now()
    logger.info("Starting SNBT dumper (concurrency=%d, batch=%d pages)", config.max_concurrent, config.page_batch_size)

    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)

    async with aiohttp.ClientSession(connector=connector) as session:
        fetcher = GCSFetcher(config, session)

        async with StorageWriter(config) as writer:
            logger.info("Listing .dwg keys from bucket ...")
            async for batch_idx, batch_keys in enumerate(fetcher.list_dwg_key_batches(), 1):
                logger.info("Batch %d: processing %d keys", batch_idx, len(batch_keys))

                tasks = [fetcher.fetch_dwg_data(k) for k in batch_keys]
                pbar = tqdm(
                    asyncio.as_completed(tasks),
                    total=len(tasks),
                    desc=f"Batch {batch_idx}",
                    unit="key",
                )
                for coro in pbar:
                    data = await coro
                    if data is not None:
                        record = SnbtRecord.from_dict(data)
                        await writer.write_record(record)

                await writer.flush()
                logger.info("Batch %d complete (running total: ~%d records)", batch_idx, writer._counter)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("Finished in %.2f seconds", elapsed)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

    config = config_from_args(args)
    asyncio.run(run(config))
