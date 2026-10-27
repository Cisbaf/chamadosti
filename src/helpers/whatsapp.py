"""Envio de WhatsApp pela Evolution API.

Nunca levanta exceção: o chamado já foi aberto quando as mensagens saem, então
uma falha aqui só vai para o log.
"""
import logging
import re
import threading
import time

import requests
from django.conf import settings

log = logging.getLogger(__name__)


def _mascarar(numero):
    numero = (numero or "").split("@")[0]
    return f"***{numero[-4:]}" if len(numero) > 4 else "***"


def _destino(numero, grupo):
    """Grupo segue como veio (JID); celular de 11 dígitos ganha o 55 do Brasil."""
    if grupo:
        return numero
    digitos = re.sub(r"\D", "", numero)
    return f"55{digitos}" if len(digitos) == 11 else digitos


def _motivo(resp):
    # o corpo de erro da Evolution pode trazer o número completo; só o campo "error" é seguro
    try:
        corpo = resp.json()
    except ValueError:
        return ""
    return str(corpo.get("error", "")) if isinstance(corpo, dict) else ""


def enviar(numero, mensagem, grupo=False):
    url, instancia, chave = settings.EVOLUTION_URL, settings.EVOLUTION_INSTANCE, settings.EVOLUTION_API_KEY
    if not (url and instancia and chave) or not numero:
        log.warning("WhatsApp não configurado; mensagem para %s não enviada", _mascarar(numero))
        return False
    try:
        resp = requests.post(
            f"{url}/message/sendText/{instancia}",
            headers={"apikey": chave},
            json={"number": _destino(numero, grupo), "text": mensagem},
            timeout=(3, 8),
        )
    except requests.RequestException as exc:
        log.error("WhatsApp para %s falhou: %s", _mascarar(numero), type(exc).__name__)
        return False
    if not 200 <= resp.status_code < 300:
        log.error("WhatsApp para %s: HTTP %s %s", _mascarar(numero), resp.status_code, _motivo(resp))
        return False
    return True


def _enviar_todas(mensagens):
    for i, (numero, texto, grupo) in enumerate(mensagens):
        if i:
            time.sleep(settings.EVOLUTION_DELAY)  # evita rajada na mesma abertura de chamado
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
