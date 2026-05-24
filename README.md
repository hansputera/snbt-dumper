# SNBT Dumper

Dumps Indonesian SNBT (Seleksi Nasional Berdasarkan Tes) announcement data from a public Google Cloud Storage bucket into CSV and SQLite.

## Prerequisites

- **Python 3.10+**
- **pip** (or pipx for isolated install)

## Install

```bash
git clone https://github.com/hansputera/snbt-dumper.git
cd snbt-dumper
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

## Usage

### Dump (default)

Dumps all `.dwg` files from a GCS bucket into CSV and SQLite.

```bash
python -m snbt_dumper
# or with explicit storage URL
python -m snbt_dumper --storage-url https://storage.googleapis.com/...
```

### Discover

Fetches `deadline.js` from `pengumuman-snbt.snpmb.id` and prints the `dataurl` (GCS bucket URL).

```bash
python -m snbt_dumper discover
```

### Watch

Polls `deadline.js` every 30 seconds until the GCS bucket is accessible, then automatically starts the dump.

```bash
python -m snbt_dumper watch
# custom polling interval
python -m snbt_dumper watch --interval 60
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--storage-url` | *2024 bucket* | Google Cloud Storage bucket URL |
| `--output, -o` | `snbt_dump` | Output file prefix |
| `--concurrency, -c` | 10 | Max concurrent HTTP requests |
| `--batch-size, -b` | 20 | Number of listing pages per batch |
| `--page-size` | 1000 | Results per bucket listing page |
| `--retries` | 3 | Retry attempts per failed download |
| `--interval` | 30 | Polling interval (seconds) for watch mode |
| `--verbose, -v` | — | Enable debug logging |
| `--help, -h` | — | Show help |

### Examples

```bash
# Dump with higher concurrency
python -m snbt_dumper --concurrency 20 -v

# Discover the current dataurl
python -m snbt_dumper discover

# Watch for the bucket to become accessible, then dump
python -m snbt_dumper watch
```

## Output

- `snbt_dump_<timestamp>.csv` — All records in CSV format
- `snbt_dump_<timestamp>.db` — Same data in SQLite (table `snbt_dump`)
