FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app

EXPOSE 8000

# workers=1: cache.py usa TTLCache em memória por processo (não compartilhado).
# Com 2+ workers, um POST invalida só o cache do worker que o atendeu — o outro
# segue servindo GET stale até o TTL expirar (bug confirmado: memoria/usuario/
# saldo servindo dado de até 60-300s atrás mesmo após write bem-sucedido).
# VPS é 1 vCPU (KVM1) — 2 workers já não davam paralelismo real, só esse bug.
CMD ["gunicorn", "--workers=1", "--bind=0.0.0.0:8000", "src.app:create_app()"]
