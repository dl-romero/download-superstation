FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py torrent_manager.py ./
COPY templates/ templates/
COPY static/ static/

RUN useradd -m -u 1000 appuser \
    && mkdir -p /downloads /data \
    && chown -R appuser:appuser /app /downloads /data

USER appuser

ENV DOWNLOAD_PATH=/downloads \
    DATA_PATH=/data \
    HOST=0.0.0.0 \
    PORT=8080

EXPOSE 8080
EXPOSE 6881/tcp
EXPOSE 6881/udp

VOLUME ["/downloads", "/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/login')" || exit 1

CMD ["python", "app.py"]
