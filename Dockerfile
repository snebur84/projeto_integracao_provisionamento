# Dockerfile para a aplicação Django (provision)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências de sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev curl netcat-openbsd \
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

# Porta interna do gunicorn
EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "provision.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]