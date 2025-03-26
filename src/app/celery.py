from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Configuração padrão para o Celery usar as configurações do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('app', broker='redis://redis-chamadosti:6380/0')

app.conf.update(
    result_extended=True
)
# Lê as configurações do Django para o Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks nos aplicativos instalados
app.autodiscover_tasks(['app'])
