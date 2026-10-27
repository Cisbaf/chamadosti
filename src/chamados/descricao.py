"""Monta título, descrição (HTML) e campos fixos do ticket no GLPI."""
from html import escape

from helpers.messages import mascara_celular, motivo_completo

from . import localizacoes

# Valores padrão de todo chamado (plano, seção 6).
PADROES_TICKET = {
    "type": 1,  # Incidente
    "itilcategories_id": 1,  # Suporte
    "status": 1,  # Novo
    "entities_id": 0,  # Entidade raiz
}


def _linhas_para_html(linhas):
    return "<br>".join(escape(linha) for linha in linhas)


def montar_ticket(dados):
    """Devolve o dict de entrada do POST /Ticket (sem requesttypes_id)."""
    atendido_nome = dados["outra_nome"] if dados["outra_pessoa"] else dados["nome"]
    atendido_localizacao_id = (
        dados["outra_localizacao_id"] if dados["outra_pessoa"] else dados["localizacao_id"]
    )

    blocos = []
    if dados["outra_pessoa"]:
        blocos.append([
            f"Solicitante: {dados['nome']}",
            f"Celular: {mascara_celular(dados['celular'])}",
            f"Localização: {localizacoes.caminho(dados['localizacao_id'])}",
        ])
        blocos.append([
            f"Terceiro: {dados['outra_nome']}",
            f"Celular: {mascara_celular(dados['outra_celular'])}",
            f"Localização: {localizacoes.caminho(dados['outra_localizacao_id'])}",
        ])
        motivo = [f"Motivo: {motivo_completo(dados['motivo'], dados['sub_motivo'])}"]
    else:
        motivo = [
            f"Solicitante: {dados['nome']}",
            f"Celular: {mascara_celular(dados['celular'])}",
            f"Localização: {localizacoes.caminho(dados['localizacao_id'])}",
            f"Motivo: {motivo_completo(dados['motivo'], dados['sub_motivo'])}",
        ]
    if dados["campos"]:
        motivo.append(" | ".join(f"{rotulo}: {valor}" for rotulo, valor in dados["campos"].items()))
    else:
        motivo.append("Descrição:")
        motivo.extend(dados["descricao"].split("\n"))
    blocos.append(motivo)

    return {
        **PADROES_TICKET,
        # provisório: vira "<Motivo> - #<número>" assim que o GLPI devolve o número
        "name": f"{dados['motivo']} - {atendido_nome}"[:250],
        "content": "".join(f"<p>{_linhas_para_html(bloco)}</p>" for bloco in blocos),
        "locations_id": atendido_localizacao_id,
    }


def titulo_final(dados, ticket_id):
    return f"{dados['motivo']} - #{ticket_id}"


def localizacao_do_atendido(dados):
    chave = "outra_localizacao_id" if dados["outra_pessoa"] else "localizacao_id"
    return localizacoes.caminho(dados[chave])
