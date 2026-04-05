from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class FocusSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.IntegerField()
    completed = models.BooleanField(default=False)