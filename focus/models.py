from django.db import models
from django.contrib.auth.models import User
from videos.models import Video
from django.utils import timezone


class FocusSession(models.Model):
    """Deep focus study sessions with distraction tracking and gamification"""
    
    STATUS = [
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
        ('ABANDONED', 'Abandoned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='focus_sessions')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='focus_sessions')
    topic = models.ForeignKey('courses.Topic', on_delete=models.SET_NULL, null=True, related_name='focus_sessions')
    
    # Session timing
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    planned_duration = models.IntegerField(default=1800, help_text="Planned session duration in seconds")
    
    # Session metrics
    actual_duration = models.IntegerField(default=0, help_text="Actual watch time in seconds")
    duration_seconds = models.IntegerField(default=0, help_text="Deprecated: use actual_duration")
    
    # Focus quality
    distraction_count = models.IntegerField(default=0, help_text="Times user left focus mode")
    pause_count = models.IntegerField(default=0, help_text="Number of pauses")
    tab_switches = models.IntegerField(default=0, help_text="External tab switches detected")
    
    # Focus score (0-100)
    focus_score = models.FloatField(default=0.0, help_text="Quality of focus during session")
    
    # Status
    is_fullscreen = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default='ACTIVE')
    completed = models.BooleanField(default=False)
    
    # Rewards
    points_earned = models.IntegerField(default=0)
    streak_maintained = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Focus Session"
        verbose_name_plural = "Focus Sessions"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', '-start_time']),
            models.Index(fields=['status']),
            models.Index(fields=['completed']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.video.title} ({self.actual_duration}s)"
    
    def calculate_focus_score(self):
        """Calculate focus quality score (0-100)"""
        max_distractions = 5
        max_pauses = 10
        
        distraction_penalty = min(100, (self.distraction_count / max_distractions) * 50)
        pause_penalty = min(50, (self.pause_count / max_pauses) * 30)
        
        self.focus_score = max(0, 100 - distraction_penalty - pause_penalty)
    
    def record_distraction(self):
        """Track distraction event"""
        self.distraction_count += 1
        self.calculate_focus_score()
    
    def end_session(self):
        """End focus session and calculate rewards"""
        self.end_time = timezone.now()
        self.actual_duration = int((self.end_time - self.start_time).total_seconds())
        self.calculate_focus_score()
        
        # Award points
        if self.actual_duration >= self.planned_duration * 0.8:
            self.points_earned = 50 + int(self.focus_score / 2)
            self.completed = True
            self.status = 'COMPLETED'
        else:
            self.points_earned = max(10, int(self.actual_duration / 60))
            self.status = 'ABANDONED'
        
        self.save()
    
    def save(self, *args, **kwargs):
        """Ensure actual_duration mirrors duration_seconds for backward compatibility"""
        if self.actual_duration > 0:
            self.duration_seconds = self.actual_duration
        super().save(*args, **kwargs)


class StudyNote(models.Model):
    """Notes taken during video watching for learning support"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_notes')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='notes')
    session = models.ForeignKey(FocusSession, on_delete=models.CASCADE, null=True, blank=True, related_name='notes')
    
    # Note content
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Timestamp
    timestamp_in_video = models.IntegerField(default=0, help_text="Seconds into video")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tags for organization
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Study Note"
        verbose_name_plural = "Study Notes"
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['video']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"