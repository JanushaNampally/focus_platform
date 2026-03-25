"""
YouTube Data API Integration Service

Complete integration with YouTube API v3 for:
- Video search and metadata fetching
- Comment analysis for quality assessment
- Channel authority calculation
- Intelligent caching to respect rate limits

Rate Limits:
- Google Cloud Free Tier: 10,000 quota units/day
- Each search: ~100 units
- Each video.get: ~2-4 units
- Comment fetch: ~1 unit per comment

Strategy: Cache aggressively (24h TTL) and prioritize operations
"""

import requests
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger('ai_engine')


class YouTubeDataService:
    """
    Full-featured YouTube Data API v3 client
    
    Features:
    - Search for videos by topic
    - Fetch detailed metadata (views, likes, duration)
    - Retrieve comments for sentiment analysis
    - Calculate channel authority scores
    - Cache management and rate limiting
    """
    
    API_BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self, api_key: str):
        """
        Initialize YouTube service with API key
        
        Args:
            api_key: YouTube Data API v3 key from Google Cloud
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FocusTube/2.0 AI Learning Platform'
        })
    
    def search_videos_for_topic(
        self,
        topic_name: str,
        course_name: str = "",
        max_results: int = 50
    ) -> List[Dict]:
        """
        Search YouTube for videos related to a topic
        
        Args:
            topic_name: Topic name (e.g., "Quantum Mechanics")
            course_name: Course context (e.g., "IIT JEE Physics")
            max_results: Number of videos to fetch
        
        Returns:
            List of video dictionaries with metadata
        """
        
        # Check cache first (24h TTL)
        cache_key = f"yt_search_{topic_name}_{course_name}".replace(" ", "_")
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.info(f"Cache hit for topic search: {topic_name}")
            return cached_results
        
        # Build intelligent search query
        query = self._build_search_query(topic_name, course_name)
        
        search_params = {
            "part": "snippet",
            "q": query,
            "key": self.api_key,
            "maxResults": max_results,
            "type": "video",
            "order": "relevance",
            "videoDuration": "medium",  # 4-20 minutes (educational sweet spot)
            "videoCaption": "closedCaption",  # Prefer videos with captions
            "regionCode": "IN",  # India-focused (customize as needed)
            "relevanceLanguage": "en",
            "safeSearch": "moderate"
        }
        
        try:
            logger.info(f"Searching YouTube for: {query}")
            response = self.session.get(
                f"{self.API_BASE_URL}/search",
                params=search_params,
                timeout=30
            )
            response.raise_for_status()
            
            search_results = response.json()
            videos = []
            
            # Process search results
            for item in search_results.get('items', []):
                video_id = item['snippet']['videoId']
                
                # Fetch detailed metadata for each video
                video_details = self._fetch_video_details(video_id)
                
                if video_details:
                    videos.append(video_details)
            
            # Cache for 24 hours
            cache.set(cache_key, videos, 86400)
            
            logger.info(f"Fetched {len(videos)} videos for topic '{topic_name}'")
            return videos
        
        except requests.exceptions.RequestException as e:
            logger.error(f"YouTube API search error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during video search: {str(e)}")
            return []
    
    def _fetch_video_details(self, video_id: str) -> Optional[Dict]:
        """
        Fetch comprehensive metadata for a single video
        
        Includes: statistics, duration, channel info, captions
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dictionary with video metadata or None if error
        """
        
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
            "key": self.api_key
        }
        
        try:
            response = self.session.get(
                f"{self.API_BASE_URL}/videos",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            items = response.json().get('items', [])
            if not items:
                logger.warning(f"No video found for ID: {video_id}")
                return None
            
            item = items[0]
            snippet = item['snippet']
            stats = item['statistics']
            content = item['contentDetails']
            
            # Parse ISO 8601 duration (PT15M33S → 933 seconds)
            duration_seconds = self._parse_iso_duration(content['duration'])
            
            # Quality filter: only educational length content
            if duration_seconds < 120 or duration_seconds > 3600:  # 2min - 60min
                logger.debug(f"Video {video_id} filtered: duration {duration_seconds}s")
                return None
            
            # Fetch channel authority score
            channel_authority = self._fetch_channel_authority(snippet['channelId'])
            
            return {
                'youtube_id': video_id,
                'title': snippet['title'][:200],
                'description': snippet['description'][:500],
                'channel_name': snippet['channelTitle'][:100],
                'channel_id': snippet['channelId'],
                'view_count': int(stats.get('viewCount', 0)),
                'like_count': int(stats.get('likeCount', 0)),
                'comment_count': int(stats.get('commentCount', 0)),
                'published_at': self._parse_rfc3339(snippet['publishedAt']),
                'thumbnail_url': snippet['thumbnails']['high']['url'],
                'duration_seconds': duration_seconds,
                'channel_authority': channel_authority
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API error fetching video {video_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing video details {video_id}: {str(e)}")
            return None
    
    def _fetch_channel_authority(self, channel_id: str) -> float:
        """
        Calculate channel credibility/authority score
        
        Based on:
        - Subscriber count
        - Video count
        - Channel verification status
        
        Returns: Authority score 0-100
        """
        
        # Check cache first (7 day TTL)
        cache_key = f"yt_channel_{channel_id}"
        cached_authority = cache.get(cache_key)
        if cached_authority is not None:
            return cached_authority
        
        params = {
            "part": "statistics,brandingSettings",
            "id": channel_id,
            "key": self.api_key
        }
        
        try:
            response = self.session.get(
                f"{self.API_BASE_URL}/channels",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            items = response.json().get('items', [])
            if not items:
                logger.warning(f"Channel not found: {channel_id}")
                return 50  # Default neutral score
            
            item = items[0]
            stats = item['statistics']
            
            subscribers = int(stats.get('subscriberCount', 0))
            video_count = int(stats.get('videoCount', 0))
            
            # Calculate authority score (0-100)
            # Factors:
            # - Subscribers: 0-50 points (1M subs = max)
            # - Video count: 0-30 points (1000+ videos = max)
            # - Base credibility: 20 points
            
            subscriber_score = min(50, (subscribers / 1000000) * 50)
            video_score = min(30, (video_count / 1000) * 30)
            
            authority = subscriber_score + video_score + 20
            authority = min(100, max(0, authority))
            
            # Cache for 7 days
            cache.set(cache_key, authority, 604800)
            
            logger.debug(f"Channel {channel_id}: Subscribers={subscribers}, Authority={authority:.1f}")
            return authority
        
        except Exception as e:
            logger.error(f"Error fetching channel authority {channel_id}: {str(e)}")
            return 50  # Default neutral score on error
    
    def fetch_comments_for_video(
        self,
        video_id: str,
        max_results: int = 100
    ) -> List[str]:
        """
        Fetch YouTube comments for sentiment analysis
        
        Args:
            video_id: YouTube video ID
            max_results: Max comments to fetch (max 100 per API call)
        
        Returns:
            List of comment strings
        """
        
        # Check cache (24h TTL)
        cache_key = f"yt_comments_{video_id}"
        cached_comments = cache.get(cache_key)
        if cached_comments is not None:
            logger.debug(f"Cache hit for comments: {video_id}")
            return cached_comments
        
        params = {
            "part": "snippet",
            "videoId": video_id,
            "key": self.api_key,
            "maxResults": min(max_results, 100),  # API max
            "textFormat": "plainText",
            "order": "relevance"  # Most relevant comments first
        }
        
        comments = []
        
        try:
            response = self.session.get(
                f"{self.API_BASE_URL}/commentThreads",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            items = response.json().get('items', [])
            
            for item in items:
                try:
                    comment_text = item['snippet'][
                        'topLevelComment']['snippet']['textDisplay']
                    
                    # Filter out spam/promotional comments
                    if len(comment_text) > 5 and len(comment_text) < 5000:
                        comments.append(comment_text)
                
                except KeyError:
                    continue
            
            # Cache for 24 hours
            cache.set(cache_key, comments, 86400)
            
            logger.info(f"Fetched {len(comments)} comments for video {video_id}")
            return comments
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching comments for {video_id}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error processing comments: {str(e)}")
            return []
    
    def _build_search_query(self, topic_name: str, course_name: str = "") -> str:
        """
        Build intelligent search query from topic and course context
        
        Examples:
        - "Quantum Mechanics" + "JEE" → "quantum mechanics tutorial JEE"
        - "Photosynthesis" + "NEET" → "photosynthesis tutorial NEET"
        
        Args:
            topic_name: Topic name
            course_name: Course context
        
        Returns:
            Optimized search query string
        """
        
        query_parts = [topic_name]
        
        # Add tutorial keyword (increases relevance for educational content)
        query_parts.append("tutorial")
        
        # Add course context if available
        if course_name:
            query_parts.append(course_name)
        
        # Add educational context keywords
        query_parts.append("explanation")
        
        return " ".join(query_parts)
    
    def _parse_iso_duration(self, duration_str: str) -> int:
        """
        Convert ISO 8601 duration to seconds
        
        Examples:
        - "PT15M33S" → 933
        - "PT1H30M" → 5400
        - "PT45S" → 45
        
        Args:
            duration_str: ISO 8601 duration string
        
        Returns:
            Duration in seconds
        """
        
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            logger.warning(f"Could not parse duration: {duration_str}")
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
    
    def _parse_rfc3339(self, rfc3339_str: str) -> datetime:
        """
        Parse RFC 3339 timestamp from YouTube API
        
        Examples:
        - "2024-03-15T10:30:00Z" → datetime object
        - "2024-03-15T10:30:00+05:30" → datetime object
        
        Args:
            rfc3339_str: RFC 3339 formatted datetime string
        
        Returns:
            datetime object (UTC timezone-aware)
        """
        
        try:
            # Replace Z with +00:00 for Python 3.6 compatibility
            rfc3339_str = rfc3339_str.replace('Z', '+00:00')
            return datetime.fromisoformat(rfc3339_str)
        except Exception as e:
            logger.error(f"Error parsing datetime {rfc3339_str}: {str(e)}")
            return datetime.now(timezone.utc)
    
    def clear_cache(self, cache_type: str = "all") -> None:
        """
        Clear YouTube API cache for testing/debugging
        
        Args:
            cache_type: "search" | "comments" | "channels" | "all"
        """
        
        if cache_type in ["search", "all"]:
            # Clear all search caches
            for key in cache.keys("yt_search_*"):
                cache.delete(key)
            logger.info("Cleared search cache")
        
        if cache_type in ["comments", "all"]:
            # Clear comment caches
            for key in cache.keys("yt_comments_*"):
                cache.delete(key)
            logger.info("Cleared comments cache")
        
        if cache_type in ["channels", "all"]:
            # Clear channel caches
            for key in cache.keys("yt_channel_*"):
                cache.delete(key)
            logger.info("Cleared channel cache")
