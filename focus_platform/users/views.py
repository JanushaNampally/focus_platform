from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import UserProfile

from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to Focus Platform")

def onboarding(request):
    if request.method == "POST":
        goal = request.POST.get("goal")
        daily_target = request.POST.get("daily_target_minutes")

        user = User.objects.first()

        UserProfile.objects.create(
            user=user,
            goal=goal,
            daily_target_minutes=daily_target
        )

        return redirect("success")

    return render(request, "users/onboarding.html")


def success(request):
    return render(request, "users/success.html")