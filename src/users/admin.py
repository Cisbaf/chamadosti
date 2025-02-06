from django.contrib import admin
from .models import UserRequest

class UserRequestAdmin(admin.ModelAdmin):
    pass


admin.site.register(UserRequest, UserRequestAdmin)