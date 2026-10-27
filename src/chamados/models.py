from django.db import models


class Envio(models.Model):
    """Controle de envio duplicado (duplo clique, reenvio após resposta perdida).

    Guarda só o identificador gerado pelo navegador e o número do chamado; nenhum
    dado pessoal.
    """

    PROCESSANDO = "processando"
    ABERTO = "aberto"

    token = models.CharField(max_length=64, unique=True)
    estado = models.CharField(max_length=12, default=PROCESSANDO)
    ticket_id = models.IntegerField(null=True, blank=True)
    anexos_falhos = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
