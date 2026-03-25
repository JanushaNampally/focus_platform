"""
Advanced Video Ranking Engine

Multi-factor ranking algorithm for personalized video recommendations.

Algorithm:
1. Fetch candidate videos for topic
2. Normalize all scoring dimensions (0-100 scale)
3. Apply weighted combination with configurable weights
4. Optional personalization adjustments per user
5. Return sorted top-N videos

Factors (8 dimensions):
- Relevance (25%): Keyword match with topic
- Quality (20%): Metadata completeness & recency
- Engagement (15%): Community reactions (likes/comments ratio)
- Sentiment (20%): NLP comment sentiment analysis
- Teaching (15%): Predicted teaching effectiveness
- Authority (5%): Channel credibility
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from django.db.models import F
from videos.models import Video
from tracking.models import WatchHistory

logger = logging.getLogger('ai_engine')


class VideoRankingEngine:
    """
    Multi-factor video ranking for distraction-free content selection
    
    Uses weighted combination of 8 scoring dimensions to rank videos.
    Optionally personalizes for individual user preferences.
    """
    
    # Default weights (tuned for broad population)
    DEFAULT_WEIGHTS = {
        'relevance': 0.25,      # Content matches topic keywords
        'quality': 0.20,         # Metadata completeness, recent upload
        'engagement': 0.15,      # Community feedback (likes/comments)
        'sentiment': 0.20,       # Comment sentiment analysis (NLP)
        'teaching': 0.15,        # Teaching effectiveness prediction
        'authority': 0.05        # Channel brand & credibility
    }
    
    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """
        Initialize ranking engine with optional custom weights
        
        Args:
            custom_weights: Override DEFAULT_WEIGHTS with custom values
                          Must sum to approximately 1.0
        """
        self.weights = custom_weights if custom_weights else self.DEFAULT_WEIGHTS.copy()
        
        # Validate weights sum to ~1.0
        weight_sum = sum(self.weights.values())
        if not (0.95 <= weight_sum <= 1.05):
            logger.warning(
                f"Weights sum to {weight_sum:.2f}, should be ~1.0. "
                f"Normalizing..."
            )
            for key in self.weights:
                self.weights[key] /= weight_sum
    
    def rank_videos(
        self,
        topic,
        user=None,
        limit: int = 10,
        min_ai_score: float = 0.0
    ) -> List[Video]:
        """
        Main ranking function: get top-N videos for a topic
        
        Args:
            topic: Course Topic object to rank videos for
            user: Optional User object for personalization
            limit: Return top N videos (default 10)
            min_ai_score: Filter out videos below this threshold (0-100)
        
        Returns:
            List of Video objects ranked by composite score
        """
        
        # Step 1: Get candidate videos
        videos = Video.objects.filter(
            topic=topic,
            is_active=True,
            ai_score__gte=min_ai_score
        ).order_by('-ai_score')[:100]  # Start with top 100
        
        if not videos.exists():
            logger.warning(f"No ranked videos found for topic {topic.id}")
            return []
        
        # Step 2: Calculate scores
        scored_videos = []
        
        for video in videos:
            # Base composite score (algorithm)
            base_score = self._calculate_composite_score(video)
            
            # Optional personalization for user
            final_score = base_score
            if user:
                personalization_bonus = self._personalize_score(video, user)
                final_score = base_score + personalization_bonus
            
            scored_videos.append((video, final_score))
        
        # Step 3: Sort by score descending and return top N
        ranked = sorted(
            scored_videos,
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        result_videos = [v[0] for v in ranked]
        
        logger.info(
            f"Ranked {len(result_videos)} videos for topic {topic.id} "
            f"(evaluated {len(videos)} candidates)"
        )
        
        return result_videos
    
    def _calculate_composite_score(self, video: Video) -> float:
        """
        Calculate weighted composite score from 8 dimensions
        
        Returns score in range 0-100
        """
        
        # Normalize scores to 0-100 range (some stored as 0-1)
        normalized_scores = {
            'relevance': self._normalize(video.relevance_score, 0, 100),
            'quality': self._normalize(video.quality_score, 0, 100),
            'engagement': self._normalize(video.engagement_score, 0, 100),
            'sentiment': self._normalize(video.sentiment_score * 100, 0, 100),
            'teaching': self._normalize(video.teaching_quality_score, 0, 100),
            'authority': self._normalize(video.channel_authority, 0, 100),
        }
        
        # Apply weights
        composite_score = sum(
            normalized_scores[key] * self.weights[key]
            for key in self.weights.keys()
        )
        
        # Clamp to valid range
        return min(100, max(0, composite_score))
    
    def _personalize_score(self, video: Video, user) -> float:
        """
        Calculate personalization bonus/penalty for user
        
        Adjusts base score based on:
        - User's preferred video length
        - Difficulty level match
        - Channel familiarity
        - Learning pace alignment
        
        Returns: -20 to +20 (added to base score)
        """
        
        adjustment = 0
        profile = user.focus_profile
        
        # 1. Length preference match (±8 points)
        preferred_duration = profile.avg_video_length_preference * 60  # Convert to seconds
        actual_duration = video.duration_seconds
        duration_diff = abs(actual_duration - preferred_duration)
        
        if duration_diff < 300:  # Within 5 minutes
            adjustment += 8
        elif duration_diff < 600:  # Within 10 minutes
            adjustment += 4
        elif duration_diff > 900:  # 15+ minutes away
            adjustment -= 8
        
        # 2. Difficulty level match (±10 points)
        if profile.difficulty_level == 'ADVANCED' and \
           video.teaching_quality_score > 80:
            adjustment += 10
        elif profile.difficulty_level == 'BEGINNER' and \
             video.teaching_quality_score < 50:
            adjustment -= 5  # Too advanced
        elif profile.difficulty_level == 'INTERMEDIATE' and \
             65 <= video.teaching_quality_score <= 85:
            adjustment += 5  # Good match
        
        # 3. Channel familiarity bonus (±6 points)
        familiar_watches = WatchHistory.objects.filter(
            user=user,
            video__channel_id=video.channel_id
        ).count()
        
        if familiar_watches >= 5:  # User knows this channel well
            adjustment += 6
        elif familiar_watches >= 2:
            adjustment += 3
        
        # 4. Learning pace alignment (±6 points)
        user_avg_completion = WatchHistory.objects.filter(
            user=user
        ).aggregate(
            avg=models.Avg('completion_rate')
        )['avg'] or 0
        
        if user_avg_completion > 80 and video.avg_completion_rate > 80:
            adjustment += 6  # Both user and video are high-quality matches
        elif user_avg_completion < 50 and video.avg_completion_rate < 60:
            adjustment -= 5  # Content mismatch
        
        return adjustment
    
    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-100 range"""
        if max_val == min_val:
            return 50  # Return middle value if min==max
        normalized = ((value - min_val) / (max_val - min_val)) * 100
        return min(100, max(0, normalized))
    
    def update_video_ranking(self, video: Video) -> None:
        """
        Trigger recalculation of AI score for a single video
        
        Called when video metadata is updated from YouTube API
        """
        
        # Recalculate composite AI score
        video.update_ai_score()
        
        logger.info(
            f"Updated ranking for video {video.id} '{video.title}': "
            f"AI score = {video.ai_score:.1f}, "
            f"Engagement = {video.engagement_score:.1f}"
        )
    
    def batch_update_rankings(self, videos: List[Video]) -> None:
        """
        Efficiently update rankings for multiple videos
        
        Use when batch updating metadata from YouTube API
        """
        
        for video in videos:
            self.update_video_ranking(video)
        
        logger.info(f"Batch updated rankings for {len(videos)} videos")
    
    def calculate_engagement_ratio(self, video: Video) -> float:
        """
        Calculate engagement ratio: (likes + comments) / views
        
        This is used in engagement_score calculation
        """
        
        if video.view_count == 0:
            return 0
        
        engagement = (video.like_count + video.comment_count) / video.view_count
        return min(1.0, engagement)  # Cap at 1.0
    
    def estimate_teaching_quality(self, video: Video) -> float:
        """
        Estimate teaching quality score from available indicators
        
        Uses:
        - Comment sentiment (if available)
        - Completion rates from user watches (if available)
        - Video duration relative to topic (too long = confusing)
        
        Returns: 0-100 score
        """
        
        components = []
        
        # 1. Sentiment-based (40% weight)
        sentiment_score = video.sentiment_score * 100  # 0-1 → 0-100
        components.append(sentiment_score * 0.40)
        
        # 2. Completion-based (40% weight)
        avg_completion = video.avg_completion_rate
        # Completion > 70% suggests good teaching
        completion_quality = min(100, (avg_completion / 70) * 100)
        components.append(completion_quality * 0.40)
        
        # 3. Duration appropriateness (20% weight)
        # Assume optimal duration is 10-20 minutes
        optimal_min = 10 * 60
        optimal_max = 20 * 60
        duration = video.duration_seconds
        
        if optimal_min <= duration <= optimal_max:
            duration_score = 100
        elif duration < optimal_min:
            duration_score = (duration / optimal_min) * 100
        else:
            duration_score = max(30, 100 - ((duration - optimal_max) / 600))
        
        components.append(duration_score * 0.20)
        
        teaching_quality = sum(components)
        return min(100, max(0, teaching_quality))
    
    @staticmethod
    def get_top_videos_for_user(user, limit: int = 5) -> List[Video]:
        """
        Get personalized top videos across all user's enrolled topics
        
        Convenience method combining ranking + personalization
        """
        
        from courses.models import Topic
        
        # Get user's enrolled topics
        user_topics = Topic.objects.filter(
            subject__course__in=user.focus_profile.enrolled_courses.all()
        ).distinct()
        
        if not user_topics.exists():
            return []
        
        engine = VideoRankingEngine()
        all_videos = Video.objects.filter(
            topic__in=user_topics,
            is_active=True,
            ai_score__gte=50
        ).order_by('-ai_score')[:50]
        
        # Collect and personalize
        scored = []
        for video in all_videos:
            base = engine._calculate_composite_score(video)
            personalization = engine._personalize_score(video, user)
            final = base + personalization
            scored.append((video, final))
        
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)
        return [v[0] for v in ranked[:limit]]
