# core/views_quiz.py (SAFE VERSION – matches your models.py)
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import QuizChapter, QuizAttempt
from django.utils import timezone

@csrf_exempt
def get_quiz(request):
    """Return latest quiz (exam mode)"""
    quiz_id = request.GET.get('quiz_id')

    if quiz_id:
        try:
            qc = QuizChapter.objects.get(pk=quiz_id)
            return JsonResponse({
                'quiz_id': qc.id,
                'questions': qc.questions_json
            })
        except QuizChapter.DoesNotExist:
            return JsonResponse({'error': 'Quiz not found'}, status=404)

    # return latest
    qc = QuizChapter.objects.order_by('-created_at').first()
    if not qc:
        return JsonResponse({'questions': []})
    return JsonResponse({'quiz_id': qc.id, 'questions': qc.questions_json})


@csrf_exempt
def start_quiz(request):
    """
    Simple start — DOES NOT require QuizInstance.
    Returns timestamp only.
    """
    try:
        data = json.loads(request.body or '{}')
        quiz_id = data.get("quiz_id")

        qc = QuizChapter.objects.get(pk=quiz_id)

        return JsonResponse({
            "started": True,
            "quiz_id": quiz_id,
            "started_at": timezone.now().isoformat()
        })
    except Exception as e:
        return HttpResponseBadRequest(str(e))


@csrf_exempt
def submit_quiz(request):
    """
    Save student answers inside QuizAttempt (matches your models.py)
    """
    try:
        data = json.loads(request.body or '{}')

        quiz_id = data.get("quiz_id")
        student = data.get("student") or "anonymous"
        answers = data.get("answers", {})

        qc = QuizChapter.objects.get(pk=quiz_id)

        attempt = QuizAttempt.objects.create(
            user=None,  # You will attach real user in Phase 5
            quiz=qc,
            answers_json=answers,
            submitted_at=timezone.now()
        )

        return JsonResponse({
            "status": "submitted",
            "attempt_id": attempt.id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def proctor_log(request):
    """
    DISABLED — You do not have ProctorLog model.
    For now return ok.
    """
    return JsonResponse({"ok": True})
