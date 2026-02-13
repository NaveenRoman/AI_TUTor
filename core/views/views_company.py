from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from core.models import CompanyUser, SkillProfile
from core.utils_prediction_engine import calculate_placement_prediction


@login_required
def company_dashboard(request):

    company_user = CompanyUser.objects.filter(
        user=request.user
    ).select_related("company").first()

    if not company_user:
        return render(request, "core/not_authorized.html")

    min_readiness = request.GET.get("min_readiness")
    branch = request.GET.get("branch")

    profiles = SkillProfile.objects.all().select_related("user")

    if min_readiness:
        profiles = profiles.filter(readiness_score__gte=min_readiness)

    candidates = []

    for profile in profiles:

        prediction = calculate_placement_prediction(profile.user)

        candidates.append({
            "username": profile.user.username,
            "readiness": profile.readiness_score,
            "behavior": getattr(profile, "behavior_score", 0),
            "prediction": prediction
        })

    # Sort by readiness descending
    candidates = sorted(
        candidates,
        key=lambda x: x["readiness"],
        reverse=True
    )

    return render(request, "core/company_dashboard.html", {
        "company": company_user.company,
        "candidates": candidates[:50]
    })


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.models import SkillProfile, InterviewResponse


@login_required
def student_profile_view(request, username):

    profile = SkillProfile.objects.select_related("user").get(
        user__username=username
    )

    interviews = InterviewResponse.objects.filter(
        session__user__username=username
    ).order_by("-created_at")[:20]

    return render(request, "core/company_student_profile.html", {
        "profile": profile,
        "interviews": interviews
    })
