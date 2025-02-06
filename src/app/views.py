from django.shortcuts import render
from users.models import UserRequest
from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from helpers.form_register import validate_form
from app.tasks import glpi_register
import json

def index(request):
    return render(request, 'index.html')

@csrf_exempt
def register(request):
    data_register = json.loads(request.POST.get("data"))
    filesForm = request.FILES.getlist('files')
    if len(filesForm) > 0:
        files = {}
        for file in filesForm:
            files[file.name] = file.read()
    else:
        files = None
    data_form = validate_form(data_register)
    glpi_register.delay(data_register, files)
    try:
        UserRequest.objects.get(number_applicant=data_form.contact)
    except:
            UserRequest.objects.create(
            name_applicant = data_register['name'],
            number_applicant = data_register['phone'],
            location_applicant = data_form.unity,
        )
    return HttpResponse(status=200)