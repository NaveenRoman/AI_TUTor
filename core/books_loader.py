import os
import re
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from core.models import Book, Chapter
from django.db import transaction


BOOK_KB = {}
EMBED = None


# IMPORTANT FIX: Correct books folder path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS_PATH = os.path.join(BASE_DIR, "templates", "books")


def extract_page_title(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        if soup.title and soup.title.text.strip():
            return soup.title.text.strip()

        h1 = soup.find("h1")
        if h1:
            return h1.text.strip()

    except Exception:
        pass

    return None


def simple_sentence_split(text):
    """
    Lightweight sentence splitter (production safe).
    Avoids nltk dependency.
    """
    sentences = re.split(r'(?<=[.!?]) +', text)
    return [s.strip() for s in sentences if s.strip()]


def extract_sections_from_html(path):
    """Extract text by headings (<h1>, <h2>, <h3>)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        sections = {}
        current_head = "General"
        sections[current_head] = []

        for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            if tag.name in ["h1", "h2", "h3"]:
                current_head = tag.get_text().strip()
                sections[current_head] = []
            else:
                text = tag.get_text().strip()
                if text:
                    sentences = simple_sentence_split(text)
                    sections[current_head].extend(sentences)

        return sections

    except Exception as e:
        print(f"[ERROR] HTML parse failed for {path}: {e}")
        return {}


def load_books():
    global BOOK_KB
    BOOK_KB.clear()

    if not os.path.isdir(BOOKS_PATH):
        print("[ERROR] books folder missing:", BOOKS_PATH)
        return

    print(f"[INFO] Loading books from: {BOOKS_PATH}")

    for subject in os.listdir(BOOKS_PATH):
        subject_folder = os.path.join(BOOKS_PATH, subject)
        if not os.path.isdir(subject_folder):
            continue

        print(f"[INFO] Subject: {subject}")

        book, _ = Book.objects.get_or_create(
            slug=subject,
            defaults={"title": f"{subject.title()} Programming"}
        )

        SUBJECT_DATA = {"sections": {}, "folder": subject_folder}

        files = sorted(
            [f for f in os.listdir(subject_folder) if f.endswith(".html")],
            key=lambda x: int(re.search(r"(\d+)", x).group(1)) if re.search(r"(\d+)", x) else 999
        )

        with transaction.atomic():
            for fname in files:
                path = os.path.join(subject_folder, fname)
                print(f"  → Reading {fname}")

                m = re.search(r"(\d+)", fname)
                if not m:
                    continue
                order = int(m.group(1))

                sections = extract_sections_from_html(path)

                page_title = extract_page_title(path)
                title = page_title or fname.replace(".html", "")

                Chapter.objects.update_or_create(
                    book=book,
                    order=order,
                    defaults={"title": title}
                )

                for heading, sentences in sections.items():
                    if not sentences:
                        continue

                    emb = None

                    SUBJECT_DATA["sections"][heading] = {
                        "sentences": sentences,
                        "embeddings": emb,
                        "file": fname,
                    }

        BOOK_KB[subject] = SUBJECT_DATA

    print("[INFO] ✅ Book loading complete!")
