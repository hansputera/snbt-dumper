from dataclasses import dataclass


@dataclass
class Config:
    storage_url: str = 'https://storage.googleapis.com/pengumuman-snbt-2024-prod-looc9w6bbg/'
    output_prefix: str = 'snbt_dump'
    max_concurrent: int = 10
    page_batch_size: int = 20
    page_size: int = 1000
    max_retries: int = 3
    save_raw: bool = True

    def __post_init__(self) -> None:
        if self.max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        if self.page_size < 1 or self.page_size > 1000:
            raise ValueError("page_size must be between 1 and 1000")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
