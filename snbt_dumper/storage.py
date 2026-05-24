import csv
import logging
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

    async def __aenter__(self) -> 'StorageWriter':
        self._csv_file = await aiofiles.open(self.csv_path, "w", newline="")
        self._csv_writer = csv.writer(self._csv_file, delimiter=',', quotechar=';')
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute(SQL_SCHEMA)
        logger.info("Output CSV: %s", self.csv_path)
        logger.info("Output DB : %s", self.db_path)
        return self

    async def __aexit__(self, *args) -> None:
        await self._db.commit()
        await self._csv_file.close()
        await self._db.close()

    async def write_record(self, record: SnbtRecord) -> None:
        self._counter += 1

        if not self._headers_written:
            await self._csv_writer.writerow(CSV_HEADERS)
            self._headers_written = True

        await self._csv_writer.writerow([str(self._counter)] + record.to_csv_row())
        await self._db.execute(SQL_INSERT, record.to_db_tuple())

    async def flush(self) -> None:
        await self._db.commit()
