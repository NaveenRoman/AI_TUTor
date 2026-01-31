# core/utils_format.py
"""
Improved answer formatter for KnowledgeStream (updated).
- Avoids empty headings / blank sections
- Strips "see above / read above" phrases
- Stable HTML output
- Keeps persona and formats code/theory intelligently
- Adds:
    - render_full_topic(...)   -> structured "full topic" pages
    - render_program_generation(...) -> example program generation helper
    - render_code_diagnostic(...) -> safe static code checks (Python + heuristics for Java/C/C++)
    - format_answer_core(template_type=...) supports 'short'|'full_topic'|'program'|'diagnose'|'auto'
"""

import html
import re
import ast
import traceback
from typing import List, Optional, Dict, Tuple

# -------------------------
# PERSONALITY / MEMORY CONFIG
# -------------------------
FRIENDLY_LEVEL = "companion"   # options: 'light', 'medium', 'companion'
MEMORY_MODE = "full"           # 'none'|'short'|'full'

# -------------------------
# Helpers
# -------------------------
def _escape(s: str) -> str:
    """Escape text for safe HTML output."""
    return html.escape(s or "")

def _contains_any(tokens: List[str], text: str) -> bool:
    """Return True if any token appears in text (case-insensitive)."""
    t = (text or "").lower()
    return any(tok in t for tok in tokens)

def _shorten(s: str, n: int = 200) -> str:
    """Shorten text to approximately n characters without cutting a word."""
    s = (s or "").strip()
    if len(s) <= n:
        return s
    truncated = s[:n].rsplit(" ", 1)[0]
    return truncated + "..."

def _last_nonempty(history: List[Dict]) -> Optional[str]:
    """Find last non-empty message/content in history for pronoun resolution."""
    if not history:
        return None
    for h in reversed(history):
        txt = h.get("text") or h.get("message") or h.get("content")
        if txt and txt.strip():
            return txt.strip()
    return None

# -------------------------
# Sanitizers
# -------------------------
_READ_ABOVE_PATTERNS = [
    r"\bsee above\b",
    r"\bread above\b",
    r"\bsee earlier\b",
    r"\brefer above\b",
    r"\brefer to above\b",
    r"\bas discussed above\b",
    r"\bsee previous\b",
    r"\babove\b"
]

_COMMENTS_REMOVE = [
    r"^from:\s*.*",
    r"^topic\s*:\s*.*",
]

def _strip_contact_info(text: str) -> str:
    """Remove or mask emails, phone numbers, URLs."""
    if not text:
        return ""

    t = text
    t = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[email removed]", t)
    t = re.sub(r"(\+?\d[\d\s\-]{8,}\d)", "[phone removed]", t)
    t = re.sub(r"https?://[^\s]+", "", t)

    cleaned = []
    for ln in t.splitlines():
        low = ln.lower()
        if any(k in low for k in [
            "linkedin.com", "github.com", "instagram.com", "facebook.com",
            "twitter.com", "whatsapp", "phone:", "mobile:", "contact:", "email:"
        ]):
            continue
        cleaned.append(ln)

    return "\n".join(cleaned)

def _remove_personal_data(text: str) -> str:
    """Remove resume-like PII lines: names, colleges, locations."""
    if not text:
        return ""

    heading_patterns = [
        r"\bcurriculum vitae\b",
        r"\bresume\b",
        r"\bcareer objective\b",
        r"\bpersonal details\b",
        r"\bdeclaration\b",
        r"\bstrengths\b",
        r"\bhobbies\b",
        r"\binterests\b",
        r"\bcontact details\b",
        r"\bprofile\b",
        r"\babout me\b"
    ]

    pii_keywords = [
        "college", "university", "hyderabad", "telangana",
        "bangalore", "india", "b.tech", "btech",
        "father's name", "mother's name", "dob", "date of birth"
    ]

    name_keywords = ["naveen", "roman", "pravalika"]

    cleaned = []
    for ln in text.splitlines():
        lstrip = ln.strip()
        low = lstrip.lower()

        if lstrip in ("•", "-", "—"):
            continue
        if any(re.search(p, low) for p in heading_patterns):
            continue
        if any(k in low for k in pii_keywords + name_keywords):
            continue

        cleaned.append(ln)

    return "\n".join(cleaned)

