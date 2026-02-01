# core/utils.py
import os
import re
import html
import nltk
from typing import Dict

# Ensure punkt tokenizer present
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


# ----------------------------
# CLEAN / HELPERS
# ----------------------------
def _clean_pdf_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ----------------------------
# TEXT EXTRACTION
# ----------------------------
def extract_text(file_path: str) -> str:
    try:
        fp = file_path.lower()

        if fp.endswith(".pdf"):
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    pages = [p.extract_text() or "" for p in reader.pages]
                    return _clean_pdf_text("\n".join(pages))
            except Exception as e:
                print("[extract_text PDF ERROR]", e)
                return ""

        if fp.endswith((".html", ".htm")):
            try:
                from bs4 import BeautifulSoup
                raw = open(file_path, "r", encoding="utf-8", errors="ignore").read()
                soup = BeautifulSoup(raw, "html.parser")
                return soup.get_text(separator="\n")
            except Exception as e:
                print("[extract_text HTML ERROR]", e)
                return ""

        return open(file_path, "r", encoding="utf-8", errors="ignore").read()

    except Exception as e:
        print("[extract_text ERROR]", e)
        return ""


# ----------------------------
# SECTION SPLITTER
# ----------------------------
def extract_pdf_sections(text: str) -> Dict[str, list]:
    if not text:
        return {"GENERAL": []}

    sentences = nltk.sent_tokenize(text)
    return {"GENERAL": sentences}


# ----------------------------
# SUMMARIZER
# ----------------------------
def summarize_text(text: str) -> Dict[str, str]:
    try:
        sentences = nltk.sent_tokenize(text)
        summary = " ".join(sentences[:5])

        key_html = "<ul>"
        for s in sentences[:5]:
            key_html += f"<li>{html.escape(s)}</li>"
        key_html += "</ul>"

        return {
            "summary": summary,
            "keyPointsHtml": key_html
        }

    except Exception as e:
        print("[summarize_text ERROR]", e)
        return {"summary": "", "keyPointsHtml": ""}


# ----------------------------
# EMBEDDINGS DISABLED
# ----------------------------
def build_embeddings(text: str):
    """
    Disabled in production (Render free plan).
    """
    return {"sentences": [], "embeddings": None}


# ----------------------------
# FORMAT ANSWER
# ----------------------------
def format_answer(question: str, content: str, detail_level: str = "auto") -> str:
    try:
        from .utils_format import format_answer_core
        return format_answer_core(question, content, detail_level)
    except Exception:
        if content:
            return f"<div><h2>Answer</h2><p>{html.escape(content)}</p></div>"
        return "<div><h2>Answer</h2><p>No content available.</p></div>"


# ----------------------------
# DAILY STUDY EMAIL
# ----------------------------
from django.core.mail import send_mail
from core.models import TopicStat


def send_daily_study_email(user):
    weak_topics = (
        TopicStat.objects
        .filter(user=user, mastery_score__lt=40)
        .order_by("mastery_score")[:3]
    )

    if not weak_topics:
        plan = ["Revise current topics"]
    else:
        plan = [f"Revise {t.topic} + 10 questions" for t in weak_topics]

    message = "📘 Your AI Study Plan Today:\n\n"
    message += "\n".join(plan)

    send_mail(
        subject="Your AI Tutor Study Plan",
        message=message,
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False
    )
