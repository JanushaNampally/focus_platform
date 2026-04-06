def calculate_video_score(video):
    like_ratio = video.likes / max(video.views, 1)

    score = (
        (video.views * 0.3) +
        (video.likes * 0.5) +
        (like_ratio * 1000 * 0.2)
    )

    return round(score, 2)