def _strip_repeated_lines(text: str) -> str:
    """Remove repeated identical lines."""
    if not text:
        return ""
    seen = set()
    out = []
    for ln in text.splitlines():
        key = ln.strip().lower()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(ln)
    return "\n".join(out)

def _aggressive_resume_clean(text: str) -> str:
    """Apply Option-B cleaning: remove contact, PII, repeated."""
    if not text:
        return ""
    t = text
    t = _strip_contact_info(t)
    t = _remove_personal_data(t)
    t = _strip_repeated_lines(t)
    return t.strip()

def _sanitize_content(text: str) -> str:
    """Clean noise, repeated phrasing, Option-B resume cleanup."""
    if not text:
        return ""
    t = text.strip()

    # remove injected lines like "From:" "Topic:"
    lines = []
    for ln in t.splitlines():
        l = ln.strip()
        if any(re.match(p, l, flags=re.IGNORECASE) for p in _COMMENTS_REMOVE):
            continue
        lines.append(l)
    t = "\n".join(lines)

    # remove "see above"
    for pat in _READ_ABOVE_PATTERNS:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)

    # collapse whitespace
    t = re.sub(r"\n{2,}", "\n\n", t)
    t = re.sub(r"[ \t]+", " ", t).strip()

    # remove trivial noise lines
    t = "\n".join([ln for ln in t.splitlines() if ln.strip() not in ("-", "—", "•")])

    # Option-B heavy cleaning
    return _aggressive_resume_clean(t)

def _meaningful_sentences(text: str) -> List[str]:
    """Heuristic sentence splitter."""
    if not text:
        return []
    segs = re.split(r'(?<=[\.\?\!])\s+', text)
    out = []
    for s in segs:
        s = s.strip()
        if len(s) < 6:
            continue
        if re.match(r'^(see|refer|read)\b', s, flags=re.IGNORECASE):
            continue
        out.append(s)
    return out

# -------------------------
# Example templates
# -------------------------
def _syntax_template(topic_hint=""):
    """Return short syntax examples."""
    th = (topic_hint or "").lower()

    if "array" in th:
        return """// Java Array Syntax
int[] arr = new int[size];
int[] arr = {10, 20, 30};
int value = arr[0];
for (int i = 0; i < arr.length; i++) {
    System.out.println(arr[i]);
}"""

    if "loop" in th or "for" in th:
        return """// Java Loop Syntax
for (int i = 0; i < n; i++) { ... }
while (condition) { ... }
do { ... } while (condition);"""

    if "exception" in th:
        return """// Java Exception Syntax
try {
    // code
} catch (Exception e) {
    // handle
} finally {
    // cleanup
}"""

    if "class" in th:
        return """// Java Class Syntax
public class Person {
    private String name;
    public Person(String name) { this.name = name; }
    public String getName() { return name; }
}"""

    return "// Syntax examples"


def _example_template(topic_hint=""):
    """Return small example program."""
    th = (topic_hint or "").lower()

    if "array" in th:
        return """// Example: Sum of elements
int[] numbers = {5,10,15,20};
int sum = 0;
for (int n : numbers) sum += n;
System.out.println("Sum = " + sum);"""

    if "loop" in th:
        return """// Example: print 1..10
for (int i = 1; i <= 10; i++) {
    System.out.println(i);
}"""

    return "// Example: Concept illustration"


def _interview_questions(topic_hint=""):
    th = (topic_hint or "").lower()

    if "array" in th:
        return [
            "What is an array?",
            "How do you declare an array in Java?",
            "What is IndexOutOfBoundsException?"
        ]

    if "loop" in th:
        return [
            "Difference between for, while, do-while?",
            "How do you break nested loops?"
        ]

    return ["Explain the core concept of this topic."]


def _common_mistakes(topic_hint=""):
    th = (topic_hint or "").lower()

    if "array" in th:
        return [
            "Index out of bounds",
            "Assuming dynamic size",
            "Incorrect loop limits"
        ]

    if "loop" in th:
        return [
            "Off-by-one errors",
            "Infinite loops",
            "Wrong condition"
        ]

    return ["Incorrect assumptions; test edge cases."]


def _quick_recap(topic_hint=""):
    th = (topic_hint or "").lower()

    if "array" in th:
        return [
            "Arrays store same-type values",
            "Index starts at 0",
            "Fixed size"
        ]

    if "loop" in th:
        return [
            "Use loops for iteration",
            "Avoid infinite loops",
            "Check exit conditions"
        ]

    return ["Understand definition, usage, pitfalls"]


