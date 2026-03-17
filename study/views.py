from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404
from .models import Subject, Video

def subject_detail(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    videos = Video.objects.filter(subject=subject)

    return render(request, "study/subject_detail.html", {
        "subject": subject,
        "videos": videos
    })

from focus.models import FocusSession
from django.utils import timezone

def video_watch(request, video_id):
    video = get_object_or_404(Video, id=video_id)

    # Create FocusSession when video opened
    session = FocusSession.objects.create(
        user=request.user,
        subject=video.subject,
        video=video
    )

    return render(request, "study/video_watch.html", {
        "video": video,
        "session_id": session.id
    })
from videos.models import Video

def video_feed(request, topic_id):
    videos = Video.objects.filter(topic_id=topic_id).order_by('-ai_score')[:5]

    return render(request, "study/video_watch.html", {
        "videos": videos
    })