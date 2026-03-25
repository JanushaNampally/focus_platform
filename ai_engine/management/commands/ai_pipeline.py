"""
Management command to orchestrate AI/ML pipeline
python manage.py ai_pipeline --analyze-videos --fetch-comments --update-rankings
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
import logging

from videos.models import Video
from videos.services.youtube_service import YouTubeDataService
from ai_engine.nlp import get_sentiment_analyzer, CommentSentimentAnalyzer
from ai_engine.ranking import VideoRankingEngine
from ai_engine.recommendations import RecommendationEngine
from tracking.models import CommentSentiment
from courses.models import Topic

logger = logging.getLogger('ai_engine')


class Command(BaseCommand):
    help = 'Run AI/ML pipeline: fetch videos, analyze comments, update rankings'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fetch-videos',
            action='store_true',
            help='Fetch new videos from YouTube'
        )
        parser.add_argument(
            '--fetch-comments',
            action='store_true',
            help='Fetch YouTube comments and run sentiment analysis'
        )
        parser.add_argument(
            '--update-rankings',
            action='store_true',
            help='Recalculate video AI scores'
        )
        parser.add_argument(
            '--generate-recommendations',
            action='store_true',
            help='Generate personalized recommendations for active users'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all pipeline steps'
        )
        parser.add_argument(
            '--topic-id',
            type=int,
            help='Limit operations to specific topic (optional)'
        )
        parser.add_argument(
            '--video-limit',
            type=int,
            default=50,
            help='Max videos to process per topic (default 50)'
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        self.stdout.write(self.style.SUCCESS('🚀 Starting FocusTube AI Pipeline...'))
        
        # Get API key
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
        if not api_key:
            raise CommandError(
                '❌ YOUTUBE_API_KEY not set in settings.py\n'
                'Add: YOUTUBE_API_KEY = "your-api-key"'
            )
        
        youtube_service = YouTubeDataService(api_key)
        topic_id = options.get('topic_id')
        video_limit = options.get('video_limit')
        
        # Determine which steps to run
        fetch_videos = options['fetch_videos'] or options['all']
        fetch_comments = options['fetch_comments'] or options['all']
        update_rankings = options['update_rankings'] or options['all']
        gen_recommendations = options['generate_recommendations'] or options['all']
        
        try:
            if fetch_videos:
                self.stdout.write(self.style.HTTP_INFO('📺 Fetching videos from YouTube...'))
                self._fetch_videos(youtube_service, topic_id, video_limit)
            
            if fetch_comments:
                self.stdout.write(self.style.HTTP_INFO('💬 Fetching and analyzing comments...'))
                self._analyze_comments(youtube_service, topic_id)
            
            if update_rankings:
                self.stdout.write(self.style.HTTP_INFO('⭐ Updating video rankings...'))
                self._update_rankings(topic_id)
            
            if gen_recommendations:
                self.stdout.write(self.style.HTTP_INFO('🎬 Generating recommendations...'))
                self._generate_recommendations()
            
            self.stdout.write(
                self.style.SUCCESS('\n✅ AI Pipeline completed successfully!\n')
            )
        
        except Exception as e:
            raise CommandError(f'Pipeline error: {str(e)}')
    
    def _fetch_videos(self, youtube_service, topic_id=None, limit=50):
        """Fetch videos from YouTube for all/specific topics"""
        
        # Get topics to process
        topics = Topic.objects.all()
        if topic_id:
            topics = topics.filter(id=topic_id)
        
        if not topics.exists():
            self.stdout.write(self.style.WARNING('⚠️  No topics found'))
            return
        
        total_videos = 0
        
        for topic in topics:
            self.stdout.write(f'\n  📍 Topic: {topic.name}')
            
            # Search YouTube
            videos_data = youtube_service.search_videos_for_topic(
                topic_name=topic.name,
                course_name=topic.subject.course.name if topic.subject else "",
                max_results=limit
            )
            
            if not videos_data:
                self.stdout.write(
                    self.style.WARNING(f'    ⚠️  No videos found for {topic.name}')
                )
                continue
            
            # Store in database
            created_count = 0
            for video_data in videos_data:
                video, created = Video.objects.update_or_create(
                    youtube_id=video_data['youtube_id'],
                    topic=topic,
                    defaults={
                        'title': video_data['title'],
                        'description': video_data['description'],
                        'channel_name': video_data['channel_name'],
                        'channel_id': video_data['channel_id'],
                        'view_count': video_data['view_count'],
                        'like_count': video_data['like_count'],
                        'comment_count': video_data['comment_count'],
                        'published_at': video_data['published_at'],
                        'thumbnail_url': video_data['thumbnail_url'],
                        'duration_seconds': video_data['duration_seconds'],
                        'channel_authority': video_data['channel_authority'],
                        'is_active': True,
                        'last_metadata_update': timezone.now()
                    }
                )
                if created:
                    created_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'    ✅ Added {created_count} videos, '
                    f'Updated {len(videos_data) - created_count}'
                )
            )
            total_videos += len(videos_data)
        
        self.stdout.write(
            self.style.SUCCESS(f'\n📊 Total videos processed: {total_videos}')
        )
    
    def _analyze_comments(self, youtube_service, topic_id=None):
        """Fetch comments and run NLP sentiment analysis"""
        
        # Get videos to analyze
        videos = Video.objects.filter(is_active=True, comment_count__gt=0)
        if topic_id:
            videos = videos.filter(topic_id=topic_id)
        
        videos = videos.order_by('-ai_score')[:100]  # Top 100 by AI score
        
        if not videos.exists():
            self.stdout.write(self.style.WARNING('⚠️  No videos to analyze'))
            return
        
        sentiment_analyzer = get_sentiment_analyzer()
        total_comments = 0
        
        for video in videos:
            self.stdout.write(f'\n  📺 {video.title[:50]}...')
            
            # Fetch comments
            comments = youtube_service.fetch_comments_for_video(
                video.youtube_id,
                max_results=100
            )
            
            if not comments:
                self.stdout.write('    ⚠️  No comments found')
                continue
            
            # Analyze sentiment
            analysis = sentiment_analyzer.batch_analyze_comments(comments)
            
            # Update video scores from analysis
            video.sentiment_score = analysis['aggregate']['avg_sentiment_score']
            video.teaching_quality_score = analysis['quality_score']
            video.last_metadata_update = timezone.now()
            video.save()
            
            # Store individual comment sentiments
            for i, comment_text in enumerate(comments[:20]):  # Store top 20
                if i < len(analysis['individual_results']):
                    result = analysis['individual_results'][i]
                    CommentSentiment.objects.update_or_create(
                        video=video,
                        comment_text=comment_text[:300],
                        defaults={
                            'sentiment': result['sentiment'],
                            'sentiment_score': result['sentiment_score'],
                            'teaching_quality': result['teaching_quality'],
                            'clarity_feedback': result['clarity_feedback'],
                            'criticism': result['criticism']
                        }
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'    ✅ Analyzed {len(comments)} comments\n'
                    f'       Sentiment: {analysis["aggregate"]["avg_sentiment_score"]:.2f}\n'
                    f'       Quality: {analysis["quality_score"]:.1f}/100'
                )
            )
            total_comments += len(comments)
        
        self.stdout.write(
            self.style.SUCCESS(f'\n📊 Total comments analyzed: {total_comments}')
        )
    
    def _update_rankings(self, topic_id=None):
        """Recalculate AI scores for all videos"""
        
        videos = Video.objects.filter(is_active=True)
        if topic_id:
            videos = videos.filter(topic_id=topic_id)
        
        if not videos.exists():
            self.stdout.write(self.style.WARNING('⚠️  No videos to rank'))
            return
        
        ranking_engine = VideoRankingEngine()
        
        for i, video in enumerate(videos, 1):
            # Recalculate AI score
            ranking_engine.update_video_ranking(video)
            
            if i % 10 == 0:
                self.stdout.write(f'  ✅ Processed {i}/{videos.count()} videos')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Updated rankings for {videos.count()} videos')
        )
    
    def _generate_recommendations(self):
        """Generate personalized recommendations for active users"""
        
        from django.contrib.auth.models import User
        from tracking.models import WatchHistory
        from django.db.models import Count
        
        # Get active users (watched > 3 videos)
        active_users = User.objects.annotate(
            watch_count=Count('watch_history')
        ).filter(watch_count__gte=3)
        
        if not active_users.exists():
            self.stdout.write(self.style.WARNING('⚠️  No active users found'))
            return
        
        processed = 0
        
        for user in active_users[:100]:  # Limit to 100 users per run
            try:
                engine = RecommendationEngine(user)
                recommendations = engine.generate_recommendations(limit=10)
                
                if recommendations:
                    processed += 1
                    if processed % 10 == 0:
                        self.stdout.write(f'  ✅ Generated recommendations for {processed} users')
            
            except Exception as e:
                logger.error(f'Error generating recommendations for user {user.id}: {str(e)}')
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Generated recommendations for {processed} users'
            )
        )
