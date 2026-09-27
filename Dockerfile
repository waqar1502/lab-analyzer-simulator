FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE config.example.json ./
COPY src ./src
COPY profiles ./profiles
COPY fixtures ./fixtures

RUN addgroup --system simulator && adduser --system --ingroup simulator simulator \
    && chown -R simulator:simulator /app

USER simulator
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

LABEL org.opencontainers.image.title="Lab Analyzer Simulator" \
      org.opencontainers.image.description="Generic HL7/MLLP laboratory analyzer simulator"

CMD ["python", "-m", "lab_analyzer_simulator", "--root", "/app", "web", "--host", "0.0.0.0", "--port", "8000"]
