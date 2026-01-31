import os
import json
import tempfile
import nltk
import html
import re
import traceback
import threading
from datetime import datetime, timedelta

import requests
import torch
from sentence_transformers import SentenceTransformer, util

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.utils import extract_text, summarize_text, extract_pdf_sections
from core.utils_format import format_answer_core
from core.books_loader import BOOK_KB


# =========================================================
# GLOBAL STORES
# =========================================================
DOCUMENT_STORE = {}   # fileId -> { text, summary, keyPointsHtml, sections }
_model = None

_NEWS_CACHE = {"ts": None, "headlines": []}
_NEWS_CACHE_TTL_SECONDS = 60 * 10  # 10 minutes

VOICE_STATE = {
    "autoplay": False,
    "last_action": None,
    "lock": threading.Lock()
}


# =========================================================
# MODEL / EMBEDDINGS
# =========================================================
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def retrieve_top_k(sentences, embeddings, question, k=4):
    if not sentences or embeddings is None:
        return ""
    try:
        model = get_model()
        q_emb = model.encode(question, convert_to_tensor=True)
        sims = util.cos_sim(q_emb, embeddings)[0]
        k = min(k, len(sentences))
        _, idxs = torch.topk(sims, k)
        idxs = sorted(idxs.tolist())
        return " ".join(sentences[i] for i in idxs)
    except Exception as e:
        print("[retrieve_top_k]", e)
        return ""


# =========================================================
# TEMPLATE / MODE DETECTION
# =========================================================
def detect_template_type(question: str, payload: dict) -> str:
    q = (question or "").lower()
    explicit = (payload.get("template_type") or payload.get("mode") or "").lower()

    if explicit in ("full", "full_topic", "topic", "detailed"):
        return "full_topic"
    if explicit in ("program", "code"):
        return "program"
    if explicit in ("diagnose", "debug"):
        return "diagnose"

    if payload.get("code"):
        return "diagnose"

    if any(x in q for x in ["write program", "generate code", "program to"]):
        return "program"
    if any(x in q for x in ["error", "exception", "debug", "fix this"]):
        return "diagnose"
    if any(x in q for x in ["full explanation", "deep dive", "complete topic"]):
        return "full_topic"

    return "auto"


def choose_language(payload: dict, question: str) -> str:
    lang = (payload.get("language") or "").lower()
    if lang:
        return lang
    q = (question or "").lower()
    if "python" in q:
        return "python"
    if "c++" in q or "cpp" in q:
        return "cpp"
    if "c " in q:
        return "c"
    return "java"


# =========================================================
# FILE UPLOAD
# =========================================================
@csrf_exempt
def upload(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"error": "No file"}, status=400)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            path = tmp.name

        text = extract_text(path)
        summary = summarize_text(text)
        sections = extract_pdf_sections(text)

        model = get_model()
        sec_map = {}
        for h, sents in sections.items():
            if not sents:
                continue
            sec_map[h] = {
                "sentences": sents,
                "embeddings": model.encode(sents, convert_to_tensor=True)
            }

        DOCUMENT_STORE[file.name] = {
            "text": text,
            "summary": summary.get("summary", ""),
            "keyPointsHtml": summary.get("keyPointsHtml", ""),
            "sections": sec_map
        }

        os.remove(path)

        return JsonResponse({
            "fileId": file.name,
            "summary": summary.get("summary", ""),
            "keyPointsHtml": summary.get("keyPointsHtml", "")
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


# =========================================================
# WEATHER & NEWS
# =========================================================
def fetch_weather(city=None):
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        return None, "API key missing"

    if not city:
        city = "Hyderabad"

    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": key, "units": "metric"},
            timeout=6
        )
        r.raise_for_status()
        j = r.json()
        return f"Weather in {city}: {j['weather'][0]['description']}, {j['main']['temp']}°C", None
    except Exception as e:
        return None, str(e)


def _refresh_news_cache(force=False):
    key = os.environ.get("NEWSAPI_KEY")
    if not key:
        return False

    if _NEWS_CACHE["ts"] and not force:
        if (datetime.now() - _NEWS_CACHE["ts"]).seconds < _NEWS_CACHE_TTL_SECONDS:
            return True

    r = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={"apiKey": key, "country": "us"},
        timeout=6
    )
    j = r.json()
    _NEWS_CACHE["headlines"] = [
        f"- {a['title']} ({a['source']['name']})"
        for a in j.get("articles", []) if a.get("title")
    ]
    _NEWS_CACHE["ts"] = datetime.now()
    return True


