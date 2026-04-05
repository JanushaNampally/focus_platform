from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    goal = models.CharField(max_length=255)
    daily_target_minutes = models.IntegerField(default=60)

    def __str__(self):
        return f"{self.user.username} - {self.goal}"