from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    # Core profile fields
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='focus_profile')
    goal_reason = models.TextField(blank=True, help_text="User's personal learning goal")
    
    # AI/ML fields
    consistency_score = models.FloatField(default=0.0, help_text="0-100 user consistency index")
    risk_level = models.CharField(max_length=20, default="LOW", choices=[
        ('LOW', 'Low Risk - Consistent'),
        ('MEDIUM', 'Medium Risk - Declining'),
        ('HIGH', 'High Risk - Needs Intervention')
    ])
    
    # Behavioral analytics
    total_watch_time = models.IntegerField(default=0, help_text="Total watch time in seconds")
    avg_session_duration = models.IntegerField(default=0, help_text="Average session duration in seconds")
    
    # Streak tracking
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # Preferences
    avg_video_length_preference = models.IntegerField(default=15, help_text="Preferred video length in minutes")
    difficulty_level = models.CharField(max_length=20, default='BEGINNER', choices=[
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced')
    ])
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Streak: {self.current_streak}"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        indexes = [
            models.Index(fields=['consistency_score']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['current_streak']),
        ]