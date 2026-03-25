"""
Hybrid Recommendation Engine

Combines 4 recommendation strategies:
1. Content-Based: Similar videos to what user watched
2. Collaborative: What similar users found helpful
3. Behavior-Based: Videos matching user's learning pace
4. Trending: Popular videos in user's topics this week

Result: Personalized list with diversity and serendipity
"""

import logging
from typing import List, Tuple, Dict
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q, F

from videos.models import Video
from tracking.models import WatchHistory, AIRecommendation

logger = logging.getLogger('ai_engine')


class RecommendationEngine:
    """
    Hybrid recommendation system for personalized video suggestions
    
    Strategy Mix (by weight):
    - Content-Based (40%): Videos similar to your watch history
    - Collaborative (30%): Videos other similar users completed
    - Behavior-Based (20%): Pace and difficulty aligned with yours
    - Trending (10%): New popular content in your topics
    """
    
    # Strategy weights
    STRATEGY_WEIGHTS = {
        'CONTENT': 0.40,
        'COLLABORATIVE': 0.30,
        'BEHAVIOR': 0.20,
        'TRENDING': 0.10
    }
    
    def __init__(self, user):
        """
        Initialize recommendation engine for a user
        
        Args:
            user: Django User object
        """
        self.user = user
        self.profile = user.focus_profile
        self.logger = logger
    
    def generate_recommendations(self, limit: int = 10) -> List[Video]:
        """
        Main recommendation pipeline
        
        Steps:
        1. Run 4 parallel recommendation strategies
        2. Score candidates from each strategy
        3. Deduplicate recommendations
        4. Apply diversity filter (avoid same channel clustering)
        5. Return top K sorted by score
        
        Args:
            limit: Number of recommendations to return
        
        Returns:
            List of Video objects
        """
        
        recommendations = []
        
        # Strategy 1: Content-Based (40%)
        self.logger.info(f"Generating content-based recommendations for user {self.user.id}")
        content_recs = self._content_based_recommendations(limit // 2)
        for video, reason in content_recs:
            recommendations.append({
                'video': video,
                'score': self.STRATEGY_WEIGHTS['CONTENT'] * 100,
                'type': 'CONTENT',
                'reason': reason
            })
        
        # Strategy 2: Collaborative (30%)
        self.logger.info(f"Generating collaborative recommendations for user {self.user.id}")
        collab_recs = self._collaborative_recommendations(limit // 3)
        for video, reason in collab_recs:
            recommendations.append({
                'video': video,
                'score': self.STRATEGY_WEIGHTS['COLLABORATIVE'] * 100,
                'type': 'COLLABORATIVE',
                'reason': reason
            })
        
        # Strategy 3: Behavior-Based (20%)
        self.logger.info(f"Generating behavior-based recommendations for user {self.user.id}")
        behavior_recs = self._behavior_based_recommendations(limit // 3)
        for video, reason in behavior_recs:
            recommendations.append({
                'video': video,
                'score': self.STRATEGY_WEIGHTS['BEHAVIOR'] * 100,
                'type': 'BEHAVIOR',
                'reason': reason
            })
        
        # Strategy 4: Trending (10%)
        self.logger.info(f"Generating trending recommendations for user {self.user.id}")
        trending_recs = self._trending_recommendations(limit // 5)
        for video, reason in trending_recs:
            recommendations.append({
                'video': video,
                'score': self.STRATEGY_WEIGHTS['TRENDING'] * 100,
                'type': 'TRENDING',
                'reason': reason
            })
        
        # Deduplicate by video_id
        seen_videos = set()
        unique_recs = []
        
        for rec in recommendations:
            if rec['video'].id not in seen_videos:
                seen_videos.add(rec['video'].id)
                unique_recs.append(rec)
        
        # Apply diversity filter (don't cluster on same channel)
        diverse_recs = self._apply_diversity_filter(unique_recs, limit)
        
        # Sort by score descending
        final_recs = sorted(
            diverse_recs,
            key=lambda x: x['score'],
            reverse=True
        )[:limit]
        
        # Save to database
        self._save_recommendations(final_recs)
        
        result_videos = [rec['video'] for rec in final_recs]
        self.logger.info(
            f"Generated {len(result_videos)} recommendations for user {self.user.id}"
        )
        
        return result_videos
    
    def _content_based_recommendations(self, limit: int) -> List[Tuple[Video, str]]:
        """
        Strategy 1: Video Similarity
        
        "If you liked Video A, you might like Video B"
        
        Algorithm:
        1. Find videos user completed with >80% watch time
        2. Extract their topics
        3. Find other videos in same topics
        4. Exclude already watched
        5. Sort by AI score and return top N
        """
        
        # Find recently completed videos
        completed_watches = WatchHistory.objects.filter(
            user=self.user,
            completion_rate__gt=80
        ).select_related('video', 'video__topic').order_by('-ended_at')[:5]
        
        if not completed_watches.exists():
            self.logger.debug(f"User {self.user.id} has no completed videos")
            return []
        
        # Extract topics from completed videos
        topics = set(w.video.topic_id for w in completed_watches)
        
        # Find related videos user hasn't watched
        watched_video_ids = WatchHistory.objects.filter(
            user=self.user
        ).values_list('video_id', flat=True)
        
        related_videos = Video.objects.filter(
            topic_id__in=topics,
            is_active=True,
            ai_score__gte=50
        ).exclude(
            id__in=watched_video_ids
        ).order_by('-ai_score')[:limit]
        
        return [
            (video, f"Similar to videos you completed in {video.topic.name}")
            for video in related_videos
        ]
    
    def _collaborative_recommendations(self, limit: int) -> List[Tuple[Video, str]]:
        """
        Strategy 2: Collaborative Filtering
        
        "Students like you found these videos helpful"
        
        Algorithm:
        1. Find similar users (same difficulty level, session duration)
        2. Find videos they completed successfully (>80% watch)
        3. Exclude videos current user has watched
        4. Rank by popularity among similar users
        5. Return top N
        """
        
        from django.contrib.auth.models import User
        
        # Find similar users (same profile characteristics)
        similar_users = User.objects.filter(
            focus_profile__difficulty_level=self.profile.difficulty_level,
            focus_profile__avg_video_length_preference__range=[
                self.profile.avg_video_length_preference - 5,
                self.profile.avg_video_length_preference + 5
            ]
        ).exclude(
            id=self.user.id
        ).values_list('id', flat=True)[:100]
        
        if not similar_users:
            self.logger.debug(f"No similar users found for user {self.user.id}")
            return []
        
        # Find videos they completed
        user_watched_ids = set(
            WatchHistory.objects.filter(
                user=self.user
            ).values_list('video_id', flat=True)
        )
        
        collaborative_videos = Video.objects.filter(
            watch_records__user_id__in=similar_users,
            watch_records__completion_rate__gt=80,
            is_active=True,
            ai_score__gte=50
        ).exclude(
            id__in=user_watched_ids
        ).annotate(
            completion_count=Count('watch_records', 
                filter=Q(watch_records__completion_rate__gt=80)),
            avg_completion=Avg('watch_records__completion_rate')
        ).order_by('-completion_count', '-avg_completion')[:limit]
        
        return [
            (video, f"Popular among students with your learning pace")
            for video in collaborative_videos
        ]
    
    def _behavior_based_recommendations(self, limit: int) -> List[Tuple[Video, str]]:
        """
        Strategy 3: Behavior Analysis
        
        "Based on your learning patterns, you'd benefit from..."
        
        Factors:
        - Preferred video duration
        - Preferred difficulty level
        - Topic enrollment
        - Consistency score alignment
        """
        
        # Get user's enrolled topics from watch history
        user_topics = set(
            WatchHistory.objects.filter(
                user=self.user
            ).values_list('video__topic_id', flat=True).distinct()
        )
        
        if not user_topics:
            self.logger.debug(f"User {self.user.id} has not watched any videos")
            return []
        
        # Calculate user's average completion rate
        user_avg_completion = WatchHistory.objects.filter(
            user=self.user
        ).aggregate(
            avg=Avg('completion_rate')
        )['avg'] or 0
        
        # Find videos matching user's characteristics
        quality_threshold = max(50, user_avg_completion * 0.8)  # Slightly below user's level
        duration_preference = self.profile.avg_video_length_preference * 60
        
        behavior_videos = Video.objects.filter(
            topic_id__in=user_topics,
            teaching_quality_score__gte=quality_threshold,
            duration_seconds__lte=duration_preference + 900,  # Within 15 min
            duration_seconds__gte=duration_preference - 600,  # Within 10 min
            is_active=True,
            ai_score__gte=50
        ).exclude(
            watch_records__user=self.user
        ).order_by('-ai_score')[:limit]
        
        return [
            (video, f"Matches your learning pace and preferences")
            for video in behavior_videos
        ]
    
    def _trending_recommendations(self, limit: int) -> List[Tuple[Video, str]]:
        """
        Strategy 4: Trending Content
        
        "Trending in your topics this week"
        
        Algorithm:
        1. Get user's topics
        2. Find videos added in last 7 days
        3. Rank by watch count in that period
        4. Exclude already watched
        5. Return top N
        """
        
        one_week_ago = timezone.now() - timedelta(days=7)
        
        # User's enrolled topics
        watched_topics = set(
            WatchHistory.objects.filter(
                user=self.user
            ).values_list('video__topic_id', flat=True).distinct()
        )
        
        if not watched_topics:
            # If no watch history, use all available topics
            watched_topics = None
        
        # Build query
        query = Video.objects.filter(
            added_at__gte=one_week_ago,
            is_active=True,
            ai_score__gte=60  # Only good quality trending content
        ).exclude(
            watch_records__user=self.user
        ).annotate(
            week_watch_count=Count('watch_records')
        ).order_by('-week_watch_count')
        
        if watched_topics:
            query = query.filter(topic_id__in=watched_topics)
        
        trending_videos = query[:limit]
        
        return [
            (video, f"New and popular in {video.topic.name} this week")
            for video in trending_videos
        ]
    
    def _apply_diversity_filter(
        self,
        recommendations: List[Dict],
        limit: int
    ) -> List[Dict]:
        """
        Ensure diversity in recommendations
        
        Prevents clustering of videos from same channel
        Returns maximum 3 videos from same channel in result
        """
        
        channel_count = {}
        filtered = []
        max_per_channel = 3
        
        for rec in recommendations:
            channel_id = rec['video'].channel_id
            
            if channel_id not in channel_count:
                channel_count[channel_id] = 0
            
            if channel_count[channel_id] < max_per_channel:
                filtered.append(rec)
                channel_count[channel_id] += 1
            
            if len(filtered) >= limit:
                break
        
        return filtered
    
    def _save_recommendations(self, recommendations: List[Dict]) -> None:
        """
        Persist recommendations to database for tracking
        
        Allows us to:
        - Track click-through rates
        - Measure recommendation effectiveness
        - A/B test strategies
        """
        
        for rec in recommendations:
            AIRecommendation.objects.update_or_create(
                user=self.user,
                video=rec['video'],
                defaults={
                    'recommendation_score': rec['score'],
                    'recommendation_type': rec['type'],
                    'reason': rec['reason'][:500]  # Truncate long reasons
                }
            )
    
    def get_next_recommended_videos(self, limit: int = 3) -> List[Video]:
        """
        Get user's next recommended videos (used in dashboard/feed)
        
        Queries recent recommendations, excludes watched videos
        """
        
        recent_recs = AIRecommendation.objects.filter(
            user=self.user,
            was_clicked=False
        ).select_related('video').order_by('-recommendation_score')[:limit]
        
        return [rec.video for rec in recent_recs]
    
    def get_recommendation_stats(self) -> Dict[str, any]:
        """
        Get stats on recommendation performance for this user
        """
        
        all_recs = AIRecommendation.objects.filter(user=self.user)
        clicked = all_recs.filter(was_clicked=True).count()
        completed = all_recs.filter(was_completed=True).count()
        total = all_recs.count()
        
        return {
            'total_recommendations': total,
            'clicked_count': clicked,
            'completed_count': completed,
            'click_through_rate': (clicked / total * 100) if total > 0 else 0,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
        }
