from django.db import models
from django.db.models import Q
from django.utils import timezone


class Video(models.Model):
    """Stores YouTube videos with AI-scored metadata and engagement metrics"""
    
    # Core fields
    topic = models.ForeignKey(
        'courses.Topic',
        on_delete=models.CASCADE,
        related_name="videos"
    )
    title = models.CharField(max_length=200)
    youtube_id = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    duration_seconds = models.IntegerField(default=0)
    
    # YouTube Metadata (fetched via API)
    channel_name = models.CharField(max_length=200, blank=True)
    channel_id = models.CharField(max_length=100, blank=True, db_index=True)
    view_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    thumbnail_url = models.URLField(blank=True)
    
    # AI/ML Scores
    relevance_score = models.FloatField(default=0.0, help_text="0-100 keyword relevance")
    quality_score = models.FloatField(default=0.0, help_text="0-100 based on metadata")
    engagement_score = models.FloatField(default=0.0, help_text="0-100 likes/views ratio")
    sentiment_score = models.FloatField(default=0.5, help_text="0-1 comment sentiment (NLP)")
    teaching_quality_score = models.FloatField(default=0.0, help_text="0-100 teaching effectiveness")
    
    # Composite ranking
    ai_score = models.FloatField(default=0.0, help_text="Final AI ranking 0-100", db_index=True)
    rank_position = models.IntegerField(null=True, blank=True, help_text="Topic-specific ranking")
    
    # Channel authority
    channel_authority = models.FloatField(default=0.0, help_text="0-100 channel credibility score")
    is_verified_channel = models.BooleanField(default=False)
    
    # Watch metrics (aggregate)
    total_watch_count = models.IntegerField(default=0)
    avg_completion_rate = models.FloatField(default=0.0, help_text="Average % watched (0-100)")
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    last_metadata_update = models.DateTimeField(null=True, blank=True)
    times_recommended = models.IntegerField(default=0)
    times_watched = models.IntegerField(default=0, db_index=True)
    
    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} (Score: {self.ai_score:.1f})"
    
    def get_engagement_ratio(self):
        """Calculate engagement ratio for ranking"""
        if self.view_count == 0:
            return 0
        return (self.like_count + self.comment_count) / self.view_count
    
    def update_ai_score(self):
        """Recalculate composite AI score based on all metrics"""
        weights = {
            'relevance': 0.25,
            'quality': 0.20,
            'engagement': 0.15,
            'sentiment': 0.20,
            'teaching': 0.15,
            'authority': 0.05
        }
        
        self.ai_score = (
            weights['relevance'] * self.relevance_score +
            weights['quality'] * self.quality_score +
            weights['engagement'] * self.engagement_score +
            weights['sentiment'] * (self.sentiment_score * 100) +
            weights['teaching'] * self.teaching_quality_score +
            weights['authority'] * self.channel_authority
        )
        self.last_metadata_update = timezone.now()
        self.save(update_fields=['ai_score', 'last_metadata_update'])
    
    @staticmethod
    def get_ranked_videos(topic, limit=10, user=None):
        """Get top-ranked videos for a topic, optionally personalized"""
        videos = Video.objects.filter(
            topic=topic,
            is_active=True,
            ai_score__gt=0
        ).order_by('-ai_score')[:limit]
        
        return videos
    
    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videos"
        ordering = ['-ai_score', '-published_at']
        indexes = [
            models.Index(fields=['topic', '-ai_score']),
            models.Index(fields=['is_active', '-ai_score']),
            models.Index(fields=['channel_id']),
            models.Index(fields=['times_watched']),
        ]