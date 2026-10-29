"""Envio de WhatsApp pelo gateway de notificações (POST /v1/messages).

Nunca levanta exceção: o chamado já foi aberto quando as mensagens saem, então
uma falha aqui só vai para o log. O gateway enfileira e espaça os envios; aqui só
se entrega a mensagem a ele.
"""
import logging
import re

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class _GatewayInacessivel(Exception):
    """O gateway não respondeu (rede/timeout): não adianta tentar as demais mensagens."""


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
    # o gateway responde {"error": {"code": ..., "message": ...}}; só o código vai para o log
    try:
        corpo = resp.json()
    except ValueError:
        return ""
    erro = corpo.get("error") if isinstance(corpo, dict) else None
    return str(erro.get("code", "")) if isinstance(erro, dict) else ""


def _enviar(numero, mensagem, grupo, chave):
    """True se o gateway aceitou, False se recusou; levanta _GatewayInacessivel se não respondeu."""
    url, api_key = settings.NOTIFY_URL, settings.NOTIFY_API_KEY
    if not (url and api_key) or not numero:
        log.warning("WhatsApp não configurado; mensagem para %s não enviada", _mascarar(numero))
        return False
    corpo = {"to": _destino(numero, grupo), "text": mensagem}
    if chave:
        corpo["idempotency_key"] = chave
    try:
        resp = requests.post(
            f"{url}/v1/messages",
            headers={"Authorization": f"Bearer {api_key}"},
            json=corpo,
            timeout=(3, 8),
        )
    except requests.RequestException as exc:
        log.error("WhatsApp para %s falhou: %s", _mascarar(numero), type(exc).__name__)
        raise _GatewayInacessivel from exc
    if not 200 <= resp.status_code < 300:
        log.error("WhatsApp para %s: HTTP %s %s", _mascarar(numero), resp.status_code, _motivo(resp))
        return False
    return True


def enviar(numero, mensagem, grupo=False, chave=None):
    """chave: idempotency_key; repetir a mesma chave não duplica a mensagem no gateway."""
    try:
        return _enviar(numero, mensagem, grupo, chave)
    except _GatewayInacessivel:
        return False


def _enviar_todas(mensagens, evento=None):
    for i, (numero, texto, grupo) in enumerate(mensagens):
        chave = f"{evento}-{i}" if evento else None
        try:
            _enviar(numero, texto, grupo, chave)
        except _GatewayInacessivel:
            log.error("Gateway de notificações inacessível; %s mensagem(ns) não enviada(s)", len(mensagens) - i - 1)
            return
        except Exception:  # noqa: BLE001 - nada aqui pode derrubar a resposta
            log.exception("Erro inesperado enviando WhatsApp para %s", _mascarar(numero))


def disparar(mensagens, evento=None):
    """mensagens: lista de (numero, texto, is_group). evento: identifica o fato (ex.: "chamado-123")
    e vira a idempotency_key de cada mensagem (evento-0, evento-1, ...)."""
    mensagens = [m for m in mensagens if m]
    if mensagens:
        _enviar_todas(mensagens, evento)
