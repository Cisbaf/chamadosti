from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import UserRequest

@csrf_exempt
def get_users_of_number(request, phone):
    user = get_object_or_404(UserRequest, number_applicant=phone)
    return JsonResponse(user.json(), safe=False)
    