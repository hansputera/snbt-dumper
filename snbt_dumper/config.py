from dataclasses import dataclass, field


@dataclass
class Config:
    storage_url: str = 'https://storage.googleapis.com/pengumuman-snbt-2024-prod-looc9w6bbg/'
    output_prefix: str = 'snbt_dump'
    max_concurrent: int = 10
    page_batch_size: int = 20
    page_size: int = 1000
    max_retries: int = 3
    save_raw: bool = True
