import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime

import aiohttp
from tqdm import tqdm

from .config import Config
from .discovery import DEADLINE_JS_URL, fetch_deadline_js, extract_dataurl, is_safe_gcs_url
from .fetcher import GCSFetcher
from .models import SnbtRecord
from .storage import StorageWriter
from .worker import watch

logger = logging.getLogger(__name__)

_SHUTTING_DOWN = False


def _handle_signal() -> None:
    global _SHUTTING_DOWN
    if _SHUTTING_DOWN:
        logger.warning("Forced exit")
        sys.exit(1)
    _SHUTTING_DOWN = True
    logger.info("Shutdown requested, finishing current batch ...")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dump SNBT announcement data from Google Cloud Storage to CSV and SQLite."
    )
    parser.add_argument(
        'command', nargs='?', choices=['discover', 'watch'], default=None,
        help="'discover' — print dataurl from deadline.js; 'watch' — poll until bucket is accessible, then dump",
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
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds for watch mode (default: %(default)s)",
    )
    parser.add_argument(
        "--no-save-raw",
        action="store_true",
        help="Don't save raw bucket listing pages and DWG files",
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
        save_raw=not args.no_save_raw,
    )


async def run_dump(config: Config, session: aiohttp.ClientSession) -> None:
    start = datetime.now()
    logger.info("Starting SNBT dumper (concurrency=%d, batch=%d pages)", config.max_concurrent, config.page_batch_size)

    ts = datetime.now().strftime('%Y-%m-%dT%H-%M-%S-%f')

    if config.save_raw:
        os.makedirs(f"raw_{ts}/pages", exist_ok=True)
        os.makedirs(f"raw_{ts}/dwg", exist_ok=True)

    async with StorageWriter(config, timestamp=ts) as writer:
        fetcher = GCSFetcher(
            config, session,
            on_page=writer.save_raw_page if config.save_raw else None,
            on_dwg=writer.save_raw_dwg if config.save_raw else None,
        )

        logger.info("Listing .dwg keys from bucket %s ...", config.storage_url)
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
            logger.info("Batch %d complete (running total: ~%d records)", batch_idx, writer.record_count)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("Finished in %.2f seconds", elapsed)


async def run(config: Config) -> None:
    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        await run_dump(config, session)


async def run_discover() -> None:
    async with aiohttp.ClientSession() as session:
        js = await fetch_deadline_js(session)
        url = extract_dataurl(js)
        if url:
            print(url)
        else:
            logger.error("Could not extract dataurl from %s", DEADLINE_JS_URL)
            raise SystemExit(1)


async def run_watch(config: Config, interval: int) -> None:
    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        url = await watch(session, poll_interval=interval)
        if url:
            if not is_safe_gcs_url(url):
                logger.error("Discovered URL is not a safe GCS URL: %s", url)
                raise SystemExit(1)
            config.storage_url = url
            logger.info("Starting dump using %s", url)
            await run_dump(config, session)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    try:
        if args.command == 'discover':
            loop.run_until_complete(run_discover())
        elif args.command == 'watch':
            config = config_from_args(args)
            loop.run_until_complete(run_watch(config, args.interval))
        else:
            config = config_from_args(args)
            loop.run_until_complete(run(config))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        loop.close()
