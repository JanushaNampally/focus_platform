from django.db import models


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