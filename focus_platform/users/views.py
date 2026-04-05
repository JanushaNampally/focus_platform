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

        return redirect("dashboard")

    return render(request, "users/onboarding.html")


def success(request):
    return render(request, "users/success.html")

def dashboard(request):
    profile = UserProfile.objects.first()
    total_sessions = FocusSession.objects.filter(completed=True).count()

    context = {
        "profile": profile,
        "total_sessions": total_sessions
    }

    return render(request, "users/dashboard.html", context)