# -------------------------
# Tone helpers
# -------------------------
def _companion_prefix():
    return "Hey there! 😊 I'm Navindhu — your friendly tutor. Here's a structured answer."

def _medium_prefix():
    return "Hi — here's the information you requested."

def _light_prefix():
    return "Answer:"

def _friendly_wrap(parts, level="companion"):
    if level == "companion":
        return "<p style='margin-top:10px;color:#475569;'>Anything else? I can simplify or show examples. ✨</p>"
    if level == "medium":
        return "<p style='margin-top:10px;color:#475569;'>Need deeper explanation?</p>"
    return ""


# -------------------------
# FULL TOPIC RENDERER — CLEAN + FIXED
# -------------------------
def render_full_topic(title: str,
                      content: str,
                      topic_hint: str = "",
                      language: str = "java") -> str:
    """
    Full topic page generator — clean, stable, NO indent errors.
    """
    txt = _sanitize_content(content)
    bullets = _meaningful_sentences(txt)
    th = (topic_hint or title or "").lower()

    parts = []
    parts.append("<div class='full-topic' style='font-family:Inter;color:#0f172a;'>")

    # Header
    parts.append(f"<h1 style='font-size:20px;margin-bottom:6px;'>{_escape(title)}</h1>")
    parts.append("<p style='color:#475569;margin:0 0 12px;'>A complete topic guide — definition, timeline, examples, diagrams, and more.</p>")

    # Definition
    definition = bullets[0] if bullets else txt[:350]
    parts.append("<h3 style='margin:8px 0 6px;'>Definition</h3>")
    parts.append(f"<p style='margin:0 0 10px;'>{_escape(_shorten(definition, 1200))}</p>")

    # Timeline
    parts.append("<h3 style='margin:8px 0 6px;'>Timeline</h3>")
    if "java" in th:
        parts.append("<ul style='margin:6px 0 10px 20px;'>"
                     "<li>1995: Java initial release</li>"
                     "<li>1998: Collections framework</li>"
                     "<li>2004–2010: Major GC/JIT improvements</li>"
                     "<li>2014+: Streams, lambdas, modules, records</li>"
                     "</ul>")
    else:
        for s in bullets[:4]:
            parts.append(f"<p>• {_escape(_shorten(s, 240))}</p>")

    # Features
    parts.append("<h3 style='margin:8px 0 6px;'>Main Features</h3>")
    if "java" in th:
        parts.append("<ul style='margin:6px 0 10px 20px;'>"
                     "<li>Platform independent</li>"
                     "<li>Strong OOP</li>"
                     "<li>Rich standard library</li>"
                     "<li>Optimized JVM (JIT, GC)</li>"
                     "</ul>")
    else:
        if bullets:
            parts.append("<ul style='margin:6px 0 10px 20px;'>")
            for s in bullets[:6]:
                parts.append(f"<li>{_escape(_shorten(s, 220))}</li>")
            parts.append("</ul>")
        else:
            parts.append("<p style='color:#64748b;'>No features found.</p>")

    # Java OOP roots
    if "java" in th:
        parts.append("<h3 style='margin:8px 0 6px;'>OOP Roots / JDK & JVM</h3>")
        parts.append("<p style='margin:0 0 10px;'>Java is built on OOP principles — encapsulation, inheritance, polymorphism. "
                     "The JDK evolved with libraries while the JVM improved through JIT and optimized garbage collection.</p>")

    # Modern features
    parts.append("<h3 style='margin:8px 0 6px;'>Modern Features</h3>")
    if "java" in th:
        parts.append("<p>Modern Java includes lambdas, streams, modules, var inference, records, pattern matching.</p>")
    else:
        parts.append("<p>Modern languages emphasize speed, tooling, libraries, and developer experience.</p>")

    # Real-world uses
    parts.append("<h3 style='margin:8px 0 6px;'>Real-world Use Cases</h3>")
    if bullets:
        for s in bullets[1:5]:
            parts.append(f"<p>{_escape(_shorten(s, 220))}</p>")
    else:
        parts.append("<p style='color:#64748b;'>No examples available.</p>")

    # Diagram placeholder
    parts.append("<h3 style='margin:8px 0 6px;'>Diagram</h3>")
    parts.append("<div style='background:#fff7ed;padding:10px;border:1px solid #fde2b4;border-radius:8px;'>"
                 "[Diagram placeholder]</div>")

    # Program example
    program = _example_template(topic_hint)
    parts.append("<h3 style='margin:8px 0 6px;'>Program Example</h3>")
    parts.append(f"<pre style='background:#f4fffb;padding:10px;border:1px solid #e6f7ec;border-radius:8px;'>{_escape(program)}</pre>")

    # Conclusion
    concluding = bullets[-1] if len(bullets) > 1 else "This topic becomes easier with examples and consistent practice."
    parts.append("<h3 style='margin:8px 0 6px;'>Conclusion</h3>")
    parts.append(f"<p>{_escape(_shorten(concluding, 500))}</p>")

    # Quick sections
    iq = _interview_questions(topic_hint)
    parts.append("<h3 style='margin:8px 0 6px;'>Quick Practice Questions</h3>")
    parts.append("<ul style='margin:6px 0 10px 20px;'>")
    for q in iq:
        parts.append(f"<li>{_escape(q)}</li>")
    parts.append("</ul>")

    ms = _common_mistakes(topic_hint)
    parts.append("<h3 style='margin:8px 0 6px;'>Common Mistakes</h3>")
    parts.append("<ul style='margin:6px 0 10px 20px;'>")
    for m in ms:
        parts.append(f"<li>{_escape(m)}</li>")
    parts.append("</ul>")

    parts.append(_friendly_wrap([], FRIENDLY_LEVEL))
    parts.append("</div>")

    return "\n".join(parts)


