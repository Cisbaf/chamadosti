import django, os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from users.models import UserRequest


print(UserRequest.objects.get(number_applicant="2199192033"))