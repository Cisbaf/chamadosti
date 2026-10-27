"""Validação do pedido de chamado (o servidor repete tudo o que o navegador valida)."""
import os
import re
from dataclasses import dataclass

from . import localizacoes

MAX_ANEXOS = 2
MAX_BYTES_ANEXOS = 15 * 1024 * 1024
MAX_NOME = 100
MAX_CAMPO = 200
MAX_DESCRICAO = 5000

MOTIVOS = [
    "Suporte Computador",
    "Suporte Impressora",
    "Suporte Sistemas",
    "Suporte Tablet",
    "Suporte Celular",
    "Criação de Login",
    "Requisição de Material",
    "Convocação para o site",
]
SUBMOTIVOS = {
    "Suporte Sistemas": ["Suporte SSO", "Suporte Marque Fácil", "Plataforma de Ensino NEP", "Outro"],
    "Criação de Login": ["Sistemas SSO", "Sistema Marque Fácil"],
}
CAMPOS_LOGIN = {
    "Sistemas SSO": ["Nome Completo", "CPF", "Cargo"],
    "Sistema Marque Fácil": ["Nome Completo", "CPF", "Cargo", "Email", "Município"],
}

_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_NOME = re.compile(r"^[^\W\d_]+(?:[ '’\-]+[^\W\d_]+)*$")
_LETRA = re.compile(r"[^\W\d_]")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TOKEN = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


@dataclass
class Anexo:
    nome: str
    conteudo: bytes
    content_type: str


def _texto(valor, multilinha=False):
    if not isinstance(valor, str):
        return ""
    valor = _CONTROLE.sub("", valor.replace("\r\n", "\n").replace("\r", "\n"))
    return valor.strip() if multilinha else " ".join(valor.split())


def _nome_valido(valor, erros, chave, rotulo):
    if not valor:
        erros[chave] = f"Preencha {rotulo}."
    elif any(c.isdigit() for c in valor):
        erros[chave] = "O nome não pode ter números."
    elif len(valor) > MAX_NOME:
        erros[chave] = f"Texto muito longo (máximo {MAX_NOME} caracteres)."
    elif not _NOME.match(valor) or len(_LETRA.findall(valor)) < 3:
        erros[chave] = f"Preencha {rotulo}, só com letras (mínimo 3)."


def _celular_valido(valor, erros, chave):
    bruto = valor if isinstance(valor, str) else ""
    digitos = re.sub(r"\D", "", bruto)
    if re.sub(r"[\d\s()\-]", "", bruto) or len(digitos) != 11:
        erros[chave] = "Informe o celular completo com DDD: (21) 99999-9999."
        return ""
    return digitos


def _cpf_confere(cpf):
    if cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d) * peso for d, peso in zip(cpf[:tamanho], range(tamanho + 1, 1, -1)))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[tamanho]):
            return False
    return True


def _cpf_valido(valor, erros, chave):
    if not valor:
        erros[chave] = "Preencha o campo CPF."
    elif not (valor.isascii() and valor.isdigit()):
        erros[chave] = "O CPF deve ter só números, sem pontos nem traço."
    elif len(valor) != 11:
        erros[chave] = "O CPF deve ter 11 números."
    elif not _cpf_confere(valor):
        erros[chave] = "CPF inválido. Confira os números."


def _localizacao_valida(valor, erros, chave):
    if isinstance(valor, bool):
        valor = None
    if isinstance(valor, str) and valor.isdigit():
        valor = int(valor)
    if not isinstance(valor, int) or not localizacoes.existe(valor):
        erros[chave] = "Escolha a localização na lista."
        return None
    return valor


def _verdadeiro(valor):
    return valor is True or (isinstance(valor, str) and valor.lower() == "true")


