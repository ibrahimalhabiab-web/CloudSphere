FROM python:3.13-alpine

RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --chown=app:app app.py /app/app.py
COPY --chown=app:app assets /app/assets

USER app
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"]
CMD ["python", "/app/app.py"]
