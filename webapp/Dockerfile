FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BILLING_DB_DIR=/app/db \
    PDF_OUTPUT_DIR=/app/pdf_output

WORKDIR /app

COPY webapp/requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

RUN groupadd --gid 1000 app && useradd --uid 1000 --gid 1000 --create-home app

COPY --chown=app:app database.py settings.py invoice.py customer.py product.py \
     reports.py printer.py receipt.py delivery_challan.py exporter.py ./
COPY --chown=app:app webapp ./webapp

RUN mkdir -p /app/db /app/backup /app/pdf_output && chown -R app:app /app/db /app/backup /app/pdf_output

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
