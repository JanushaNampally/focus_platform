import pandas as pd
from sklearn.linear_model import LogisticRegression


def train_churn_model():
    data = {
        "streak": [0, 1, 2, 5, 7, 10],
        "sessions": [0, 1, 2, 5, 8, 12],
        "days_inactive": [7, 5, 3, 2, 1, 0],
        "churn": [1, 1, 1, 0, 0, 0]
    }

    df = pd.DataFrame(data)

    X = df[["streak", "sessions", "days_inactive"]]
    y = df["churn"]

    model = LogisticRegression()
    model.fit(X, y)

    return model


def predict_churn(streak, sessions, days_inactive):
    model = train_churn_model()

    prediction = model.predict_proba([[
        streak,
        sessions,
        days_inactive
    ]])[0][1]

    return round(float(prediction), 2)