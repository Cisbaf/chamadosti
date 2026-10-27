"""Cliente da API REST do GLPI (apirest.php).

Autenticação só por token: App-Token do cliente de API + user_token do usuário
de serviço. Cada abertura de chamado usa uma sessão curta
(initSession -> Ticket -> Document* -> killSession) com prazo total único.
"""
import json
import logging
import time
from dataclasses import dataclass, field

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class GlpiErro(Exception):
    """Falha ao falar com o GLPI.

    tipo: config | conexao | timeout | auth | api
    """

    def __init__(self, mensagem, tipo="api", status=None):
        super().__init__(mensagem)
        self.tipo = tipo
        self.status = status


@dataclass
class ResultadoAbertura:
    ticket_id: int
    anexos_falhos: list = field(default_factory=list)
    titulo_provisorio: bool = False


class GlpiClient:
    def __init__(self, url, app_token, user_token, timeout=20, requesttype_id=None):
        if not (url and app_token and user_token):
            raise GlpiErro(
                "GLPI_API_URL, GLPI_APP_TOKEN e GLPI_USER_TOKEN precisam estar configurados",
                tipo="config",
            )
        self.url = url.rstrip("/")
        self.app_token = app_token
        self.user_token = user_token
        self.timeout = timeout
        self.requesttype_id = requesttype_id
        self._http = requests.Session()
        self._sessao = None
        self._limite = None
        self._usuario_id = None
        self._usuario_consultado = False

    @classmethod
    def das_configuracoes(cls, timeout_extra=0):
        return cls(
            settings.GLPI_API_URL,
            settings.GLPI_APP_TOKEN,
            settings.GLPI_USER_TOKEN,
            timeout=settings.GLPI_TIMEOUT + timeout_extra,
            requesttype_id=settings.GLPI_REQUESTTYPE_ID,
        )

    def __enter__(self):
        self._limite = time.monotonic() + self.timeout
        self.abrir_sessao()
        return self

    def __exit__(self, *exc):
        self.fechar_sessao()
        self._http.close()

    def _requisicao(self, metodo, caminho, **kwargs):
        restante = self._limite - time.monotonic() if self._limite else self.timeout
        if restante <= 0:
            raise GlpiErro("Prazo total da chamada ao GLPI esgotado", tipo="timeout")
        headers = {"App-Token": self.app_token}
        if self._sessao:
            headers["Session-Token"] = self._sessao
        headers.update(kwargs.pop("headers", {}))
        try:
            resp = self._http.request(
                metodo,
                f"{self.url}/{caminho}",
                headers=headers,
                timeout=(min(5, restante), restante),
                **kwargs,
            )
        except requests.Timeout as exc:
            raise GlpiErro("Tempo esgotado falando com o GLPI", tipo="timeout") from exc
        except requests.ConnectionError as exc:
            raise GlpiErro("Não foi possível conectar ao GLPI", tipo="conexao") from exc
        except requests.RequestException as exc:
            raise GlpiErro(f"Erro de rede com o GLPI: {type(exc).__name__}", tipo="conexao") from exc

        if resp.status_code >= 400:
            codigo, texto = self._ler_erro(resp)
            auth = resp.status_code == 401 or any(
                parte in codigo for parte in ("TOKEN", "LOGIN", "NOT_ALLOWED_IP")
            )
            raise GlpiErro(
                f"HTTP {resp.status_code} {codigo}: {texto}".strip(),
                tipo="auth" if auth else "api",
                status=resp.status_code,
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise GlpiErro("Resposta do GLPI não é JSON", tipo="api", status=resp.status_code) from exc

    @staticmethod
    def _ler_erro(resp):
        # O GLPI responde erros como ["ERROR_CODE", "mensagem"].
        try:
            corpo = resp.json()
            if isinstance(corpo, list) and corpo:
                return str(corpo[0]), str(corpo[1] if len(corpo) > 1 else "")[:300]
        except ValueError:
            pass
        return "", resp.text[:300]

    def abrir_sessao(self):
        corpo = self._requisicao(
            "GET", "initSession", headers={"Authorization": f"user_token {self.user_token}"}
        )
        token = corpo.get("session_token") if isinstance(corpo, dict) else None
        if not token:
            raise GlpiErro("GLPI não devolveu session_token", tipo="auth")
        self._sessao = token

    def fechar_sessao(self):
        if not self._sessao:
            return
        try:
            self._limite = max(self._limite or 0, time.monotonic() + 3)
            self._requisicao("GET", "killSession")
        except GlpiErro as exc:
            log.warning("killSession falhou: %s", exc)
        finally:
            self._sessao = None

    def usuario_id(self):
        """Id do usuário de serviço no GLPI (o dono do user_token). None se não der para saber."""
        if not self._usuario_consultado:
            self._usuario_consultado = True
            try:
                corpo = self._requisicao("GET", "getFullSession")
                self._usuario_id = int(corpo["session"]["glpiID"])
            except (GlpiErro, KeyError, TypeError, ValueError) as exc:
                log.warning("Não foi possível descobrir o usuário de serviço do GLPI: %s", exc)
        return self._usuario_id

    def criar_ticket(self, dados):
        entrada = dict(dados)
        # Pela interface o GLPI já marca quem abre como requerente; pela API é preciso dizer.
        requerente = self.usuario_id()
        if requerente:
            entrada["_users_id_requester"] = requerente
        if self.requesttype_id:
            entrada["requesttypes_id"] = self.requesttype_id
        corpo = self._requisicao("POST", "Ticket", json={"input": entrada})
        ticket_id = corpo.get("id") if isinstance(corpo, dict) else None
        if not ticket_id:
            raise GlpiErro("GLPI não devolveu o id do chamado", tipo="api")
        return int(ticket_id)

    def renomear(self, ticket_id, titulo):
        self._requisicao("PUT", f"Ticket/{ticket_id}", json={"input": {"name": titulo}})

    def anexar(self, ticket_id, nome, conteudo, content_type):
        manifesto = json.dumps(
            {"input": {"name": nome, "_filename": [nome], "itemtype": "Ticket", "items_id": ticket_id}}
        )
        arquivos = {
            "uploadManifest": (None, manifesto, "application/json"),
            "filename[0]": (nome, conteudo, content_type),
        }
        return self._requisicao("POST", "Document", files=arquivos)

    def abrir_chamado(self, dados_ticket, anexos=(), titulo_final=None):
        """Cria o ticket e anexa os arquivos. Falha de anexo não desfaz o chamado.

        titulo_final: função(ticket_id) -> título que leva o número do chamado. O número
        só existe depois da criação, então o título é trocado logo em seguida; se a troca
        falhar, o chamado continua aberto com o título provisório.
        """
        ticket_id = self.criar_ticket(dados_ticket)
        resultado = ResultadoAbertura(ticket_id=ticket_id)
        if titulo_final:
            try:
                self.renomear(ticket_id, titulo_final(ticket_id))
            except GlpiErro as exc:
                resultado.titulo_provisorio = True
                log.warning("Título do chamado %s não foi atualizado: %s", ticket_id, exc)
        for anexo in anexos:
            try:
                self.anexar(ticket_id, anexo.nome, anexo.conteudo, anexo.content_type)
            except GlpiErro as exc:
                log.warning("Anexo %s do chamado %s falhou: %s", anexo.nome, ticket_id, exc)
                resultado.anexos_falhos.append(anexo.nome)
        return resultado
