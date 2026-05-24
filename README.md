# SNBT Dumper

Dumps Indonesian SNBT (Seleksi Nasional Berdasarkan Tes) announcement data from a public Google Cloud Storage bucket into CSV and SQLite.

## Prerequisites

- **Standalone:** Python 3.10+ and pip
- **Docker:** Docker installed

## Install

### Standalone

```bash
git clone https://github.com/hansputera/snbt-dumper.git
cd snbt-dumper
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

### Docker

```bash
docker build -t snbt-dumper .
```

## Usage

### Dump

Downloads all DWG files from a GCS bucket and writes them to CSV and SQLite.

```bash
# Standalone
python -m snbt_dumper
python -m snbt_dumper --storage-url https://storage.googleapis.com/...

# Docker (use -v to persist output on host)
docker run --rm -v "$PWD":/data snbt-dumper
docker run --rm -v "$PWD":/data snbt-dumper --storage-url https://storage.googleapis.com/...
```

### Discover

Fetches `deadline.js` from `pengumuman-snbt.snpmb.id` and prints the `dataurl` (GCS bucket URL).

```bash
# Standalone
python -m snbt_dumper discover

# Docker
docker run --rm snbt-dumper discover
```

### Watch

Polls `deadline.js` every 30 seconds until the GCS bucket is accessible (200 OK), then automatically starts the dump.

```bash
# Standalone
python -m snbt_dumper watch
python -m snbt_dumper watch --interval 60

# Docker (foreground)
docker run --rm -v "$PWD":/data snbt-dumper watch
docker run --rm -v "$PWD":/data snbt-dumper watch --interval 60

# Docker (background / daemon)
docker run -d --name snbt-watch -v "$PWD":/data snbt-dumper watch
docker logs snbt-watch -f          # follow logs
docker stop snbt-watch             # stop when done

# Docker (background with auto-restart)
docker run -d --restart on-failure --name snbt-watch -v "$PWD":/data snbt-dumper watch
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--storage-url` | *2024 bucket* | Google Cloud Storage bucket URL |
| `--output, -o` | `snbt_dump` | Output file prefix |
| `--concurrency, -c` | 10 | Max concurrent HTTP requests |
| `--batch-size, -b` | 20 | Number of listing pages per batch |
| `--page-size` | 1000 | Results per bucket listing page (max 1000) |
| `--retries` | 3 | Retry attempts per failed download |
| `--interval` | 30 | Polling interval (seconds) for watch mode |
| `--no-save-raw` | — | Disable saving raw XML/JSON files |
| `--verbose, -v` | — | Enable debug logging |
| `--help, -h` | — | Show help |

### Examples

```bash
# Dump with higher concurrency and debug logging
python -m snbt_dumper --concurrency 20 -v

# Watch with custom polling interval, saving output to current directory
docker run --rm -v "$PWD":/data snbt-dumper watch --interval 60

# Discover and pipe the URL to a file
python -m snbt_dumper discover > url.txt
```

## Output

All output files are written to the working directory (or `/data` inside Docker).

- `snbt_dump_<timestamp>.csv` — All records in CSV format
- `snbt_dump_<timestamp>.db` — Same data in SQLite (table `snbt_dump`)
- `raw_<timestamp>/` — Raw bucket listing pages (XML) and DWG files (JSON), saved by default (use `--no-save-raw` to disable)
