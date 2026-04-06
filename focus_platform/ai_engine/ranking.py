from ai_engine.engagement_predictor import predict_engagement


def calculate_video_score(video, user_goal=None):
    like_ratio = video.likes / max(video.views, 1)

    base_score = (
        (video.views * 0.3) +
        (video.likes * 0.5) +
        (like_ratio * 1000 * 0.2)
    )

    ml_score = predict_engagement(video) * 50

    score = base_score + ml_score

    if user_goal:
        goal_text = user_goal.lower()
        topic_text = video.topic.lower()
        title_text = video.title.lower()

        if topic_text in goal_text or goal_text in title_text:
            score += 5000

    return round(score, 2)