def fetch_news():
    if not _refresh_news_cache():
        return None, "News API error"
    return "\n".join(_NEWS_CACHE["headlines"][:8]), None


# =========================================================
# MAIN ASK (AI CORE)
# =========================================================
@csrf_exempt
def ask(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
        question = payload.get("question", "")
        fileId = payload.get("fileId")
        book = payload.get("book")
        full = bool(payload.get("full"))
        code = payload.get("code")

        if not question and not code:
            return JsonResponse({"answer": "Ask something"})

        mode = detect_template_type(question, payload)
        language = choose_language(payload, question)

        if code and mode == "diagnose":
            ans = format_answer_core("Code diagnosis", code, template_type="diagnose", language=language)
            return JsonResponse({"answer": ans, "mode": mode})

        ql = question.lower()

        if "time" in ql or "date" in ql:
            now = datetime.now().strftime("%A %d %B %Y, %I:%M %p")
            ans = format_answer_core(question, now, template_type=mode)
            return JsonResponse({"answer": ans})

        if "weather" in ql:
            text, err = fetch_weather()
            ans = format_answer_core(question, text or err)
            return JsonResponse({"answer": ans})

        if "news" in ql:
            text, err = fetch_news()
            ans = format_answer_core(question, text or err)
            return JsonResponse({"answer": ans})

        if fileId and fileId in DOCUMENT_STORE:
            data = DOCUMENT_STORE[fileId]
            best = ""
            best_score = -1
            model = get_model()
            for h, sec in data["sections"].items():
                sims = util.cos_sim(
                    model.encode(question, convert_to_tensor=True),
                    sec["embeddings"]
                )[0]
                score = float(torch.max(sims))
                if score > best_score:
                    best_score = score
                    best = retrieve_top_k(sec["sentences"], sec["embeddings"], question)

            ans = format_answer_core(question, best, template_type=mode, language=language)
            return JsonResponse({"answer": ans, "source": "file"})

        if book and book in BOOK_KB:
            best = ""
            best_score = -1
            model = get_model()
            for h, sec in BOOK_KB[book]["sections"].items():
                sims = util.cos_sim(
                    model.encode(question, convert_to_tensor=True),
                    sec["embeddings"]
                )[0]
                score = float(torch.max(sims))
                if score > best_score:
                    best_score = score
                    best = retrieve_top_k(sec["sentences"], sec["embeddings"], question)

            ans = format_answer_core(question, best, template_type=mode, language=language)
            return JsonResponse({"answer": ans, "source": "book"})

        # global fallback
        best = ""
        best_score = -1
        best_subj = None
        model = get_model()
        for subj, info in BOOK_KB.items():
            for h, sec in info["sections"].items():
                sims = util.cos_sim(
                    model.encode(question, convert_to_tensor=True),
                    sec["embeddings"]
                )[0]
                score = float(torch.max(sims))
                if score > best_score:
                    best_score = score
                    best = retrieve_top_k(sec["sentences"], sec["embeddings"], question)
                    best_subj = subj

        ans = format_answer_core(question, best or "No answer found", template_type=mode, language=language)
        return JsonResponse({"answer": ans, "source": "global", "subject": best_subj})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


# =========================================================
# VOICE + CHAT
# =========================================================
@csrf_exempt
def voice_control(request):
    try:
        if request.method == "GET":
            return JsonResponse(VOICE_STATE)

        payload = json.loads(request.body or "{}")
        action = payload.get("action")

        with VOICE_STATE["lock"]:
            if action == "start":
                VOICE_STATE["autoplay"] = True
            elif action == "stop":
                VOICE_STATE["autoplay"] = False
            elif action == "toggle":
                VOICE_STATE["autoplay"] = not VOICE_STATE["autoplay"]
            VOICE_STATE["last_action"] = action

        return JsonResponse(VOICE_STATE)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def chat(request):
    if request.method == "POST":
        return ask(request)
    if request.method == "GET":
        return JsonResponse({"autoplay": VOICE_STATE["autoplay"]})
    return JsonResponse({"error": "Invalid method"}, status=405)