# -------------------------
# PROGRAM GENERATION (simple template)
# -------------------------
def render_program_generation(topic: str, language: str = "java"):
    th = (topic or "").lower()
    code = _example_template(th)
    return language.lower(), code


# -------------------------
# CODE DIAGNOSTIC (safe static checker)
# -------------------------
def render_code_diagnostic(code: str, language: str = "python") -> Dict:
    res = {"ok": True, "errors": [], "corrected_code": None, "notes": ""}

    if not code:
        res["ok"] = False
        res["errors"].append({
            "line": None,
            "message": "No code provided.",
            "suggestion": "Paste your code for analysis."
        })
        return res

    lang = (language or "python").lower()

    # -------------------------
    # PYTHON DIAGNOSTICS
    # -------------------------
    if lang == "python":
        try:
            ast.parse(code)
            res["notes"] = "Python AST parse succeeded. No syntax errors detected."
            return res
        except SyntaxError as se:
            lineno = getattr(se, "lineno", None)
            msg = se.msg
            sug = _python_suggestion_for_error(msg, code, lineno)
            res["ok"] = False
            res["errors"].append({"line": lineno, "message": msg, "suggestion": sug})
            fixed = _attempt_simple_python_fix(code)
            if fixed and fixed != code:
                res["corrected_code"] = fixed
            return res

        except Exception as e:
            tb = traceback.format_exc()
            res["ok"] = False
            res["errors"].append({"line": None, "message": str(e), "suggestion": "Parsing failed — inspect the code manually."})
            res["notes"] = tb
            return res

    # -------------------------
    # JAVA / C / C++ DIAGNOSTICS
    # -------------------------
    if lang in ("java", "c", "cpp", "c++"):
        errors = []
        lines = code.splitlines()

        # brace check
        if code.count("{") != code.count("}"):
            errors.append({
                "line": None,
                "message": "Mismatched braces.",
                "suggestion": "Check '{' and '}' — ensure all blocks are closed."
            })

        # missing semicolons
        missing = []
        for i, ln in enumerate(lines, start=1):
            l = ln.strip()
            if not l or l.endswith(";") or l.endswith("{") or l.endswith("}") \
               or l.startswith("//") or l.startswith("/*") or l.endswith(");"):
                continue
            if "(" in l and not l.endswith(";"):
                missing.append(i)

        if missing:
            errors.append({
                "line": missing[0],
                "message": f"Possible missing semicolons on lines: {missing[:5]}",
                "suggestion": "Add ';' where needed."
            })

        res["ok"] = len(errors) == 0
        res["errors"] = errors

        if res["ok"]:
            res["notes"] = "No obvious static issues found. For full accuracy, compile using javac/gcc."
        else:
            res["notes"] = "Static checks suggest potential issues."

        return res

    # -------------------------
    # UNSUPPORTED LANG
    # -------------------------
    res["ok"] = False
    res["errors"].append({
        "line": None,
        "message": f"Language '{language}' not supported for diagnostics.",
        "suggestion": "Use python/java/c/cpp"
    })
    return res


