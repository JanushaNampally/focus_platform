from django.db import models
from django.contrib.auth.models import User


class FocusSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.IntegerField(default=25)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.duration_minutes} min"