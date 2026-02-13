import os
import sys

# ---------------------------------------------
# Add project root to Python path
# ---------------------------------------------
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

sys.path.append(BASE_DIR)

# ---------------------------------------------
# Setup Django
# ---------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_tutor.settings")

import django
django.setup()

# ---------------------------------------------
# ML Imports
# ---------------------------------------------
import joblib
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from core.models import SkillProfile


# =====================================================
# Generate Training Data
# =====================================================
def generate_training_data():
    profiles = SkillProfile.objects.all()

    X = []
    y = []

    for p in profiles:

        features = [
            p.readiness_score,
            p.technical_score,
            p.communication_score,
            p.confidence_score,
            p.consistency_score,
            getattr(p, "behavior_score", 0),
        ]

        # ---------------------------------------
        # TEMP LABEL LOGIC (Replace with real later)
        # ---------------------------------------
        if p.readiness_score >= 75:
            label = 2   # Tier-1
        elif p.readiness_score >= 50:
            label = 1   # Service
        else:
            label = 0   # Fail

        X.append(features)
        y.append(label)

    return np.array(X), np.array(y)


# =====================================================
# Train Model
# =====================================================
def train():
    X, y = generate_training_data()

    if len(X) < 10:
        print("Not enough data to train model.")
        return

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            multi_class="multinomial",
            max_iter=1000
        ))
    ])

    model.fit(X, y)

    model_path = os.path.join(BASE_DIR, "core", "ml", "placement_model.pkl")
    joblib.dump(model, model_path)

    print("✅ Model trained and saved at:", model_path)


if __name__ == "__main__":
    train()
