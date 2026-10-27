"""Localizações do GLPI, lidas uma vez do arquivo que acompanha o app.

Não há sincronização com o GLPI: se a TI criar ou renomear uma localização,
atualize data/localizacoes-glpi.json (id do GLPI + caminho completo).
"""
import json
import unicodedata
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "data" / "localizacoes-glpi.json"

with open(ARQUIVO, encoding="utf-8") as _f:
    LOCALIZACOES = json.load(_f)

_POR_ID = {item["id"]: item for item in LOCALIZACOES}


def normalizar(texto):
    sem_acento = unicodedata.normalize("NFD", str(texto or ""))
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.lower().split())


_POR_CAMINHO = {normalizar(item["caminho"]): item["id"] for item in LOCALIZACOES}


def existe(localizacao_id):
    return localizacao_id in _POR_ID


def caminho(localizacao_id):
    item = _POR_ID.get(localizacao_id)
    return item["caminho"] if item else None


def id_do_caminho_antigo(texto):
    """Converte o formato antigo do cadastro ("CAXIAS-UPA SARAPUI") no id atual."""
    if not texto:
        return None
    partes = [p.strip() for p in str(texto).split("-", 1)]
    return _POR_CAMINHO.get(normalizar(" > ".join(p for p in partes if p)))
