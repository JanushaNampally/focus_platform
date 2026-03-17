from django.db import models
from django.contrib.auth.models import User
from videos.models import Video


class VideoRankingTraining(models.Model):
    """Training data for ML ranking model"""
    
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='ranking_data')
    
    # Features
    views = models.IntegerField()
    likes = models.IntegerField()
    comments = models.IntegerField()
    duration = models.IntegerField()
    upload_age_days = models.IntegerField()
    channel_subscribers = models.IntegerField(default=0)
    
    # Target (ground truth)
    user_rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])  # 1-5 star
    teaching_effectiveness = models.FloatField(default=0.0)  # 0-1
    
    # Metadata
    feedback_source = models.CharField(max_length=50, default='MANUAL')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Video Ranking Training"
        verbose_name_plural = "Video Ranking Training Data"
        ordering = ['-created_at']


class UserPreferenceModel(models.Model):
    """Stores personalization model data for each user"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference_model')
    
    # Video preference vectors (could store embeddings)
    preferred_video_length = models.IntegerField(default=10, help_text="Minutes")
    preferred_teaching_style = models.CharField(max_length=100, blank=True)
    preferred_channels = models.JSONField(default=list, help_text="List of trusted channel IDs")
    
    # Behavioral patterns
    optimal_session_time = models.TimeField(null=True, blank=True)
    optimal_session_duration = models.IntegerField(default=1800, help_text="Seconds")
    
    # Personalization weights
    weights_json = models.JSONField(default=dict, help_text="ML model weights for personalization")
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Preference Model"
        verbose_name_plural = "User Preference Models"
    
    def __str__(self):
        return f"{self.user.username} - Preferences"


class ModelPerformance(models.Model):
    """Track AI model performance metrics over time"""
    
    MODEL_TYPES = [
        ('RANKING', 'Video Ranking'),
        ('RECOMMENDATION', 'Recommendation Engine'),
        ('SENTIMENT', 'Sentiment Analysis'),
        ('PREDICTION', 'Focus Prediction'),
    ]
    
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES)
    version = models.CharField(max_length=20)
    
    # Performance metrics
    accuracy = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    f1_score = models.FloatField()
    
    # Training info
    training_samples = models.IntegerField()
    training_date = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['model_type', 'version']
        ordering = ['-training_date']
        verbose_name = "Model Performance"
        verbose_name_plural = "Model Performance Records"
    
    def __str__(self):
        return f"{self.model_type} v{self.version} - F1: {self.f1_score:.3f}"
