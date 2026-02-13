from django.shortcuts import render
from core.models import SkillProfile


def public_student_profile(request, username):

    profile = SkillProfile.objects.select_related("user").get(
        user__username=username
    )

    return render(request, "core/public_profile.html", {
        "profile": profile
    })
