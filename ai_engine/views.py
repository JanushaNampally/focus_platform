"""
ai_engine/views.py - AI Engine API Views
Connects frontend with AI/ML engines
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, F, Sum
from django.utils import timezone
from datetime import timedelta
import json

from users.models import Profile
from videos.models import Video
from tracking.models import (
    WatchHistory, AIRecommendation, StreakTracking, 
    UserBehaviorMetrics
)
from .nlp import get_sentiment_analyzer
from .ranking import VideoRankingEngine
from .recommendations import HybridRecommendationEngine


@login_required
@require_http_methods(["GET"])
def get_personalized_recommendations(request):
    """
    Get AI-personalized video recommendations for the user
    Uses hybrid recommendation system
    """
    try:
        user = request.user
        profile = Profile.objects.get(user=user)
        topic_id = request.GET.get('topic_id')
        limit = int(request.GET.get('limit', 10))
        
        # Get recommendation engine
        recommender = HybridRecommendationEngine()
        
        # Get recommendations
        if topic_id:
            recommendations = recommender.get_recommendations(
                user_id=user.id,
                topic_id=int(topic_id),
                top_n=limit
            )
        else:
            recommendations = recommender.get_recommendations(
                user_id=user.id,
                top_n=limit
            )
        
        # Format response
        video_list = []
        for rec in recommendations:
            video = rec['video']
            video_list.append({
                'id': video.id,
                'title': video.title,
                'channel_name': video.channel_name,
                'thumbnail_url': video.thumbnail_url,
                'duration_seconds': video.duration_seconds,
                'view_count': video.view_count,
                'like_count': video.like_count,
                'ai_score': round(video.ai_score, 2),
                'reason': rec.get('reason', 'Recommended for you'),
            })
        
        # Save recommendation for analytics
        for i, video in enumerate(video_list[:3]):  # Top 3
            AIRecommendation.objects.create(
                user=user,
                video_id=video['id'],
                recommendation_rank=i + 1,
                reason=video['reason']
            )
        
        return JsonResponse({
            'status': 'success',
            'videos': video_list,
            'total': len(video_list)
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET"])
def get_trending_videos(request):
    """
    Get trending videos (top videos from last 7 days)
    """
    try:
        limit = int(request.GET.get('limit', 10))
        
        # Get videos trending in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        
        videos = Video.objects.filter(
            updated_at__gte=week_ago
        ).order_by('-ai_score')[:limit]
        
        video_list = []
        for video in videos:
            video_list.append({
                'id': video.id,
                'title': video.title,
                'channel_name': video.channel_name,
                'thumbnail_url': video.thumbnail_url,
                'duration_seconds': video.duration_seconds,
                'view_count': video.view_count,
                'like_count': video.like_count,
                'ai_score': round(video.ai_score, 2),
            })
        
        return JsonResponse({
            'status': 'success',
            'videos': video_list
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET"])
def get_user_streak(request, user_id):
    """
    Get user's current streak information
    """
    try:
        user = get_object_or_404(request.user.__class__, id=user_id)
        profile = get_object_or_404(Profile, user=user)
        
        streak = StreakTracking.objects.filter(user=user).latest('date')
        
        return JsonResponse({
            'status': 'success',
            'streak': streak.current_streak,
            'longest_streak': streak.longest_streak,
            'points_today': streak.points_earned_today,
            'last_active': streak.date.isoformat()
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET"])
def get_user_achievements(request, user_id):
    """
    Get user's unlocked achievements/badges
    """
    try:
        user = get_object_or_404(request.user.__class__, id=user_id)
        profile = get_object_or_404(Profile, user=user)
        
        achievements = []
        
        # Starter Badge - Complete first session
        if profile.total_watch_hours > 0:
            achievements.append({
                'id': 'starter',
                'name': 'Starter',
                'icon': '🚀',
                'description': 'Complete your first focus session',
                'unlocked': True
            })
        
        # Learner Badge - 7-day streak
        if profile.current_streak >= 7:
            achievements.append({
                'id': 'learner',
                'name': 'Learner',
                'icon': '📚',
                'description': 'Maintain a 7-day streak',
                'unlocked': True,
                'new': True
            })
        
        # Master Badge - 30-day streak
        if profile.current_streak >= 30:
            achievements.append({
                'id': 'master',
                'name': 'Master',
                'icon': '🎓',
                'description': 'Maintain a 30-day streak',
                'unlocked': True,
                'new': True
            })
        
        # Dedicated Badge - 50+ hours
        if profile.total_watch_hours >= 50:
            achievements.append({
                'id': 'dedicated',
                'name': 'Dedicated',
                'icon': '⭐',
                'description': 'Watch 50+ hours',
                'unlocked': True,
                'new': True
            })
        
        # Excellence Badge - 100+ hours
        if profile.total_watch_hours >= 100:
            achievements.append({
                'id': 'excellence',
                'name': 'Excellence',
                'icon': '🏆',
                'description': 'Watch 100+ hours',
                'unlocked': True
            })
        
        new_achievements = [a for a in achievements if a.get('new', False)]
        
        return JsonResponse({
            'status': 'success',
            'achievements': achievements,
            'new_achievements': new_achievements
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def save_video(request):
    """
    Save video to user's saved list
    """
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        
        video = get_object_or_404(Video, id=video_id)
        profile = Profile.objects.get(user=request.user)
        
        # Toggle save status
        if video in profile.saved_videos.all():
            profile.saved_videos.remove(video)
            saved = False
        else:
            profile.saved_videos.add(video)
            saved = True
        
        return JsonResponse({
            'status': 'success',
            'saved': saved,
            'message': 'Video saved!' if saved else 'Video removed'
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def update_watch_history(request):
    """
    Update watch history with current progress
    """
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        watch_time = int(data.get('watch_time', 0))
        
        video = get_object_or_404(Video, id=video_id)
        
        history, created = WatchHistory.objects.get_or_create(
            user=request.user,
            video=video,
            date=timezone.now().date()
        )
        
        history.watch_duration_seconds += watch_time
        history.last_watched = timezone.now()
        history.save()
        
        # Update user profile stats
        profile = Profile.objects.get(user=request.user)
        total_seconds = WatchHistory.objects.filter(
            user=request.user
        ).aggregate(total=Sum('watch_duration_seconds'))['total'] or 0
        profile.total_watch_hours = total_seconds / 3600
        profile.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Watch history updated'
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def end_focus_session(request):
    """
    End a focus session and award points
    """
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        reason = data.get('reason', 'completed')
        
        from focus.models import FocusSession
        session = get_object_or_404(FocusSession, id=session_id, user=request.user)
        
        session.end_time = timezone.now()
        session.duration_seconds = int(
            (session.end_time - session.start_time).total_seconds()
        )
        
        # Award points based on completion
        if reason == 'completed':
            points = min(100, int(session.duration_seconds / 15))
            session.completed = True
            streak_change = 1
        else:
            points = max(10, int(session.duration_seconds / 60))
            session.completed = False
            streak_change = -1
        
        session.points_earned = points
        session.save()
        
        # Update streak
        profile = Profile.objects.get(user=request.user)
        profile.total_points += points
        profile.current_streak = max(0, profile.current_streak + streak_change)
        profile.save()
        
        return JsonResponse({
            'status': 'success',
            'points_earned': points,
            'streak_updated': profile.current_streak,
            'message': 'Session saved!'
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
def predict_user_risk(request):
    """
    ML: Predict user dropout risk
    """
    try:
        profile = Profile.objects.get(user=request.user)
        
        # Get user behavior metrics
        metrics = UserBehaviorMetrics.objects.filter(
            user=request.user
        ).order_by('-date')[:30]  # Last 30 days
        
        if not metrics:
            return JsonResponse({
                'status': 'insufficient_data',
                'message': 'Not enough data for prediction'
            })
        
        # Simple risk calculation
        avg_watch_time = sum(m.daily_watch_minutes for m in metrics) / len(metrics)
        recent_activity = metrics.filter(
            date__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Risk score (0-100)
        risk_score = 100 - min(100, (avg_watch_time / 30) * 100)
        risk_score *= (7 - recent_activity) / 7  # Reduce if recently active
        
        if risk_score > 75:
            risk_level = 'HIGH'
        elif risk_score > 50:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return JsonResponse({
            'status': 'success',
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'recommendation': f'Your dropout risk is {risk_level}. Keep up your consistent learning!'
        })
    
    except Profile.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Profile not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
