from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from core.models import InstitutionMembership, PlatformAdmin


# =========================================================
# SIGNUP FORM
# =========================================================

from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from core.models import Institution, InstitutionMembership

User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    date_of_birth = forms.DateField(
    required=True,
    widget=forms.DateInput(
        attrs={
            "type": "date"
        }
    )
)

    branch = forms.CharField(required=True)
    year = forms.CharField(required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "date_of_birth",
            "branch",
            "year",
            "password1",
            "password2",
        )


def signup(request):

    institution_code = request.GET.get("institution")
    institution = None

    if institution_code:
        institution = Institution.objects.filter(code=institution_code).first()

    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()

            # 🔥 Attach student to institution
            if institution:
                InstitutionMembership.objects.create(
                    user=user,
                    institution=institution,
                    role="student",
                    branch=form.cleaned_data["branch"],
                    batch=form.cleaned_data["year"],
                )

            auth_login(request, user)
            messages.success(request, "Account created successfully 🎉")
            return redirect("dashboard")

    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {
        "form": form,
        "institution": institution
    })



# =========================================================
# SIGNUP VIEW
# =========================================================

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Account created successfully 🎉")
            return redirect("role_redirect")  # 🔥 IMPORTANT

    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})


# =========================================================
# ROLE BASED REDIRECT
# =========================================================

@login_required
def role_based_redirect(request):

    user = request.user

    # 👑 SUPER ADMIN
    if PlatformAdmin.objects.filter(
        user=user,
        is_super_admin=True
    ).exists():
        return redirect("super_admin_dashboard")

    # 🏫 COLLEGE ADMIN
    if InstitutionMembership.objects.filter(
        user=user,
        role="college_admin"
    ).exists():
        return redirect("admin_dashboard")

    # 👨‍🎓 STUDENT
    return redirect("dashboard")


from django.shortcuts import get_object_or_404
from core.models import Institution, InstitutionMembership
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden

def college_join_signup(request, token):

    institution = get_object_or_404(Institution, invite_token=token)

    # 🔐 Check student limit
    current_students = InstitutionMembership.objects.filter(
        institution=institution,
        role="student"
    ).count()

    if current_students >= institution.student_limit:
        return HttpResponseForbidden("Student limit reached for this college.")

    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()

            InstitutionMembership.objects.create(
                user=user,
                institution=institution,
                role="student"
            )

            auth_login(request, user)
            return redirect("dashboard")

    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {
        "form": form,
        "institution": institution
    })
