from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count

from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem
from reportlab.lib.pagesizes import A4
from django.utils import timezone
from core.utils_plan import is_feature_allowed, has_active_subscription
from core.models import InterviewSession
from django.db.models.functions import TruncWeek
from core.utils_prediction_engine import calculate_placement_prediction
from django.http import HttpResponseForbidden







from datetime import timedelta




from core.models import ReadinessHistory
from datetime import timedelta



from core.models import (
    InstitutionMembership,
    SkillProfile,
    TopicStat,
)


@login_required
def admin_dashboard(request):

    # --------------------------------------------------
    # 1️⃣ Verify college admin access
    # --------------------------------------------------
    membership = (
        InstitutionMembership.objects
        .select_related("institution")
        .filter(user=request.user, role="college_admin")
        .first()
    )

    if not membership:
        return render(request, "core/not_authorized.html")

    institution = membership.institution

    # --------------------------------------------------
    # 2️⃣ Subscription checks
    # --------------------------------------------------
    if not has_active_subscription(institution):
        return render(request, "core/subscription_expired.html")

    if not is_feature_allowed(institution, "admin_dashboard"):
        return render(request, "core/upgrade_required.html")

    # --------------------------------------------------
    # 3️⃣ Filters
    # --------------------------------------------------
    branch = request.GET.get("branch")
    batch = request.GET.get("batch")

    student_memberships = InstitutionMembership.objects.filter(
        institution=institution,
        role="student"
    )

    if branch:
        student_memberships = student_memberships.filter(branch=branch)

    if batch:
        student_memberships = student_memberships.filter(batch=batch)

    student_ids = student_memberships.values_list("user_id", flat=True)

    # --------------------------------------------------
    # 4️⃣ Skill Profiles
    # --------------------------------------------------
    profiles = SkillProfile.objects.filter(user_id__in=student_ids)

    # --------------------------------------------------
# 🔥 Risk Panel (Behavior + Readiness Combined)
# --------------------------------------------------

    high_risk_students = profiles.filter(risk_level="high").order_by("readiness_score")

    medium_risk_students = profiles.filter(risk_level="medium").order_by("readiness_score")

    low_risk_students = profiles.filter(risk_level="low").order_by("-readiness_score")


    avg_readiness = profiles.aggregate(
        avg=Avg("readiness_score")
    )["avg"] or 0

    not_ready = profiles.filter(readiness_score__lt=40).count()
    moderate = profiles.filter(
        readiness_score__gte=40,
        readiness_score__lt=70
    ).count()
    ready = profiles.filter(readiness_score__gte=70).count()

    top_students = profiles.order_by("-readiness_score")[:10]

    # --------------------------------------------------
    # 5️⃣ Weak Topic Clusters
    # --------------------------------------------------
    weak_topics = (
        TopicStat.objects
        .filter(user_id__in=student_ids, mastery_score__lt=40)
        .values("topic")
        .annotate(student_count=Count("user", distinct=True))
        .order_by("-student_count")[:5]
    )

    # --------------------------------------------------
    # 6️⃣ 🚨 Risk Students Detection
    # --------------------------------------------------
    latest_sessions = (
        InterviewSession.objects
        .filter(user_id__in=student_ids)
        .order_by("user_id", "-created_at")
    )

    latest_per_student = {}
    for session in latest_sessions:
        if session.user_id not in latest_per_student:
            latest_per_student[session.user_id] = session

    risk_students = []

    for user_id, session in latest_per_student.items():
        if session.risk_flag:
            risk_students.append(session)

    risk_students = sorted(
        risk_students,
        key=lambda x: x.user.skillprofile.readiness_score
    )

    # --------------------------------------------------
    # 7️⃣ Growth Trend (Last 30 Days)
    # --------------------------------------------------
    thirty_days_ago = timezone.now() - timedelta(days=30)

    recent_history = ReadinessHistory.objects.filter(
        user_id__in=student_ids,
        recorded_at__gte=thirty_days_ago
    )

    growth_data = (
        recent_history
        .extra(select={'day': "date(recorded_at)"})
        .values('day')
        .annotate(avg_score=Avg("readiness_score"))
        .order_by('day')
    )


    
    # ----------------------------------------
    # 📈 Weekly Interview Growth (Last 8 Weeks)
    # ----------------------------------------



    eight_weeks_ago = timezone.now() - timedelta(weeks=8)

    weekly_growth_qs = (
        InterviewSession.objects
       .filter(
        user_id__in=student_ids,
        created_at__gte=eight_weeks_ago
        )
       .annotate(week=TruncWeek("created_at"))
       .values("week")
       .annotate(avg_score=Avg("average_score"))
       .order_by("week")
)

    growth_data = [
    {
        "week": w["week"].strftime("%b %d"),
        "avg_score": round(w["avg_score"] or 0, 2)
    }
    for w in weekly_growth_qs
    ]


    # --------------------------------------------------