# -------------------------
# PYTHON ERROR HELPERS
# -------------------------
def _python_suggestion_for_error(msg: str, code: str, lineno: Optional[int]):
    low = msg.lower()

    if "unexpected indent" in low:
        return "Check indentation. Use 4 spaces consistently."

    if "invalid syntax" in low:
        return "Possible missing colon ':' or extra characters. Verify parentheses and colons."

    if "unterminated string" in low or "eol while scanning string" in low:
        return "A string is missing a closing quote."

    return "Check syntax near the reported line."


def _attempt_simple_python_fix(code: str):
    try:
        fixed = code.replace("\t", "    ")
        fixed = "\n".join([ln.rstrip() for ln in fixed.splitlines()])
        ast.parse(fixed)
        return fixed
    except Exception:
        return None


# ---------------------------------------------------------
# ⭐ FINAL: MAIN FORMATTER — CLEAN, SAFE, 100% WORKING
# ---------------------------------------------------------
def format_answer_core(
    question: str,
    content: str,
    detail_level: str = "auto",
    history: Optional[List[Dict]] = None,
    template_type: str = "auto",
    language: str = "java"
) -> str:

    q = (question or "").strip()
    c_raw = (content or "").strip()
    history = history or []

    # Option-B sanitize
    c = _sanitize_content(c_raw)
    esc = _escape

    q_low = q.lower()

    small_talk = any(w in q_low for w in [
        "hi", "hello", "hey", "good morning", "good evening",
        "thanks", "thank you"
    ])

    needs_context = any(w in q_low for w in ["this", "that", "it", "they", "these"])

    last_ctx = None
    if needs_context:
        last_ctx = _last_nonempty(history)
        if last_ctx and not c:
            c = _sanitize_content(last_ctx)

    # Full detailed mode requested?
    want_full = detail_level == "long" or any(
        w in q_low for w in ["full", "complete", "deep", "detailed"]
    )

    tt = (template_type or "auto").lower()

    # -----------------------------------------
    # FULL TOPIC TEMPLATE
    # -----------------------------------------
    if tt == "full_topic":
        title = q or "Topic"
        return render_full_topic(title, c, topic_hint=q, language=language)

    # -----------------------------------------
    # PROGRAM TEMPLATE
    # -----------------------------------------
    if tt == "program":
        lang_used, code = render_program_generation(q, language)
        return (
            "<div class='program-answer' style='font-family:Inter;color:#0f172a;'>"
            f"<h3>🧩 Program Example ({esc(lang_used)})</h3>"
            f"<pre style='background:#f4fffb;padding:10px;border-radius:8px;'>{esc(code)}</pre>"
            f"{_friendly_wrap([], FRIENDLY_LEVEL)}"
            "</div>"
        )

    # -----------------------------------------
    # DIAGNOSTIC TEMPLATE
    # -----------------------------------------
    if tt == "diagnose":
        diag = render_code_diagnostic(c, language)
        out = []
        out.append("<div class='diagnose-answer' style='font-family:Inter;color:#0f172a;'>")
        out.append(f"<h3>🔍 Code Diagnostic ({esc(language)})</h3>")

        if diag["ok"]:
            out.append("<p style='color:#16a34a;'>No issues detected.</p>")
            if diag["notes"]:
                out.append(f"<pre>{esc(diag['notes'])}</pre>")
        else:
            for e in diag["errors"]:
                out.append("<div style='background:#fff5f5;padding:10px;border-radius:8px;margin:8px 0;'>")
                out.append(f"<strong>Line: {esc(str(e['line']))}</strong><br>")
                out.append(f"Error: {esc(e['message'])}<br>")
                out.append(f"<span style='color:#991b1b;'>Suggestion: {esc(e['suggestion'])}</span>")
                out.append("</div>")

            if diag.get("corrected_code"):
                out.append("<h4>Corrected Code</h4>")
                out.append(f"<pre>{esc(diag['corrected_code'])}</pre>")

        out.append(_friendly_wrap([], FRIENDLY_LEVEL))
        out.append("</div>")
        return "\n".join(out)

    # ==================================================================
    # NORMAL ANSWER MODE (SHORT or AUTO)
    # ==================================================================

    bullets = _meaningful_sentences(c)
    topic_text = q_low + " " + c.lower()
    code_keywords = ["array", "loop", "class", "method", "exception", "string", "file"]
    theory_keywords = ["history", "evolution", "features", "advantages"]

    include_code = any(k in topic_text for k in code_keywords) and not any(
        k in topic_text for k in theory_keywords
    )
    topic_hint = next((k for k in code_keywords if k in topic_text), "")

    # -----------------------------------------
    # SMALL TALK
    # -----------------------------------------
    if small_talk and not c:
        return "<div class='note-answer'><p>Hey! 😊 How can I help you today?</p></div>"

    # -----------------------------------------
    # START OUTPUT
    # -----------------------------------------
    out = []
    out.append("<div class='note-answer' style='font-family:Inter;color:#0f172a;'>")

    # tone prefix
    if FRIENDLY_LEVEL == "companion":
        out.append(f"<div style='font-weight:600;margin-bottom:8px;'>{esc(_companion_prefix())}</div>")
    elif FRIENDLY_LEVEL == "medium":
        out.append(f"<div style='font-weight:600;margin-bottom:8px;'>{esc(_medium_prefix())}</div>")
    else:
        out.append(f"<div style='font-weight:600;margin-bottom:8px;'>{esc(_light_prefix())}</div>")

    # -----------------------------------------
    # FULL DETAILED ANSWER
    # -----------------------------------------
    if want_full:
        # overview
        out.append("<h3>🧠 Overview</h3>")
        if c:
            out.append(f"<p>{esc(_shorten(c,2000))}</p>")
        else:
            out.append("<p style='color:#64748b;'>No content found.</p>")

        # syntax + example
        if include_code:
            syn = _syntax_template(topic_hint)
            ex = _example_template(topic_hint)
            out.append("<h3>⚙️ Syntax</h3>")
            out.append(f"<pre>{esc(syn)}</pre>")
            out.append("<h3>📌 Example</h3>")
            out.append(f"<pre>{esc(ex)}</pre>")

        # key points
        if bullets:
            out.append("<h3>💡 Key Concepts</h3><ul>")
            for b in bullets[:12]:
                out.append(f"<li>{esc(_shorten(b,400))}</li>")
            out.append("</ul>")

        # interview
        iq = _interview_questions(topic_hint)
        out.append("<h3>🗒️ Interview Questions</h3><ul>")
        for qx in iq:
            out.append(f"<li>{esc(qx)}</li>")
        out.append("</ul>")

        # mistakes
        ms = _common_mistakes(topic_hint)
        out.append("<h3>⚠️ Common Mistakes</h3><ul>")
        for m in ms:
            out.append(f"<li>{esc(m)}</li>")
        out.append("</ul>")

        # recap
        rc = _quick_recap(topic_hint)
        out.append("<h3>💬 Quick Recap</h3><ul>")
        for r in rc:
            out.append(f"<li>{esc(r)}</li>")
        out.append("</ul>")

        out.append(_friendly_wrap([], FRIENDLY_LEVEL))
        out.append("</div>")
        return "\n".join(out)

    # -----------------------------------------
    # NORMAL SHORT ANSWER
    # -----------------------------------------
    out.append("<h3>✅ Answer</h3>")
    if c:
        out.append(f"<p>{esc(_shorten(c,1200))}</p>")
    else:
        out.append("<p style='color:#64748b;'>No source content available.</p>")

    # summary bullets
    if bullets:
        out.append("<h3>📘 Summary Notes</h3><ul>")
        for b in bullets[:6]:
            out.append(f"<li>{esc(_shorten(b,300))}</li>")
        out.append("</ul>")

    # quick syntax
    if include_code:
        syn = _syntax_template(topic_hint)
        out.append("<h3>⚙️ Quick Syntax</h3>")
        out.append(f"<pre>{esc(syn)}</pre>")

    # recap
    rc = _quick_recap(topic_hint)
    out.append("<h3>💬 Quick Recap</h3><ul>")
    for r in rc:
        out.append(f"<li>{esc(r)}</li>")
    out.append("</ul>")

    out.append(_friendly_wrap([], FRIENDLY_LEVEL))
    out.append("</div>")
    return "\n".join(out)
