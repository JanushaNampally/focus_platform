from django.urls import path
from .views import subject_detail, video_watch

urlpatterns = [
    path('<int:subject_id>/', subject_detail, name='subject_detail'),
    path('video/<int:video_id>/', video_watch, name='video_watch'),

]