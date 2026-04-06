from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect
from django.contrib.auth.models import User
from .models import Video, WatchHistory

from django.http import HttpResponse

def watch_video(request, video_id):
    user = User.objects.first()
    video = Video.objects.get(id=video_id)

    WatchHistory.objects.create(
        user=user,
        video=video,
        completed=True
    )

    return redirect("/users/dashboard/")


from django.http import HttpResponse
from ai_engine.youtube_fetcher import save_videos_to_db_for_topics


def fetch_live_videos(request):
    total_saved = save_videos_to_db_for_topics()

    return HttpResponse(
        f"{total_saved} new educational videos fetched successfully"
    )