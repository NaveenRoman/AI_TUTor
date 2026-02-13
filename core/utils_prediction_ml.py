import joblib
import os
import numpy as np

MODEL_PATH = os.path.join("core", "ml_models", "placement_model.pkl")

def load_model():
    return joblib.load(MODEL_PATH)

def predict_probability(profile):
    model = load_model()

    features = np.array([[
        profile.readiness_score,
        profile.behavior_score,
        profile.technical_score,
        profile.communication_score,
        profile.confidence_score,
    ]])

    prob = model.predict_proba(features)[0][1]
    return round(float(prob), 4)