# 🔮 Placement Prediction Distribution
# --------------------------------------------------

    tier1_ready = 0
    service_ready = 0
    high_risk = 0
    needs_improvement = 0

    for profile in profiles:
        prediction = calculate_placement_prediction(profile.user)
        if not prediction:
            continue

        category = prediction["category"]

        if category == "Tier-1 Ready":
            tier1_ready += 1
        elif category == "Service Ready":
            service_ready += 1
        elif category == "High Risk":
            high_risk += 1
        else:
            needs_improvement += 1





    # --------------------------------------------------
    # 8️⃣ Render
    # --------------------------------------------------
    return render(request, "core/admin_dashboard.html", {
        "institution": institution,
        "avg_readiness": round(avg_readiness, 2),
        "not_ready": not_ready,
        "moderate": moderate,
        "ready": ready,
        "risk_students": risk_students,
        "top_students": top_students,
        "weak_topics": weak_topics,
        "growth_data": growth_data,

        "high_risk_students": high_risk_students,
        "medium_risk_students": medium_risk_students,
        "low_risk_students": low_risk_students,


        "tier1_ready": tier1_ready,
        "service_ready": service_ready,
        "high_risk": high_risk,
        "needs_improvement": needs_improvement,


    })





@login_required
def export_placement_report(request):

    membership = (
        InstitutionMembership.objects
        .select_related("institution")
        .filter(user=request.user, role="college_admin")
        .first()
    )

    if not membership:
        return render(request, "core/not_authorized.html")

    institution = membership.institution

    # Plan check AFTER institution defined
    if not is_feature_allowed(institution, "pdf_export"):
        return render(request, "core/upgrade_required.html")

    student_ids = (
        InstitutionMembership.objects
        .filter(institution=institution, role="student")
        .values_list("user_id", flat=True)
    )

    profiles = SkillProfile.objects.filter(user_id__in=student_ids)

    avg_readiness = profiles.aggregate(
        avg=Avg("readiness_score")
    )["avg"] or 0

    not_ready = profiles.filter(readiness_score__lt=40).count()
    moderate = profiles.filter(readiness_score__gte=40, readiness_score__lt=70).count()
    ready = profiles.filter(readiness_score__gte=70).count()

    top_students = profiles.order_by("-readiness_score")[:10]

    weak_topics = (
        TopicStat.objects
        .filter(user_id__in=student_ids, mastery_score__lt=40)
        .values("topic")
        .annotate(student_count=Count("user", distinct=True))
        .order_by("-student_count")[:5]
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="placement_report_{institution.code}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph(
        f"<b>{institution.name} - Placement Analytics Report</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"Generated on: {timezone.now().strftime('%d %b %Y')}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"<b>Average Readiness:</b> {round(avg_readiness,2)}%",
        styles["Heading2"]
    ))
    elements.append(Spacer(1, 0.2 * inch))

    data = [
        ["Category", "Student Count"],
        ["0–40% (Not Ready)", not_ready],
        ["40–70% (Moderate)", moderate],
        ["70–100% (Placement Ready)", ready],
    ]

    table = Table(data, colWidths=[3 * inch, 2 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("<b>Top 10 Students</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    for s in top_students:
        elements.append(Paragraph(
            f"{s.user.username} — {round(s.readiness_score,2)}%",
            styles["Normal"]
        ))

    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("<b>Weak Topic Clusters</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    for t in weak_topics:
        elements.append(Paragraph(
            f"{t['topic']} — {t['student_count']} students weak",
            styles["Normal"]
        ))

    doc.build(elements)
    return response



import uuid
from django.conf import settings

@login_required
def generate_invite_link(request):
    from core.models import Institution

    membership = InstitutionMembership.objects.filter(
        user=request.user,
        role="college_admin"
    ).first()

    if not membership:
        return HttpResponseForbidden("Not allowed")

    institution = membership.institution

    # Create token
    token = uuid.uuid4().hex

    institution.invite_token = token
    institution.save()

    invite_url = f"http://127.0.0.1:8000/college/join/{token}/"

    return render(request, "core/invite_link.html", {
        "invite_url": invite_url
    })
