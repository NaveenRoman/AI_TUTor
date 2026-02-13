from statistics import pstdev
from core.models import SkillProfile


def analyze_session_behavior(session):

    responses = session.responses.order_by("created_at")

    if responses.count() < 2:
        return

    scores = [r.total_score for r in responses]
    lengths = [r.answer_length for r in responses]
    confidence_values = [r.confidence_score for r in responses]
    times = [r.time_taken_seconds for r in responses]

    # -----------------------------------
    # 1️⃣ Performance Slope
    # -----------------------------------
    performance_slope = scores[-1] - scores[0]

    # -----------------------------------
    # 2️⃣ Score Consistency
    # -----------------------------------
    deviation = pstdev(scores)
    consistency_score = max(0, 100 - (deviation * 10))

    # -----------------------------------
    # 3️⃣ Confidence Trend
    # -----------------------------------
    confidence_trend = confidence_values[-1] - confidence_values[0]

    # -----------------------------------
    # 4️⃣ Time Stability
    # -----------------------------------
    time_deviation = pstdev(times)
    time_stability = max(0, 100 - (time_deviation * 5))

    # -----------------------------------
    # 5️⃣ Final Behavior Score
    # -----------------------------------
    behavior_score = (
        0.3 * consistency_score +
        0.3 * max(0, confidence_trend * 10) +
        0.2 * max(0, performance_slope * 10) +
        0.2 * time_stability
    )

    # -----------------------------------
    # Store in session
    # -----------------------------------
    session.performance_slope = round(performance_slope, 2)
    session.consistency_score = round(consistency_score, 2)
    session.confidence_trend = round(confidence_trend, 2)

    # Optional legacy flag
    session.risk_flag = (
        performance_slope < -2 or consistency_score < 40
    )

    session.save()

    # -----------------------------------
    # Update Skill Profile
    # -----------------------------------
    profile, _ = SkillProfile.objects.get_or_create(user=session.user)

    profile.behavior_score = round(behavior_score, 2)

    # -----------------------------------
    # Risk Escalation Logic (FINAL)
    # -----------------------------------
    if (
        profile.readiness_score < 40 and
        profile.behavior_score < 50 and
        performance_slope < 0
    ):
        profile.risk_level = "high"
    elif profile.behavior_score < 60:
        profile.risk_level = "medium"
    else:
        profile.risk_level = "low"

    profile.save()
