from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Account created successfully 🎉")
            return redirect("dashboard")  # ✅ redirect works

    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})
