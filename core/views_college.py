from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.models import InstitutionMembership, SkillProfile
from django.db.models import Avg


@login_required
def college_dashboard(request):

    membership = InstitutionMembership.objects.filter(
        user=request.user,
        role="college_admin"
    ).select_related("institution").first()

    if not membership:
        return render(request, "core/not_authorized.html")

    institution = membership.institution

    # Get all students of this institution
    student_ids = InstitutionMembership.objects.filter(
        institution=institution,
        role="student"
    ).values_list("user", flat=True)

    total_students = len(student_ids)

    avg_readiness = (
        SkillProfile.objects.filter(
            user__in=student_ids
        ).aggregate(avg=Avg("readiness_score"))["avg"] or 0
    )

    return render(request, "core/college_dashboard.html", {
        "institution": institution,
        "total_students": total_students,
        "avg_readiness": round(avg_readiness, 2),
    })
