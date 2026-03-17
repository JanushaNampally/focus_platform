
from django.shortcuts import render, get_object_or_404
from .models import Course, Subject


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    subjects = Subject.objects.filter(course=course)

    return render(request, "courses/course_detail.html", {
        "course": course,
        "subjects": subjects
    })
