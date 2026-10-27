from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from chamados.descricao import PADROES_TICKET
from helpers.glpi_client import GlpiClient, GlpiErro

# PNG 1x1 transparente
PNG_MINIMO = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0\x00\x00\x00\x00IEND\xaeB`\x82"
)


class Anexo:
    nome = "teste.png"
    conteudo = PNG_MINIMO
    content_type = "image/png"


class Command(BaseCommand):
    help = "Cria um chamado de teste no GLPI configurado no .env (com um anexo) para validar a integração."

    def add_arguments(self, parser):
        parser.add_argument("--sim", action="store_true", help="Confirma que o GLPI do .env é o de TESTE.")
        parser.add_argument("--localizacao", type=int, default=59, help="id da localização (padrão: 59)")

    def handle(self, *args, **opcoes):
        self.stdout.write(f"GLPI: {settings.GLPI_API_URL}")
        if not opcoes["sim"]:
            raise CommandError("Confira o endereço acima e rode de novo com --sim se for o GLPI de TESTE.")

        ticket = {
            **PADROES_TICKET,
            "name": "[TESTE] testar_glpi",
            "content": "<p>Chamado criado pelo comando testar_glpi. Pode apagar.</p>",
            "locations_id": opcoes["localizacao"],
        }
        try:
            with GlpiClient.das_configuracoes() as glpi:
                resultado = glpi.abrir_chamado(ticket, [Anexo()])
        except GlpiErro as exc:
            raise CommandError(f"Falhou ({exc.tipo}): {exc}")
        self.stdout.write(self.style.SUCCESS(f"Chamado {resultado.ticket_id} criado."))
        if resultado.anexos_falhos:
            raise CommandError(f"Chamado criado, mas o anexo falhou: {resultado.anexos_falhos}")
        self.stdout.write(self.style.SUCCESS("Anexo enviado."))
