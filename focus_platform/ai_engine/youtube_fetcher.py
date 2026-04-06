import requests
from videos.models import Video

API_KEY = "AIzaSyAy8cTJ68q8hHcnhkfe03Xmd_MS8B81Emc"


def fetch_educational_videos(query="machine learning", max_results=5):
    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    return data.get("items", [])


def save_videos_to_db_for_topics(topics=None):
    if topics is None:
        topics = [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "nlp",
            "computer vision"
        ]

    total_saved = 0

    for topic in topics:
        videos = fetch_educational_videos(topic)

        for item in videos:
            title = item["snippet"]["title"]
            youtube_id = item["id"]["videoId"]

            _, created = Video.objects.get_or_create(
                youtube_id=youtube_id,
                defaults={
                    "title": title,
                    "topic": topic,
                    "views": 1000,
                    "likes": 100,
                    "duration_minutes": 15
                }
            )

            if created:
                total_saved += 1

    return total_saved