import pandas as pd
from sklearn.linear_model import LinearRegression


def train_engagement_model():
    data = {
        "views": [1000, 2000, 3000, 5000, 7000],
        "likes": [80, 150, 240, 400, 600],
        "duration": [10, 12, 15, 20, 25],
        "engagement_score": [60, 70, 78, 88, 95]
    }

    df = pd.DataFrame(data)

    X = df[["views", "likes", "duration"]]
    y = df["engagement_score"]

    model = LinearRegression()
    model.fit(X, y)

    return model


def predict_engagement(video):
    model = train_engagement_model()

    prediction = model.predict([[
        video.views,
        video.likes,
        video.duration_minutes
    ]])

    return round(float(prediction[0]), 2)