# core/utils.py
import os
import re
import html
import nltk
from typing import Dict
from sentence_transformers import SentenceTransformer

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
    text = re.sub(r"-\n", "", text)        # fix hyphen line breaks
    text = re.sub(r"\n{2,}", "\n\n", text) # collapse multiple blanks, keep paragraphs
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ----------------------------
# TEXT EXTRACTION
# ----------------------------
def extract_text(file_path: str) -> str:
    """
    Extract text from PDF, HTML, TXT. If a package is missing returns empty string
    but logs the error to console (so server doesn't crash).
    """
    try:
        fp = file_path.lower()
        if fp.endswith(".pdf"):
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    pages = []
                    for p in reader.pages:
                        pages.append(p.extract_text() or "")
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

        # fallback: plain text
        try:
            return open(file_path, "r", encoding="utf-8", errors="ignore").read()
        except Exception as e:
            print("[extract_text TXT ERROR]", e)
            return ""

    except Exception as e:
        print("[extract_text ERROR]", e)
        return ""


# ----------------------------
# SECTION SPLITTER (PDF-like files)
# ----------------------------
# Basic heading heuristics to make structured summary for a wide range of files
_HEADING_HINTS = [
    r"SUMMARY", r"PROFILE", r"ABOUT", r"EXPERIENCE", r"WORK EXPERIENCE",
    r"PROJECTS", r"EDUCATION", r"SKILLS", r"CERTIFICATIONS", r"ACHIEVEMENTS",
    r"RESPONSIBILITIES", r"INTRODUCTION", r"CHAPTER", r"UNIT", r"SECTION"
]
_HEADING_RE = re.compile(r"^\s*(" + "|".join(_HEADING_HINTS) + r")\b", re.IGNORECASE)


def extract_pdf_sections(text: str) -> Dict[str, list]:
    """
    Use light heuristics to split text into sections keyed by heading.
    If headings aren't obvious returns single GENERAL section.
    """
    if not text:
        return {"GENERAL": []}

    lines = [l.rstrip() for l in text.splitlines()]
    # Merge broken lines heuristically (join lines where the next line begins lowercase)
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # try to join with next lines if continuation (next starts lowercase and current doesn't end with punctuation)
        j = i + 1
        merged_line = line
        while j < len(lines):
            nxt = lines[j].strip()
            if nxt and (not re.search(r"[.!?:]$", merged_line)) and nxt and nxt[0].islower():
                merged_line = merged_line + " " + nxt
                j += 1
            else:
                break

        merged.append(merged_line)
        i = j

    sections = {"GENERAL": []}
    current = "GENERAL"
    found_heading = False

    for line in merged:
        # heading if matches heading regex or short title-like line
        if _HEADING_RE.match(line) or (len(line.split()) <= 6 and line.isupper()):
            key = line.strip().upper()
            if key not in sections:
                sections[key] = []
            current = key
            found_heading = True
        else:
            # split into sentences and append
            for s in nltk.sent_tokenize(line):
                s = s.strip()
                if len(s) > 3:
                    sections[current].append(s)

    # fallback: if no headings found, try to split by paragraphs and create small headings where possible
    if not found_heading:
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        sections = {"GENERAL": []}
        for p in paras:
            lines = p.splitlines()
            # if first line looks like a heading, make it a heading
            first = lines[0].strip()
            if first and (first.isupper() or _HEADING_RE.match(first)):
                key = first.upper()
                rest = " ".join(lines[1:]).strip()
                sections.setdefault(key, [])
                for s in nltk.sent_tokenize(rest):
                    if s.strip():
                        sections[key].append(s.strip())
            else:
                for s in nltk.sent_tokenize(p):
                    if s.strip():
                        sections["GENERAL"].append(s.strip())

    return sections


# ----------------------------
# SUMMARIZER (left panel quick summary)
# ----------------------------
def summarize_text(text: str) -> Dict[str, str]:
    """
    Produces {"summary": short_text, "keyPointsHtml": html_string}
    - summary: quick 2-4 line textual summary assembled from top points
    - keyPointsHtml: grouped bullets per detected heading (HTML UL)
    """
    try:
        secs = extract_pdf_sections(text)
        key_html = ["<ul>"]
        summary_parts = []

        for head, sents in secs.items():
            if not sents:
                continue
            key_html.append(f"<li><b>{html.escape(head.title())}</b><ul>")
            # take up to first 3 representative sentences
            for p in sents[:3]:
                key_html.append(f"<li>{html.escape(p[:260])}</li>")
                if len(summary_parts) < 6:
                    summary_parts.append(f"{head.title()}: {p[:160]}")
            key_html.append("</ul></li>")

        key_html.append("</ul>")
        return {"summary": " ".join(summary_parts[:6]), "keyPointsHtml": "".join(key_html)}
    except Exception as e:
        print("[summarize_text ERROR]", e)
        return {"summary": "", "keyPointsHtml": ""}


# ----------------------------
# EMBEDDINGS BUILDER
# ----------------------------
def build_embeddings(text: str):
    """
    Returns {"sentences":[...], "embeddings": tensor or None}
    """
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        sentences = nltk.sent_tokenize(text or "")
        if not sentences:
            return {"sentences": [], "embeddings": None}
        emb = model.encode(sentences, convert_to_tensor=True)
        return {"sentences": sentences, "embeddings": emb}
    except Exception as e:
        print("[build_embeddings ERROR]", e)
        return {"sentences": [], "embeddings": None}


# ----------------------------
# FORMAT ANSWER (delegates to utils_format)
# ----------------------------
def format_answer(question: str, content: str, detail_level: str = "auto") -> str:
    """
    Thin wrapper that imports the formatting core from utils_format.
    Keeps separation of concerns so format logic can be iterated quickly.
    """
    try:
        from .utils_format import format_answer_core
        return format_answer_core(question, content, detail_level)
    except Exception as e:
        print("[format_answer ERROR]", e)
        # fallback: simple escaped answer
        if content:
            return f"<div class='note-answer'><h2>✅ Answer</h2><p>{html.escape(content)}</p></div>"
        return "<div class='note-answer'><h2>✅ Answer</h2><p>No content available.</p></div>"




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
        from_email="ai@aitutor.com",
        recipient_list=[user.email],
        fail_silently=False
    )
