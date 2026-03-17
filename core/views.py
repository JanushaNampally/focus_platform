from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from users.models import Profile
from courses.models import Course
from videos.models import Video

def landing(request):
    return render(request, "core/landing.html")

@login_required
def dashboard(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if not profile.goal_reason:
        return redirect("users:goal_setup")
    
    courses = Course.objects.all()
    videos = Video.objects.select_related('topic', 'topic__subject', 'topic__subject__course')

    context = {
        'courses': courses,
        'videos': videos,
        'profile': profile,
    }
    return render(request, 'core/dashboard.html', context)