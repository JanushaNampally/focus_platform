"""
ai_engine/urls.py - API endpoints for AI engine
"""

from django.urls import path
from . import views

app_name = 'ai_engine'

urlpatterns = [
    # Video recommendations
    path('videos/recommended/', views.get_personalized_recommendations, name='get_recommendations'),
    path('videos/trending/', views.get_trending_videos, name='get_trending'),
    path('videos/<int:video_id>/save/', views.save_video, name='save_video'),
    
    # Watch history
    path('watch-history/update/', views.update_watch_history, name='update_watch_history'),
    
    # Focus sessions
    path('focus-session/end/', views.end_focus_session, name='end_focus_session'),
    
    # User stats
    path('user/<int:user_id>/streak/', views.get_user_streak, name='get_streak'),
    path('user/<int:user_id>/achievements/', views.get_user_achievements, name='get_achievements'),
    
    # ML predictions
    path('user/risk/', views.predict_user_risk, name='predict_risk'),
]
