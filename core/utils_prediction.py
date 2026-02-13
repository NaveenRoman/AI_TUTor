from django.db.models import Avg
from core.models import SkillProfile, InstitutionMembership

def placement_prediction(institution):

    students = InstitutionMembership.objects.filter(
        institution=institution,
        role="student"
    ).values_list("user", flat=True)

    profiles = SkillProfile.objects.filter(user__in=students)

    avg_readiness = profiles.aggregate(
        avg=Avg("readiness_score")
    )["avg"] or 0

    if avg_readiness >= 70:
        return "High placement probability (70%+ likely selection)"
    elif avg_readiness >= 50:
        return "Moderate placement probability"
    else:
        return "Low placement probability — needs intervention"
