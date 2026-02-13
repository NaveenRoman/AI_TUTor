from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from core.models import CompanyUser, SkillProfile


@csrf_exempt
@login_required
def company_filter_students(request):

    # Verify company access
    company_user = CompanyUser.objects.filter(
        user=request.user
    ).select_related("company").first()

    if not company_user:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        min_readiness = float(request.GET.get("min_readiness", 60))
        risk_allowed = request.GET.get("risk", "low")

        students = SkillProfile.objects.filter(
            readiness_score__gte=min_readiness
        )

        if risk_allowed != "all":
            students = students.filter(risk_level=risk_allowed)

        students = students.order_by("-readiness_score")[:50]

        data = [
            {
                "username": s.user.username,
                "readiness": s.readiness_score,
                "behavior_score": s.behavior_score,
                "risk_level": s.risk_level
            }
            for s in students
        ]

        return JsonResponse({
            "results": data,
            "count": len(data)
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from core.models import CompanyUser, SkillProfile
from core.utils_prediction_ml import predict_probability


@csrf_exempt
@login_required
def company_filter_students(request):

    company_user = CompanyUser.objects.filter(
        user=request.user
    ).select_related("company").first()

    if not company_user:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        min_readiness = float(request.GET.get("min_readiness", 50))
        min_probability = float(request.GET.get("min_probability", 0.4))

        profiles = SkillProfile.objects.filter(
            readiness_score__gte=min_readiness
        )

        ranked = []

        for p in profiles:
            prob = predict_probability(p)

            if prob >= min_probability:
                ranked.append({
                    "username": p.user.username,
                    "readiness": p.readiness_score,
                    "behavior_score": p.behavior_score,
                    "probability": prob,
                    "risk_level": p.risk_level
                })

        ranked = sorted(
            ranked,
            key=lambda x: x["probability"],
            reverse=True
        )

        return JsonResponse({
            "results": ranked[:50],
            "count": len(ranked)
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
