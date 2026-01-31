from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

# =========================================================
# BOOKS & CONTENT
# =========================================================

class Book(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=400)
    description = models.TextField(blank=True)
    folder = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=400)
    heading_id = models.CharField(max_length=400, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["book", "order"]
        indexes = [
            models.Index(fields=["book", "order"]),
            models.Index(fields=["heading_id"]),
        ]

    def __str__(self):
        return f"{self.book.title} — {self.title}"


# =========================================================
# USER PROFILE (CORE BRAIN)
# =========================================================

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    bio = models.TextField(blank=True)

    # Gamification
    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)
    streak = models.PositiveIntegerField(default=0)

    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    weekly_quiz_enabled = models.BooleanField(default=True)

    # Current learning context
    current_book = models.ForeignKey(
        Book, on_delete=models.SET_NULL, null=True, blank=True, related_name="active_users"
    )
    current_chapter = models.ForeignKey(
        Chapter, on_delete=models.SET_NULL, null=True, blank=True, related_name="active_users"
    )

    ai_mode = models.CharField(
        max_length=20,
        choices=[("global", "Global"), ("book", "Book")],
        default="global"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user})"


# =========================================================
# BOOK & CHAPTER PROGRESS
# =========================================================

class BookProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="book_progress")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="user_progress")

    completed_chapters = models.PositiveIntegerField(default=0)
    total_chapters = models.PositiveIntegerField(default=0)
    percent_complete = models.FloatField(default=0.0)

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "book")
        indexes = [
            models.Index(fields=["user", "book"]),
            models.Index(fields=["percent_complete"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.book} ({self.percent_complete:.1f}%)"


class UserChapterProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chapter_progress")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="user_progress")

    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("user", "chapter")

    def mark_done(self):
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save()

    def __str__(self):
        return f"{self.user} — {self.chapter} (done={self.completed})"
    

class ChapterProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "chapter")



# =========================================================
# QUIZ SYSTEM (CHAPTER / FULL QUIZ)
# =========================================================

class QuizChapter(models.Model):
    subject = models.CharField(max_length=200)
    chapter = models.CharField(max_length=400)
    quiz_type = models.CharField(max_length=50, default="full")

    questions_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} — {self.chapter}"


class QuizInstance(models.Model):
    quiz = models.ForeignKey(
        QuizChapter, on_delete=models.CASCADE,
        related_name="instances", null=True, blank=True
    )
    student_id = models.CharField(max_length=200, default="anon")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    client_info = models.JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return f"Instance {self.id} ({self.student_id})"


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey(QuizChapter, on_delete=models.CASCADE, null=True, blank=True)
    instance = models.ForeignKey(QuizInstance, on_delete=models.SET_NULL, null=True, blank=True)

    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)

    duration_seconds = models.IntegerField(null=True, blank=True)
    answers_json = models.JSONField(default=dict, blank=True, null=True)

    score = models.FloatField(null=True, blank=True)
    correct_count = models.IntegerField(null=True, blank=True)
    total_questions = models.IntegerField(null=True, blank=True)

    mistakes = models.JSONField(default=list, blank=True, null=True)

    ai_tip = models.TextField(blank=True, null=True)

   




# =========================================================
# TOPIC MASTERY (AI ANALYTICS CORE)
# =========================================================

class TopicStat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    topic = models.CharField(max_length=400)

    attempts = models.IntegerField(default=0)
    correct = models.IntegerField(default=0)
    mastery_score = models.FloatField(default=0.0)
    last_attempted = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user}-{self.topic} ({self.mastery_score})"


# =========================================================
# DAILY QUIZ (SIMPLE VERSION – KEPT AS YOU WROTE)
# =========================================================

class DailyQuiz(models.Model):
    date = models.DateField(unique=True)
    questions_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Daily Quiz - {self.date}"


# =========================================================
# WEEKLY QUIZ
# =========================================================

class WeeklyQuiz(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    week_start = models.DateField()
    questions_json = models.JSONField(default=dict)
    score = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "week_start")

    def __str__(self):
        return f"WeeklyQuiz({self.user} - {self.week_start})"


# =========================================================
# NOTIFICATIONS
# =========================================================

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    body = models.TextField()
    payload = models.JSONField(default=dict, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)


# =========================================================
# PROCTOR LOGS
# =========================================================

class ProctorLog(models.Model):
    quiz_instance = models.ForeignKey(
        QuizInstance, on_delete=models.CASCADE,
        null=True, blank=True, related_name="proctor_logs"
    )
    student_id = models.CharField(max_length=255, blank=True, null=True)
    event = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ProctorLog({self.student_id}) at {self.timestamp}"


# =========================================================
# DAILY QUIZ QUESTION BANK
# =========================================================

class DailyQuizQuestion(models.Model):
    subject = models.CharField(max_length=100)
    question = models.TextField()

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)

    correct_option = models.CharField(
        max_length=1,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]
    )

    difficulty = models.CharField(
        max_length=20,
        choices=[
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("hard", "Hard"),
        ],
        default="medium"
    )

    def __str__(self):
        return f"{self.subject} – {self.question[:40]}"


# =========================================================
# DAILY QUIZ ATTEMPT (PER USER / PER DAY)
# =========================================================

class DailyQuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)

    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    time_taken_seconds = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "date")  # ✅ only one attempt per day

    def __str__(self):
        return f"{self.user} – {self.date} – {self.score}"


class TopicQuiz(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    topic = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.topic}"

