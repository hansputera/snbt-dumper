FROM python:3.11-slim

RUN pip install --no-cache-dir aiohttp aiosqlite aiofiles xmltodict tqdm

COPY snbt_dumper/ /app/snbt_dumper/
ENV PYTHONPATH=/app

WORKDIR /data

ENTRYPOINT ["python3", "-m", "snbt_dumper"]
