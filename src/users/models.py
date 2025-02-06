from django.db import models
from django_celery_results.models import TaskResult

class UserRequest(models.Model):
    name_applicant = models.CharField(max_length=200)
    number_applicant = models.CharField(max_length=200, unique=True)
    location_applicant = models.CharField(max_length=200)
    
    
    def get_location(self):
        return self.location_applicant.split('-')[0]
    
    def get_base(self):
        base_split = self.location_applicant.split('-')
        if len(base_split) > 1:
            return base_split[1]
        return None

    def json(self):
        return {
            "name": self.name_applicant,
            "number": self.number_applicant,
            "location": self.get_location(),
            "base": self.get_base()
        }

    def __str__(self) -> str:
        return self.name_applicant
    