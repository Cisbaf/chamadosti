from django.urls import path

from . import views

urlpatterns = [
    path("chamados", views.criar_chamado),
    path("solicitante/<str:celular>", views.solicitante),
]
