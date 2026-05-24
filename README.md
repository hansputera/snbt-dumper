# SNBT Dumper

Dumps Indonesian SNBT (Seleksi Nasional Berdasarkan Tes) 2024 announcement data from a public Google Cloud Storage bucket into CSV and SQLite.

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

```bash
# Run from the package
python -m snbt_dumper

# Or if installed via pip install -e .
snbt-dumper
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--concurrency, -c` | 10 | Max concurrent HTTP requests |
| `--batch-size, -b` | 20 | Number of listing pages per batch |
| `--page-size` | 1000 | Results per bucket listing page |
| `--retries` | 3 | Retry attempts per failed download |
| `--output, -o` | `snbt_dump` | Output file prefix |
| `--verbose, -v` | — | Enable debug logging |
| `--help, -h` | — | Show help |

### Example

```bash
python -m snbt_dumper --concurrency 20 -v
```

## Output

- `snbt_dump_<timestamp>.csv` — All records in CSV format
- `snbt_dump_<timestamp>.db` — Same data in SQLite (table `snbt_dump`)
