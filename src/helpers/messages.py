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


def para_grupo(numero, dados, localizacao, quantidade_anexos=0, link=""):
    """Mesmo formato do chamadosTI antigo: uma linha com os campos separados por " | "."""
    if dados["campos"]:
        detalhe = " | ".join(f"{rotulo}: {valor}" for rotulo, valor in dados["campos"].items())
    else:
        detalhe = " ".join(dados["descricao"].split())
    partes = [
        f"Protocolo: #{numero}",
        f"Solicitante: {dados['nome']}",
        f"Unidade: {localizacao}",
        f"Solicita: {motivo_completo(dados['motivo'], dados['sub_motivo'])}",
    ]
    if detalhe:
        partes.append(f"Motivo: {detalhe}")
    partes.append(f"Contato: {dados['celular']}")
    if dados["outra_pessoa"]:
        partes.append(f"Para: {dados['outra_nome']} ({dados['outra_celular']})")
    partes.append(f"Anexos {quantidade_anexos}")
    texto = "*NOVO CHAMADO!*\n" + " | ".join(partes)
    return f"{texto}\nLink: {link}" if link else texto


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
