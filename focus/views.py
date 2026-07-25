from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import FocusSession


def timer(request):
    return render(request, "focus/timer.html")


def complete_session(request):
    user = User.objects.first()

    FocusSession.objects.create(
        user=user,
        duration_minutes=25,
        completed=True
    )

    return redirect("/users/dashboard/")