def validar(dados):
    """Devolve (limpo, erros). Se erros não estiver vazio, limpo é None."""
    if not isinstance(dados, dict):
        return None, {"geral": "Pedido inválido."}
    erros = {}

    nome = _texto(dados.get("nome"))
    _nome_valido(nome, erros, "nome", "o seu nome completo")
    celular = _celular_valido(dados.get("celular"), erros, "celular")
    localizacao_id = _localizacao_valida(dados.get("localizacao_id"), erros, "localizacao_id")

    outra = _verdadeiro(dados.get("outra_pessoa"))
    outra_nome = outra_celular = ""
    outra_localizacao_id = None
    if outra:
        outra_nome = _texto(dados.get("outra_nome"))
        _nome_valido(outra_nome, erros, "outra_nome", "o nome da outra pessoa")
        outra_celular = _celular_valido(dados.get("outra_celular"), erros, "outra_celular")
        outra_localizacao_id = _localizacao_valida(
            dados.get("outra_localizacao_id"), erros, "outra_localizacao_id"
        )

    motivo = _texto(dados.get("motivo"))
    if motivo not in MOTIVOS:
        erros["motivo"] = "Selecione o motivo."
    sub_motivo = _texto(dados.get("sub_motivo"))
    opcoes = SUBMOTIVOS.get(motivo)
    if opcoes:
        if sub_motivo not in opcoes:
            erros["sub_motivo"] = "Marque uma opção."
    else:
        sub_motivo = ""

    campos = {}
    descricao = ""
    if motivo == "Criação de Login":
        if sub_motivo in CAMPOS_LOGIN:
            brutos = dados.get("campos") if isinstance(dados.get("campos"), dict) else {}
            for rotulo in CAMPOS_LOGIN[sub_motivo]:
                chave = f"campos.{rotulo}"
                valor = _texto(brutos.get(rotulo))
                if rotulo == "Nome Completo":
                    _nome_valido(valor, erros, chave, "o campo Nome Completo")
                elif rotulo == "CPF":
                    _cpf_valido(valor, erros, chave)
                elif not valor:
                    erros[chave] = f"Preencha o campo {rotulo}."
                elif len(valor) > MAX_CAMPO:
                    erros[chave] = f"Texto muito longo (máximo {MAX_CAMPO} caracteres)."
                elif rotulo == "Email" and not _EMAIL.match(valor):
                    erros[chave] = "Informe um e-mail válido."
                campos[rotulo] = valor
    else:
        descricao = _texto(dados.get("descricao"), multilinha=True)
        if len(descricao) < 5:
            erros["descricao"] = "Descreva o problema."
        elif len(descricao) > MAX_DESCRICAO:
            erros["descricao"] = f"Texto muito longo (máximo {MAX_DESCRICAO} caracteres)."

    token = dados.get("token")
    if token is not None and not (isinstance(token, str) and _TOKEN.match(token)):
        erros["token"] = "Identificador do envio inválido."

    if erros:
        return None, erros
    return {
        "token": token,
        "nome": nome,
        "celular": celular,
        "localizacao_id": localizacao_id,
        "outra_pessoa": outra,
        "outra_nome": outra_nome,
        "outra_celular": outra_celular,
        "outra_localizacao_id": outra_localizacao_id,
        "motivo": motivo,
        "sub_motivo": sub_motivo,
        "campos": campos,
        "descricao": descricao,
    }, {}


def _tipo_do_conteudo(conteudo):
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if conteudo[:6] in (b"GIF87a", b"GIF89a"):
        return "gif", "image/gif"
    if conteudo.startswith(b"%PDF-"):
        return "pdf", "application/pdf"
    return None, None


def validar_anexos(arquivos):
    """arquivos: lista de (nome_original, bytes). Devolve (anexos, erro)."""
    if len(arquivos) > MAX_ANEXOS:
        return [], f"Envie no máximo {MAX_ANEXOS} arquivos."
    if sum(len(conteudo) for _, conteudo in arquivos) > MAX_BYTES_ANEXOS:
        return [], "Os anexos somam mais de 15 MB."
    anexos, usados = [], set()
    for nome_original, conteudo in arquivos:
        extensao, content_type = _tipo_do_conteudo(conteudo)
        if not extensao:
            return [], "Anexo inválido: envie apenas fotos (JPG, PNG, GIF) ou PDF."
        base = os.path.splitext(os.path.basename((nome_original or "").replace("\\", "/")))[0]
        base = re.sub(r"[^\w\-. ]", "_", base).strip(" ._")[:60] or "anexo"
        nome, n = f"{base}.{extensao}", 1
        while nome in usados:
            n += 1
            nome = f"{base}-{n}.{extensao}"
        usados.add(nome)
        anexos.append(Anexo(nome=nome, conteudo=conteudo, content_type=content_type))
    return anexos, ""
