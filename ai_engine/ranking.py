def calculate_score(video):
    like_ratio = video.likes / video.views if video.views else 0
    engagement = (video.likes) / video.views if video.views else 0

    score = (
        0.4 * like_ratio +
        0.3 * engagement +
        0.3 * video.ai_score
    )

    return score