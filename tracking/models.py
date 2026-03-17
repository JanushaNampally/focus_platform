from django.db import models

from django.db import models
from django.contrib.auth.models import User
from videos.models import Video
from django.utils import timezone


class WatchHistory(models.Model):
    """Tracks every video watch with detailed behavioral metrics"""
    
    COMPLETION_STATUS = [
        ('STARTED', 'Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ABANDONED', 'Abandoned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_history')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='watch_records')
    
    # Watch metrics
    watch_time = models.IntegerField(help_text="Actual watch time in seconds")
    video_duration = models.IntegerField(help_text="Total video duration in seconds")
    completion_rate = models.FloatField(default=0.0, help_text="% of video watched")
    
    # Behavioral signals
    skip_count = models.IntegerField(default=0, help_text="Number of times skipped")
    rewind_count = models.IntegerField(default=0, help_text="Number of times rewound")
    playback_speed = models.FloatField(default=1.0, help_text="Average playback speed")
    pauses = models.IntegerField(default=0, help_text="Number of pauses")
    
    # Status
    status = models.CharField(max_length=20, choices=COMPLETION_STATUS, default='STARTED')
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = "Watch History"
        verbose_name_plural = "Watch Histories"
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['video', 'user']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.video.title} ({self.completion_rate}%)"
    
    def save(self, *args, **kwargs):
        """Auto-calculate completion rate on save"""
        if self.video_duration > 0:
            self.completion_rate = min(100, (self.watch_time / self.video_duration) * 100)
        super().save(*args, **kwargs)


class UserBehaviorMetrics(models.Model):
    """Daily behavioral analytics for predicting focus patterns"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='behavior_metrics')
    date = models.DateField(auto_now_add=True, db_index=True)
    
    # Daily metrics
    total_watch_time = models.IntegerField(default=0, help_text="Total watch time in seconds")
    videos_watched = models.IntegerField(default=0)
    videos_completed = models.IntegerField(default=0)
    avg_completion_rate = models.FloatField(default=0.0)
    
    # Focus patterns
    session_count = models.IntegerField(default=0)
    avg_session_duration = models.IntegerField(default=0, help_text="Average session length in seconds")
    max_session_duration = models.IntegerField(default=0)
    
    # Engagement quality
    skip_ratio = models.FloatField(default=0.0, help_text="0-1 skip behavior")
    pause_ratio = models.FloatField(default=0.0, help_text="0-1 pause frequency")
    completion_quality = models.FloatField(default=0.0, help_text="0-1 completion quality score")
    
    # Streak maintenance
    streak_maintained = models.BooleanField(default=False)
    streak_points = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']
        verbose_name = "User Behavior Metrics"
        indexes = [
            models.Index(fields=['user', '-date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"


class StreakTracking(models.Model):
    """Gamification: Daily streak tracking for motivation"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='streaks')
    
    # Current streak
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    
    # Streak history
    total_days_active = models.IntegerField(default=0)
    streak_started_at = models.DateField(null=True, blank=True)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # Rewards
    total_points = models.IntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Streak Tracking"
        verbose_name_plural = "Streak Trackings"
    
    def __str__(self):
        return f"{self.user.username} - Streak: {self.current_streak}"
    
    def update_streak(self, date=None):
        """Update streak based on activity"""
        if date is None:
            date = timezone.now().date()
        
        # Reset streak if more than 1 day has passed
        if self.last_activity_date and (date - self.last_activity_date).days > 1:
            self.current_streak = 0
        
        # Increment streak if active today
        if self.last_activity_date != date:
            self.current_streak += 1
            self.total_days_active += 1
            self.total_points += 10 + (self.current_streak * 5)  # Bonus for streaks
        
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        
        self.last_activity_date = date
        self.save()


class AIRecommendation(models.Model):
    """ML-generated personalized video recommendations"""
    
    RECOMMENDATION_TYPE = [
        ('CONTENT', 'Content Match'),
        ('BEHAVIOR', 'Behavior-based'),
        ('COLLABORATIVE', 'Collaborative Filtering'),
        ('TRENDING', 'Trending in Topic'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_recommendations')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='recommendations')
    
    # Recommendation scoring
    recommendation_score = models.FloatField(help_text="0-100 recommendation score")
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPE)
    
    # Reasoning (for explainability)
    reason = models.TextField(blank=True, help_text="Why was this recommended?")
    
    # Tracking
    was_clicked = models.BooleanField(default=False)
    was_completed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    interacted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-recommendation_score']
        unique_together = ['user', 'video']
        verbose_name = "AI Recommendation"
        verbose_name_plural = "AI Recommendations"
        indexes = [
            models.Index(fields=['user', '-recommendation_score']),
            models.Index(fields=['was_clicked']),
        ]
    
    def __str__(self):
        return f"{self.user.username} → {self.video.title} ({self.recommendation_score:.1f})"


class CommentSentiment(models.Model):
    """NLP-analyzed YouTube comments for quality assessment"""
    
    SENTIMENT_CHOICE = [
        ('POSITIVE', 'Positive'),
        ('NEUTRAL', 'Neutral'),
        ('NEGATIVE', 'Negative'),
    ]
    
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comment_sentiments')
    
    comment_text = models.TextField()
    author = models.CharField(max_length=200, blank=True)
    
    # NLP sentiment analysis
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICE)
    sentiment_score = models.FloatField(help_text="0-1 positive score from NLP")
    
    # Quality indicators
    teaching_quality = models.BooleanField(default=False, help_text="Indicates teaching quality")
    clarity_feedback = models.BooleanField(default=False, help_text="Mentions clarity/understanding")
    criticism = models.BooleanField(default=False, help_text="Constructive criticism")
    
    analyzed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Comment Sentiment"
        verbose_name_plural = "Comment Sentiments"
        indexes = [
            models.Index(fields=['video', 'sentiment']),
        ]
    
    def __str__(self):
        return f"{self.video.title} - {self.sentiment}"