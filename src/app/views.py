from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from chamados import localizacoes, validacao


@ensure_csrf_cookie
def index(request):
    return render(request, 'index.html', {
        'localizacoes': localizacoes.LOCALIZACOES,
        'motivos': validacao.MOTIVOS,
        'submotivos': validacao.SUBMOTIVOS,
        'campos_login': validacao.CAMPOS_LOGIN,
        'ano': timezone.localdate().year,
    })
