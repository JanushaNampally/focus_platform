from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            return render(request, "users/login.html", {"error": "Invalid username or password"})

    return render(request, "users/login.html")


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        User.objects.create_user(username=username, email=email, password=password)

        return redirect('user_login')


    return render(request, "users/register.html")
from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect("dashboard")

from django.contrib.auth.decorators import login_required
from .models import Profile

@login_required
def goal_setup(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        goal = request.POST.get("goal_reason")
        profile.goal_reason = goal
        profile.save()
        return redirect("dashboard")

    return render(request, "users/goal_setup.html")