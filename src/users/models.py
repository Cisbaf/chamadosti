from django.db import models


class UserRequest(models.Model):
    """Cadastro por celular, usado só para preencher nome e localização sozinho."""

    name_applicant = models.CharField(max_length=200)
    number_applicant = models.CharField(max_length=200, unique=True)
    # Caminho completo da localização (ex.: "CAXIAS > UPA SARAPUI"). Em cadastros
    # antigos ainda está no formato "CAXIAS-UPA SARAPUI" e location_id fica vazio.
    location_applicant = models.CharField(max_length=200)
    location_id = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name_applicant
