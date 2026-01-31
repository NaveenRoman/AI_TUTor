from django.shortcuts import render
from django.http import Http404

def book_topic_page(request, subject, page):
    """
    Loads topic HTML from:
    core/templates/books/<subject>/<page>.html
    """

    template_path = f"books/{subject}/{page}.html"

    try:
        return render(request, template_path)
    except Exception:
        raise Http404("Topic not found")