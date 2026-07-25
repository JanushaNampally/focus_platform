from django.urls import path
from .views import watch_video, fetch_live_videos

urlpatterns = [
    path('watch/<int:video_id>/', watch_video, name='watch_video'),
    path('fetch-live/', fetch_live_videos, name='fetch_live_videos'),
]