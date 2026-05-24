import csv
import logging
import os
from datetime import datetime

import aiofiles
import aiosqlite

from .config import Config
from .models import SnbtRecord

logger = logging.getLogger(__name__)

CSV_HEADERS = [
    'id', 'utbk_no', 'name', 'date_of_birth', 'bidik_misi',
    'passed', 'ptn', 'ptn_code', 'prodi', 'prodi_code', 'next_url',
]

SQL_SCHEMA = """
    CREATE TABLE IF NOT EXISTS snbt_dump (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utbk_no TEXT NOT NULL,
        name TEXT NOT NULL,
        date_of_birth TEXT NOT NULL,
        bidik_misi INTEGER,
        passed INTEGER NOT NULL,
        ptn TEXT,
        ptn_code INTEGER,
        prodi TEXT,
        prodi_code INTEGER,
        next_url TEXT
    )
"""

SQL_INSERT = """
    INSERT INTO snbt_dump (utbk_no, name, date_of_birth, bidik_misi, passed, ptn, ptn_code, prodi, prodi_code, next_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class StorageWriter:

    def __init__(self, config: Config) -> None:
        timestamp = datetime.now().isoformat()
        self.csv_path = f"{config.output_prefix}_{timestamp}.csv"
        self.db_path = f"{config.output_prefix}_{timestamp}.db"
        self._csv_file = None
        self._csv_writer = None
        self._db: aiosqlite.Connection | None = None
        self._headers_written = False
        self._counter = 0
        self._save_raw = config.save_raw
        self._raw_pages_dir = f"raw_{timestamp}/pages" if self._save_raw else None
        self._raw_dwg_dir = f"raw_{timestamp}/dwg" if self._save_raw else None

    async def __aenter__(self) -> 'StorageWriter':
        self._csv_file = await aiofiles.open(self.csv_path, "w", newline="")
        self._csv_writer = csv.writer(self._csv_file, delimiter=',', quotechar=';')
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute(SQL_SCHEMA)
        logger.info("Output CSV: %s", self.csv_path)
        logger.info("Output DB : %s", self.db_path)
        if self._save_raw:
            os.makedirs(self._raw_pages_dir, exist_ok=True)
            os.makedirs(self._raw_dwg_dir, exist_ok=True)
            logger.info("Raw dirs: %s & %s", self._raw_pages_dir, self._raw_dwg_dir)
        return self

    async def __aexit__(self, *args) -> None:
        await self._db.commit()
        await self._csv_file.close()
        await self._db.close()

    async def save_raw_page(self, page_number: int, text: str) -> None:
        if not self._save_raw:
            return
        os.makedirs(self._raw_pages_dir, exist_ok=True)
        path = f"{self._raw_pages_dir}/page_{page_number:05d}.xml"
        async with aiofiles.open(path, "w") as f:
            await f.write(text)

    async def save_raw_dwg(self, key: str, text: str) -> None:
        if not self._save_raw:
            return
        os.makedirs(self._raw_dwg_dir, exist_ok=True)
        safe = key.replace("/", "_").replace(":", "_")
        path = f"{self._raw_dwg_dir}/{safe}"
        async with aiofiles.open(path, "w") as f:
            await f.write(text)

    async def write_record(self, record: SnbtRecord) -> None:
        self._counter += 1

        if not self._headers_written:
            await self._csv_writer.writerow(CSV_HEADERS)
            self._headers_written = True

        await self._csv_writer.writerow([str(self._counter)] + record.to_csv_row())
        await self._db.execute(SQL_INSERT, record.to_db_tuple())

    async def flush(self) -> None:
        await self._db.commit()
