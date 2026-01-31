# core/quiz_generator.py
import re
import random
import json
from typing import List, Dict
from .utils_format import _meaningful_sentences, _sanitize_content

# Conservative text cleaning wrapper
def clean_text(raw: str) -> List[str]:
    s = _sanitize_content(raw or "")
    sents = _meaningful_sentences(s)
    return sents

# Utility to pick random sentences safely
def pick_sentences(sentences: List[str], n: int) -> List[str]:
    if not sentences:
        return []
    if len(sentences) <= n:
        return sentences[:]
    return random.sample(sentences, n)

# 1) MCQ generator (simple but meaningful)
def generate_mcq_from_sentences(sentences: List[str], count: int = 10) -> List[Dict]:
    out = []
    pick = pick_sentences(sentences, max(count, min(len(sentences), count)))
    for s in pick[:count]:
        words = re.findall(r"\w+", s)
        if len(words) < 4: words = [w for w in re.findall(r"\w+", s) if len(w) > 4]
        if not words: continue
        
        correct = words[0]
        distractors = random.sample(
        [w for w in words if w != correct],
        min(3, len(words) - 1) )
        while len(distractors) < 3:
            distractors.append(correct[::-1])
            
            
            options = [correct] + distractors[:3]
            random.shuffle(options)
            question_text = re.sub(
                  re.escape(correct),  "_____",  s, count=1,  flags=re.IGNORECASE )
            out.append({
                  "question": f"Fill in the blank: {question_text}",
                "options": options,
                "answer": correct })
            continue

        # choose a key word (prefer nouns/long words heuristically)
        words_sorted = sorted(words, key=lambda w: (-len(w), w))
        correct = words_sorted[0]
        # build distractors: different words from sentence or scrambled
        distractors = []
        for w in words_sorted[1:]:
            if w.lower() != correct.lower() and len(distractors) < 2:
                distractors.append(w)
        # fill remaining distractors with plausible variations
        while len(distractors) < 3:
            distractors.append(correct[::-1][:len(correct)])
        options = [correct] + distractors[:3]
        random.shuffle(options)
        qtext = re.sub(re.escape(correct), "_____", s, flags=re.IGNORECASE)
        question = f"(MCQ) Fill the blank: {qtext}"
        out.append({
            "question": question,
            "options": options,
            "answer": correct
        })
    return out

