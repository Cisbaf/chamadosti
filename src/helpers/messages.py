"""Textos das mensagens de WhatsApp."""


def mascara_celular(digitos):
    d = "".join(c for c in str(digitos) if c.isdigit())
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    return d


def motivo_completo(motivo, sub_motivo=""):
    return f"{motivo} › {sub_motivo}" if sub_motivo else motivo


def para_solicitante(numero):
    return f"Seu chamado nº {numero} foi aberto. Use esse número se precisar falar com a TI."


def para_atendido(numero, solicitante):
    return f"A TI abriu o chamado nº {numero} para você, a pedido de {solicitante}."


def para_grupo(numero, dados, localizacao):
    quem = f"aberto por {dados['nome']}"
    if dados["outra_pessoa"]:
        quem += f" para {dados['outra_nome']}"
    return (
        f"*NOVO CHAMADO nº {numero}* · {motivo_completo(dados['motivo'], dados['sub_motivo'])}"
        f" · {localizacao} · {quem}"
    )


def anexos_nao_enviados(numero, nomes):
    lista = ", ".join(nomes)
    return (
        f"*Atenção:* o chamado nº {numero} foi aberto, mas "
        f"{'o anexo não foi enviado' if len(nomes) == 1 else 'os anexos não foram enviados'} ao GLPI: {lista}."
    )


def falha_glpi(dados, localizacao, erro, quantidade_anexos):
    linhas = [
        "*FALHA AO ABRIR CHAMADO NO GLPI*",
        f"Erro: {erro}",
        f"Solicitante: {dados['nome']} ({mascara_celular(dados['celular'])})",
    ]
    if dados["outra_pessoa"]:
        linhas.append(f"Atendido: {dados['outra_nome']} ({mascara_celular(dados['outra_celular'])})")
    linhas.append(f"Local: {localizacao}")
    linhas.append(f"Motivo: {motivo_completo(dados['motivo'], dados['sub_motivo'])}")
    if dados["campos"]:
        linhas.append(" | ".join(f"{k}: {v}" for k, v in dados["campos"].items()))
    if dados["descricao"]:
        texto = dados["descricao"]
        linhas.append(f"Descrição: {texto[:500]}{'…' if len(texto) > 500 else ''}")
    if quantidade_anexos:
        linhas.append(f"Anexos: {quantidade_anexos} (não guardados; peça de novo ao solicitante)")
    return "\n".join(linhas)
