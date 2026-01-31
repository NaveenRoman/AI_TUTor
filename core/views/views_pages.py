from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def index_page(request):
    return render(request, "index.html")

def categories_page(request):
    return render(request, "categories.html")

def ai_tutor_page(request):
    return render(request, "ai_tutor.html")

def contact_page(request):
    return render(request, "contact.html")

@login_required
def interview_page(request):
    return render(request, "interview.html")


