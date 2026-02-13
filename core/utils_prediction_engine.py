# core/utils_prediction_engine.py

import joblib
import numpy as np
from core.models import SkillProfile, InterviewSession

MODEL_PATH = "placement_model.pkl"

try:
    model = joblib.load(MODEL_PATH)
except:
    model = None


def calculate_placement_prediction(user):

    profile = SkillProfile.objects.filter(user=user).first()
    if not profile:
        return None

    # =====================================================
    # 🔥 IF ML MODEL EXISTS → USE ML
    # =====================================================
    if model:
        features = np.array([[
            profile.readiness_score,
            profile.technical_score,
            profile.communication_score,
            profile.confidence_score,
            profile.consistency_score,
            getattr(profile, "behavior_score", 0),
        ]])

        probabilities = model.predict_proba(features)[0]
        predicted_class = model.predict(features)[0]

        class_map = {
            2: "Tier-1 Ready",
            1: "Service Ready",
            0: "High Risk"
        }

        return {
            "category": class_map[predicted_class],
            "tier1_probability": round(probabilities[2] * 100, 2),
            "service_probability": round(probabilities[1] * 100, 2),
            "failure_risk": round(probabilities[0] * 100, 2),
        }

    # =====================================================
    # 🧠 FALLBACK HEURISTIC LOGIC (SAFE MODE)
    # =====================================================

    readiness = profile.readiness_score
    behavior = getattr(profile, "behavior_score", 0)
    consistency = profile.consistency_score

    last_sessions = (
        InterviewSession.objects
        .filter(user=user, completed=True)
        .order_by("-created_at")[:3]
    )

    if last_sessions:
        avg_interview = sum(s.average_score for s in last_sessions) / len(last_sessions)
    else:
        avg_interview = 0

    tier1_prob = (
        0.4 * readiness +
        0.3 * behavior +
        0.2 * consistency +
        0.1 * (avg_interview * 10)
    )

    tier1_prob = min(100, round(tier1_prob, 2))

    service_prob = (
        0.5 * readiness +
        0.2 * consistency +
        0.2 * (avg_interview * 10) +
        0.1 * behavior
    )

    service_prob = min(100, round(service_prob, 2))

    failure_risk = max(0, 100 - readiness)
    failure_risk = round(failure_risk, 2)

    if tier1_prob >= 75:
        category = "Tier-1 Ready"
    elif service_prob >= 65:
        category = "Service Ready"
    elif readiness < 40:
        category = "High Risk"
    else:
        category = "Needs Improvement"

    return {
        "tier1_probability": tier1_prob,
        "service_probability": service_prob,
        "failure_risk": failure_risk,
        "category": category,
    }
