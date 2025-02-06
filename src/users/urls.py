from django.urls import path
from users import views

urlpatterns = [
    path("get_of_number/<str:phone>", views.get_users_of_number)
]