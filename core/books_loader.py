import os
import re
import nltk
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

from core.models import Book, Chapter

# ================================
# GLOBALS
# ================================

BOOK_KB = {}
EMBED = SentenceTransformer("all-MiniLM-L6-v2")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS_PATH = os.path.join(BASE_DIR, "templates", "books")


# ================================
# HELPERS
# ================================

def extract_order(filename):
    match = re.search(r"topic(\d+)", filename)
    return int(match.group(1)) if match else 9999


def extract_sections_from_html(path):
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
                    sentences = nltk.sent_tokenize(text)
                    sections[current_head].extend(sentences)

        return sections
    except Exception as e:
        print(f"[ERROR] HTML parse failed for {path}: {e}")
        return {}


# ================================
# LOAD BOOKS INTO MEMORY
# ================================

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
        SUBJECT_DATA = {"sections": {}, "folder": subject_folder}

        for fname in sorted(os.listdir(subject_folder), key=extract_order):
            if not fname.endswith(".html"):
                continue

            path = os.path.join(subject_folder, fname)
            print(f"  → Reading {fname}")

            sections = extract_sections_from_html(path)

            for heading, sentences in sections.items():
                if not sentences:
                    continue

                emb = EMBED.encode(sentences, convert_to_tensor=True)

                SUBJECT_DATA["sections"][heading] = {
                    "sentences": sentences,
                    "embeddings": emb,
                    "file": fname,
                }

        BOOK_KB[subject] = SUBJECT_DATA

    print("[INFO] ✅ Book loading complete!")


# ================================
# SYNC BOOKS TO DATABASE (FIXED)
# ================================

def sync_books_to_db():
    print("[INFO] Syncing books to DB...")

    if not os.path.isdir(BOOKS_PATH):
        print("[ERROR] Books folder missing.")
        return

    for subject in os.listdir(BOOKS_PATH):

        subject_folder = os.path.join(BOOKS_PATH, subject)
        if not os.path.isdir(subject_folder):
            continue

        book, _ = Book.objects.get_or_create(
            slug=subject,
            defaults={"title": subject.capitalize()}
        )

        print(f"[INFO] Syncing subject: {subject}")

        for fname in sorted(os.listdir(subject_folder), key=extract_order):

            if not fname.endswith(".html"):
                continue

            match = re.search(r"topic(\d+)", fname)
            if not match:
                continue

            order = int(match.group(1))
            title = fname.replace(".html", "").replace("-", " ").title()

            chapter, created = Chapter.objects.get_or_create(
                book=book,
                order=order,
                defaults={"title": title}
            )

            if not created and chapter.title != title:
                chapter.title = title
                chapter.save()

            if created:
                print(f"   → Created chapter {order}")

    print("[INFO] ✅ DB Sync Complete!")
