FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# mysqlclient precisa compilar contra a libmysqlclient
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc pkg-config default-libmysqlclient-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src .

# Arquivos estáticos com nome por versão (cache do navegador não serve JS/CSS velho).
# A SECRET_KEY daqui só existe durante o build; a de verdade vem do .env na execução.
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

# Usuário sem privilégios (com pasta pessoal: o gunicorn cria ali o socket de controle); /data guarda o SQLite quando não há MySQL
RUN useradd --system --uid 1000 --create-home app && \
    mkdir /data && chown app /data
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)"

# Aplica migrações pendentes e sobe o gunicorn. O prazo de 90 s cobre anexos grandes indo para o GLPI.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn app.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 90 --access-logfile -"]