# 2) Fill-in-the-blank generator
def generate_fill_from_sentences(sentences: List[str], count: int = 5) -> List[Dict]:
    out = []
    pick = pick_sentences(sentences, count)
    for s in pick:
        words = re.findall(r"\w+", s)
        if len(words) < 4:
            continue
        # choose a mid-sentence word to mask
        idx = max(1, min(len(words) - 2, len(words) // 3))
        missing = words[idx]
        # replace only first occurrence of word (case-insensitive)
        pattern = re.compile(re.escape(missing), flags=re.IGNORECASE)
        qtext = pattern.sub("_____", s, count=1)
        out.append({"question": qtext, "answer": missing})
    return out

# 3) Short answer questions
def generate_short_from_sentences(sentences: List[str], count: int = 5) -> List[Dict]:
    out = []
    pick = pick_sentences(sentences, count)
    for s in pick:
        q = f"(Short) In 1-3 sentences, explain: \"{s[:100]}...\""
        out.append({"question": q, "answer": s})
    return out

# 4) Long answer questions
def generate_long_from_sentences(sentences: List[str], count: int = 3) -> List[Dict]:
    out = []
    pick = pick_sentences(sentences, count)
    for s in pick:
        q = f"(Long) Write a detailed answer about: \"{s[:120]}...\" (250-400 words)"
        out.append({"question": q, "answer": s})
    return out

# 5) Program questions (outline)
def generate_program_questions(sentences: List[str], count: int = 2) -> List[Dict]:
    out = []
    pick = pick_sentences(sentences, count)
    for s in pick:
        q = f"(Program) Design and write a program related to: \"{s[:90]}...\""
        out.append({"question": q, "notes": "Write code, include sample input and output."})
    return out

# Full mixed quiz generator (25 questions configured)
def generate_mixed_quiz_from_text(raw_text: str, total_questions: int = 25) -> Dict:
    sentences = clean_text(raw_text)
    # desired distribution for 25 Q:
    # MCQ 10, Fill 5, Short 5, Long 3, Program 2 = 25
    mcq_n = 10
    fill_n = 5
    short_n = 5
    long_n = 3
    prog_n = 2
    # generate
    mcq = generate_mcq_from_sentences(sentences, mcq_n)
    fill = generate_fill_from_sentences(sentences, fill_n)
    short = generate_short_from_sentences(sentences, short_n)
    long = generate_long_from_sentences(sentences, long_n)
    program = generate_program_questions(sentences, prog_n)
    # flatten to ensure totals (in rare cases of shortages)
    quiz = {
        "mcq": mcq,
        "fill": fill,
        "short": short,
        "long": long,
        "program": program
    }
    return quiz

# Helper to combine multiple subjects' text
def combine_texts_from_sections(sections_texts: List[str]) -> str:
    return "\n\n".join(s for s in sections_texts if s)


# ------------------------------------------------------------
# SIMPLE FULL CHAPTER QUIZ GENERATOR (used by generate_quiz)
# ------------------------------------------------------------
def generate_full_quiz(text):
    """
    Generates a full quiz set (MCQ, Fill, Short, Long, Program).
    Used by Chapter Quiz API.
    """

    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 25]
    if not sentences:
        return {"mcq": [], "fill": [], "short": [], "long": [], "program": []}

    quiz = {
        "mcq": [],
        "fill": [],
        "short": [],
        "long": [],
        "program": []
    }

    # -------------------------
    # 1️⃣ MCQ (Real options)
    # -------------------------
    for i, s in enumerate(sentences[:5]):
        words = [w for w in re.findall(r"\w+", s) if len(w) > 4]

        if not words:
            continue

        correct = words[0]

        # create distractors from other words
        distractors = random.sample(
            [w for w in words if w != correct],
            min(3, len(words) - 1)
        )

        while len(distractors) < 3:
            distractors.append(correct[::-1])

        options = [correct] + distractors[:3]
        random.shuffle(options)

        question_text = re.sub(
            re.escape(correct),
            "_____",
            s,
            count=1,
            flags=re.IGNORECASE
        )

        quiz["mcq"].append({
            "question": f"Fill in the blank: {question_text}",
            "options": options,
            "answer": correct
        })

    # -------------------------
    # 2️⃣ Fill in the blank
    # -------------------------
    for s in sentences[5:10]:
        words = s.split()
        if len(words) < 4:
            continue

        answer = words[-1]
        q = s.replace(answer, "______", 1)

        quiz["fill"].append({
            "question": q,
            "answer": answer
        })

    # -------------------------
    # 3️⃣ Short Answer
    # -------------------------
    for s in sentences[10:13]:
        quiz["short"].append({
            "question": f"Explain: {s}",
            "answer": ""
        })

    # -------------------------
    # 4️⃣ Long Answer
    # -------------------------
    for s in sentences[13:15]:
        quiz["long"].append({
            "question": f"Write a detailed note on: {s}",
            "answer": ""
        })

    # -------------------------
    # 5️⃣ Program
    # -------------------------
    quiz["program"].append({
        "question": "Write a simple program related to this chapter topic.",
        "answer": ""
    })

    return quiz


# ------------------------------------------------------------
# Helper: Combine multiple chapter texts for daily quiz
# ------------------------------------------------------------
def combine_texts_from_sections(text_list):
    return "\n".join(text_list)


# ------------------------------------------------------------
# Mix generator for daily quiz (MCQ + fill + short + long)
# ------------------------------------------------------------
def generate_mixed_quiz_from_text(text, total_questions=25):
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
    if not sentences:
        return {"mcq": [], "fill": [], "short": [], "long": [], "program": []}

    quiz = {"mcq": [], "fill": [], "short": [], "long": [], "program": []}

    # 1) MCQ – 10
    for s in sentences[:10]:
        words = [w for w in re.findall(r"\w+", s) if len(w) > 4]
        if len(words) < 2:continue

    correct = words[0]

    distractors = random.sample(
        [w for w in words if w.lower() != correct.lower()],
        min(3, len(words) - 1)
    )

    while len(distractors) < 3:
        distractors.append(correct[::-1])

    options = [correct] + distractors[:3]
    random.shuffle(options)

    question_text = re.sub(
        re.escape(correct),
        "_____",
        s,
        count=1,
        flags=re.IGNORECASE
    )

    quiz["mcq"].append({
        "question": f"Fill in the blank: {question_text}",
        "options": options,
        "answer": correct
    })


    # 2) Fill – 5
    for s in sentences[10:15]:
        parts = s.split()
        if len(parts) < 4:
            continue
        ans = parts[-1]
        q = s.replace(ans, "______")
        quiz["fill"].append({"question": q, "answer": ans})

    # 3) Short – 5
    for s in sentences[15:20]:
        quiz["short"].append({
            "question": f"Explain briefly: {s}",
            "answer": ""
        })

    # 4) Long – 4
    for s in sentences[20:24]:
        quiz["long"].append({
            "question": f"Write a detailed answer on: {s}",
            "answer": ""
        })

    # 5) Program – 1
    quiz["program"].append({
        "question": "Write a simple program based on today's topic.",
        "answer": ""
    })

    return quiz
