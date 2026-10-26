import json
import logging
import math
import re
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from helpers import messages, whatsapp
from helpers.glpi_client import GlpiClient, GlpiErro
from users.models import UserRequest

from . import descricao, localizacoes, validacao
from .models import Envio

log = logging.getLogger(__name__)

# Um envio "processando" há mais que isso é considerado abandonado.
ENVIO_ABANDONADO = timedelta(seconds=60)

MSG_FALHA = "Não conseguimos abrir o chamado. Tente de novo em alguns instantes. A TI já foi avisada."


def _json(corpo, status=200):
    resposta = JsonResponse(corpo, status=status, json_dumps_params={"ensure_ascii": False})
    resposta["Cache-Control"] = "no-store"
    return resposta


def _ler_pedido(request):
    """Aceita multipart (campo "data" em JSON + "files") ou application/json."""
    if (request.content_type or "").startswith("application/json"):
        return json.loads(request.body or b"null"), []
    arquivos = [(f.name, f.read()) for f in request.FILES.getlist("files")]
    return json.loads(request.POST.get("data", "null")), arquivos


def _reservar_envio(token):
    """Devolve (envio, resposta). Se resposta não for None, é o que deve ser devolvido."""
    Envio.objects.filter(criado_em__lt=timezone.now() - timedelta(days=2)).delete()
    try:
        with transaction.atomic():
            return Envio.objects.create(token=token), None
    except IntegrityError:
        envio = Envio.objects.get(token=token)
    if envio.estado == Envio.ABERTO:
        return None, _json(
            {"ok": True, "numero": envio.ticket_id, "anexos_falhos": envio.anexos_falhos, "repetido": True},
            status=200,
        )
    if timezone.now() - envio.atualizado_em < ENVIO_ABANDONADO:
        return None, _json({"ok": False, "erro": "em_andamento", "mensagem": "Seu pedido já está sendo enviado."}, status=409)
    envio.save()  # reassume um envio abandonado (atualiza atualizado_em)
    return envio, None


def _guardar_pessoa(nome, celular, localizacao_id):
    try:
        UserRequest.objects.update_or_create(
            number_applicant=celular,
            defaults={
                "name_applicant": nome,
                "location_id": localizacao_id,
                "location_applicant": localizacoes.caminho(localizacao_id),
            },
        )
    except Exception:  # noqa: BLE001 - o chamado já existe; o cadastro é só conveniência
        log.exception("Não foi possível atualizar o cadastro por celular")


def _guardar_cadastros(dados):
    _guardar_pessoa(dados["nome"], dados["celular"], dados["localizacao_id"])
    if dados["outra_pessoa"]:
        _guardar_pessoa(dados["outra_nome"], dados["outra_celular"], dados["outra_localizacao_id"])


def _avisar_abertura(ticket_id, dados, resultado, local, grupo):
    mensagens = [(dados["celular"], messages.para_solicitante(ticket_id), False)]
    if dados["outra_pessoa"]:
        mensagens.append((dados["outra_celular"], messages.para_atendido(ticket_id, dados["nome"]), False))
    mensagens.append((grupo, messages.para_grupo(ticket_id, dados, local), True))
    if resultado.anexos_falhos:
        mensagens.append((grupo, messages.anexos_nao_enviados(ticket_id, resultado.anexos_falhos), True))
    whatsapp.disparar(mensagens)


@require_POST
def criar_chamado(request):
    try:
        bruto, arquivos_brutos = _ler_pedido(request)
    except (ValueError, UnicodeDecodeError):
        return _json({"ok": False, "erros": {"geral": "Pedido inválido."}}, status=400)

    dados, erros = validacao.validar(bruto)
    anexos = []
    if not erros:
        anexos, erro_anexo = validacao.validar_anexos(arquivos_brutos)
        if erro_anexo:
            erros = {"anexos": erro_anexo}
    if erros:
        return _json({"ok": False, "erros": erros}, status=422)

    envio = None
    if dados["token"]:
        envio, resposta = _reservar_envio(dados["token"])
        if resposta is not None:
            return resposta

    local = descricao.localizacao_do_atendido(dados)
    try:
        # anexos grandes precisam de mais tempo: +2 s por MB enviado ao GLPI
        extra = 2 * math.ceil(sum(len(a.conteudo) for a in anexos) / (1024 * 1024))
        with GlpiClient.das_configuracoes(extra) as glpi:
            resultado = glpi.abrir_chamado(
                descricao.montar_ticket(dados), anexos, lambda numero: descricao.titulo_final(dados, numero)
            )
    except Exception as exc:  # noqa: BLE001 - qualquer falha vira "tente de novo" + aviso à TI
        tipo = exc.tipo if isinstance(exc, GlpiErro) else type(exc).__name__
        log.error("Falha ao abrir chamado no GLPI (%s): %s", tipo, exc, exc_info=not isinstance(exc, GlpiErro))
        if envio:
            envio.delete()
        erro = f"{tipo} - {exc}" if isinstance(exc, GlpiErro) else tipo
        whatsapp.disparar([(settings.CONTACT_NOTIFICATION, messages.falha_glpi(dados, local, erro, len(anexos)), True)])
        return _json({"ok": False, "erro": "glpi", "mensagem": MSG_FALHA}, status=502)

    if envio:
        envio.estado = Envio.ABERTO
        envio.ticket_id = resultado.ticket_id
        envio.anexos_falhos = len(resultado.anexos_falhos)
        envio.save()
    _guardar_cadastros(dados)
    _avisar_abertura(resultado.ticket_id, dados, resultado, local, settings.CONTACT_NOTIFICATION)
    return _json(
        {"ok": True, "numero": resultado.ticket_id, "anexos_falhos": len(resultado.anexos_falhos)},
        status=201,
    )


@require_GET
def solicitante(request, celular):
    digitos = re.sub(r"\D", "", celular)
    if len(digitos) != 11:
        return _json({"encontrado": False}, status=400)
    cadastro = UserRequest.objects.filter(number_applicant=digitos).first()
    if not cadastro:
        return _json({"encontrado": False})
    localizacao_id = cadastro.location_id
    if not localizacoes.existe(localizacao_id):
        localizacao_id = localizacoes.id_do_caminho_antigo(cadastro.location_applicant)
    return _json({
        "encontrado": True,
        "nome": cadastro.name_applicant,
        "localizacao_id": localizacao_id,
        "localizacao": localizacoes.caminho(localizacao_id),
    })
