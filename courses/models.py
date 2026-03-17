from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Subject(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="subjects"
    )
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Topic(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name