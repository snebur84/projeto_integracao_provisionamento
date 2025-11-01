# Dockerfile para a aplicação Django (provision)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Variável de ambiente PORT é injetada pelo Cloud Run. Usamos 8080 como fallback.
ARG PORT=8080
ENV PORT=${PORT}

# Instala dependências de sistema
# Removendo netcat-openbsd (assumindo que o entrypoint não espera mais por DBs locais)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/app/provision

# Copia requirements e instala
# (assume que requirements.txt exista na raiz do projeto)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /app/requirements.txt

# Copia o código da aplicação
COPY . /app

# Copia scripts e torna executáveis
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY scripts/create_superuser.py /app/scripts/create_superuser.py
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /app/scripts/create_superuser.py

ENV PATH="/root/.local/bin:${PATH}"

# A porta 8080 é a porta padrão que o Cloud Run espera
EXPOSE 8080

ENTRYPOINT ["docker-entrypoint.sh"]
# CRÍTICO: Usa a variável de ambiente $PORT injetada pelo Cloud Run
CMD ["gunicorn", "provision.wsgi:application", "--bind", "0.0.0.0:${PORT}", "--workers", "3"]