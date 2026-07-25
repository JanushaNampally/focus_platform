from django.db import models
from django.contrib.auth.models import User


class Video(models.Model):
    title = models.CharField(max_length=255)
    youtube_id = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)

    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(default=10)

    ai_score = models.FloatField(default=0)

    def __str__(self):
        return self.title
    
    
    


class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)

    watched_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} watched {self.video.title}"