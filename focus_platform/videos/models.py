from django.db import models

class Video(models.Model):
    title = models.CharField(max_length=255)
    youtube_id = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    score = models.FloatField(default=0)

    def __str__(self):
        return self.title