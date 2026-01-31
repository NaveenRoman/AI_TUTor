import json
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


# ======================================================
# LOCAL HR INTERVIEW EVALUATOR (NO OPENAI)
# ======================================================
@csrf_exempt
def hr_interviewer(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body or "{}")

        question = data.get("question", "").strip()
        answer = data.get("answer", "").strip()

        if not question or not answer:
            return JsonResponse(
                {"error": "Question and answer required"},
                status=400
            )

        # -----------------------------
        # SIMPLE LOCAL SCORING LOGIC
        # -----------------------------

        word_count = len(answer.split())

        java_keywords = [
            "java", "jvm", "class", "object",
            "method", "memory", "runtime",
            "inheritance", "polymorphism"
        ]

        keyword_hits = sum(
            1 for k in java_keywords if re.search(rf"\b{k}\b", answer.lower())
        )

        technical_score = min(10, 3 + keyword_hits)
        clarity_score = 8 if word_count > 60 else 5
        communication_score = 7 if "." in answer else 5
        confidence_score = 7 if word_count > 40 else 5

        total_score = round(
            (technical_score + clarity_score + communication_score + confidence_score) / 4,
            1
        )

        if total_score >= 8:
            feedback = "Excellent answer. Strong Java fundamentals."
        elif total_score >= 6:
            feedback = "Good answer. Can improve depth with examples."
        else:
            feedback = "Basic understanding. Revise core Java concepts."

        return JsonResponse({
            "technical_score": technical_score,
            "clarity_score": clarity_score,
            "communication_score": communication_score,
            "confidence_score": confidence_score,
            "total_score": total_score,
            "feedback": feedback
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
