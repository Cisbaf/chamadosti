"""Envio de WhatsApp pelo serviço notification-go.

Nunca levanta exceção: o chamado já foi aberto quando as mensagens saem, então
uma falha aqui só vai para o log.
"""
import logging
import threading

import requests
from django.conf import settings

log = logging.getLogger(__name__)


def _mascarar(numero):
    return f"***{numero[-4:]}" if numero and len(numero) > 4 else "***"


def enviar(numero, mensagem, grupo=False):
    url = settings.API_NOTIFICATION_URL
    if not url or not numero:
        log.warning("WhatsApp não configurado; mensagem para %s não enviada", _mascarar(numero))
        return False
    try:
        resp = requests.post(
            url,
            json={"to": numero, "message": mensagem, "is_group": grupo},
            timeout=(3, 8),
        )
    except requests.RequestException as exc:
        log.warning("WhatsApp para %s falhou: %s", _mascarar(numero), type(exc).__name__)
        return False
    if resp.status_code != 200:
        log.warning("WhatsApp para %s: HTTP %s", _mascarar(numero), resp.status_code)
        return False
    return True


def _enviar_todas(mensagens):
    for numero, texto, grupo in mensagens:
        try:
            enviar(numero, texto, grupo)
        except Exception:  # noqa: BLE001 - nada aqui pode derrubar a resposta
            log.exception("Erro inesperado enviando WhatsApp para %s", _mascarar(numero))


def disparar(mensagens):
    """mensagens: lista de (numero, texto, is_group). Sai em segundo plano."""
    mensagens = [m for m in mensagens if m]
    if not mensagens:
        return
    if settings.WHATSAPP_SINCRONO:
        _enviar_todas(mensagens)
        return
    threading.Thread(target=_enviar_todas, args=(mensagens,), daemon=True).start()
