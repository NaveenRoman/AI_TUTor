from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.models import Institution, SkillProfile
from django.db.models import Avg, Sum


@login_required
def super_admin_dashboard(request):

    # -----------------------------------------
    # 🔐 HARD FOUNDER LOCK
    # -----------------------------------------
    if not (
        request.user.username == "Naveen" and
        request.user.email == "naveenrom232@gmail.com"
    ):
        return render(request, "core/not_authorized.html")

    institutions = Institution.objects.all()


    # --------------------------------------------------
    # Platform-wide analytics
    # --------------------------------------------------
    total_colleges = institutions.count()
    total_students = SkillProfile.objects.count()

    avg_readiness = (
        SkillProfile.objects.aggregate(
            avg=Avg("readiness_score")
        )["avg"] or 0
    )

    total_revenue = (
        Institution.objects.filter(is_active=True)
        .aggregate(total=Sum("monthly_price"))["total"] or 0
    )

    college_analytics = []

    # --------------------------------------------------
    # Per College Analytics
    # --------------------------------------------------
    for inst in institutions:

        student_ids = inst.institutionmembership_set.filter(
            role="student"
        ).values_list("user", flat=True)

        avg = SkillProfile.objects.filter(
            user__in=student_ids
        ).aggregate(avg=Avg("readiness_score"))["avg"] or 0

        college_analytics.append({
            "name": inst.name,
            "avg_readiness": round(avg, 2),
            "students": len(student_ids),
            "plan": inst.plan,
        })

    return render(request, "core/super_admin_dashboard.html", {
        "institutions": institutions,
        "total_colleges": total_colleges,
        "total_students": total_students,
        "total_revenue": total_revenue,
        "college_analytics": college_analytics,
        "avg_readiness": round(avg_readiness, 2),
    })
