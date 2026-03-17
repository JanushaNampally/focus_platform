from django.db import models
from courses.models import Subject

class Video(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="videos"
    )
    title = models.CharField(max_length=255)
    url = models.URLField()
    duration = models.IntegerField(default=0)  # in seconds

    def __str__(self):
        return self.title