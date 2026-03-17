import requests

API_KEY = "YOUR_API_KEY"

def search_videos(query):
    url = f"https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": query,
        "key": API_KEY,
        "maxResults": 10,
        "type": "video"
    }

    response = requests.get(url, params=params)
    return response.json()