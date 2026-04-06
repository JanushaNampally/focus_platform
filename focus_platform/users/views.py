from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.http import HttpResponse
from datetime import date, timedelta

from .models import UserProfile
from focus.models import FocusSession
from ai_engine.ranking import calculate_video_score
from videos.models import Video, WatchHistory
from ai_engine.churn_predictor import predict_churn

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
    sessions = FocusSession.objects.filter(completed=True)
    total_videos = Video.objects.count()
    total_sessions = sessions.count()

    today = date.today()
    streak = 0

    for i in range(30):
        check_date = today - timedelta(days=i)

        if sessions.filter(session_date=check_date).exists():
            streak += 1
        else:
            break

    consistency_score = min(100, streak * 10)

    if churn_risk > 0.7:
        motivation = "High risk detected. Start a quick 10-minute focus session now."
    elif streak >= 5:
        motivation = "Excellent discipline! Keep the momentum."
    elif streak >= 2:
        motivation = "Good consistency. Stay focused."
    else:
        motivation = "Start your streak today."
    churn_risk = predict_churn(
        streak,
        total_sessions,
        days_inactive
    )
    # DAY 6 VIDEO RECOMMENDATION LOGIC
    user_goal = profile.goal if profile else ""

    watched_topics = WatchHistory.objects.filter(
        user=User.objects.first()
    ).values_list("video__topic", flat=True)

    ranked_videos = sorted(
        video,
        key=lambda video: calculate_video_score(video, user_goal)
        + (2000 if video.topic in watched_topics else 0),
        reverse=True
    )

  
    top_videos = ranked_videos[:3]

    context = {
        "profile": profile,
        "total_sessions": total_sessions,
        "streak": streak,
        "consistency_score": consistency_score,
        "motivation": motivation,
        "top_videos": top_videos,
        "total_videos": total_videos,
    }

    return render(request, "users/dashboard.html", context)