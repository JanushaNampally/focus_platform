from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Q
from datetime import timedelta
import json

from users.models import Profile
from courses.models import Course, Subject
from videos.models import Video
from tracking.models import WatchHistory, StreakTracking, UserBehaviorMetrics
from ai_engine.recommendations import HybridRecommendationEngine


def landing(request):
    """Landing page for unauthenticated users"""
    return render(request, "core/landing.html")


@login_required
def dashboard(request):
    """
    AI-Powered Dashboard with personalized recommendations
    and gamification features
    """
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # Redirect to goal setup if not completed
    if not profile.goal_reason:
        return redirect("users:goal_setup")
    
    # Get user's enrolled courses and subjects
    courses = Course.objects.all()
    subjects = Subject.objects.all()
    
    # Calculate activity data for last 7 days (for chart)
    today = timezone.now().date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    
    activity_data = []
    for day in last_7_days:
        watch_time = WatchHistory.objects.filter(
            user=request.user,
            date=day
        ).aggregate(
            total=Sum('watch_duration_seconds')
        )['total'] or 0
        
        activity_data.append(round(watch_time / 3600, 1))  # Convert to hours
    
    # Get subject progress
    subject_progress = []
    for subject in subjects:
        total_videos = Video.objects.filter(
            topic__subject=subject
        ).count()
        
        watched_videos = WatchHistory.objects.filter(
            user=request.user,
            video__topic__subject=subject
        ).values('video').distinct().count()
        
        completion_percentage = (watched_videos / total_videos * 100) if total_videos > 0 else 0
        
        subject_progress.append({
            'name': subject.name,
            'completion_percentage': round(completion_percentage, 1),
            'watched': watched_videos,
            'total': total_videos
        })
    
    # Check if daily challenge is completed
    today_watch_count = WatchHistory.objects.filter(
        user=request.user,
        date=today
    ).values('video').distinct().count()
    
    challenge_completed = today_watch_count >= 3
    
    context = {
        'profile': profile,
        'courses': courses,
        'subjects': subject_progress,
        'challenge_completed': challenge_completed,
        'activity_json': json.dumps({
            'labels': [d.strftime('%a') for d in last_7_days],
            'data': activity_data
        }),
    }
    
    # Use new AI-powered dashboard template
    return render(request, 'core/dashboard_new.html', context)    
    context = {
        'courses': courses,
        'videos': videos,
        'profile': profile,
    }
    return render(request, 'core/dashboard.html', context)