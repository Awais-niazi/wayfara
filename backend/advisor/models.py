from django.conf import settings
from django.db import models


class AdvisorThread(models.Model):
    """A private conversation between a student and their human advisor.

    Deliberately separate from chat.Conversation (that is the AI 'Ask
    Wayfara' assistant). This is human-to-human, paid, and scoped to the
    student's assigned advisor. One thread per student.
    """

    student = models.OneToOneField(
        "students.Student", on_delete=models.CASCADE, related_name="advisor_thread"
    )
    # Snapshot of the advisor at thread creation. If a student is reassigned,
    # history stays intact; the service refreshes this to the current advisor.
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="advisor_threads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_message_at"]

    def __str__(self):
        return f"Thread: {self.student} ⇄ {self.advisor}"


class AdvisorMessage(models.Model):
    thread = models.ForeignKey(
        AdvisorThread, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    # A message is text, a voice note, or both — body may be blank if audio is set.
    body = models.TextField(blank=True)
    audio = models.FileField(upload_to="advisor_audio/%Y/%m/", null=True, blank=True)
    audio_duration_seconds = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Null until the *other* participant has seen it — drives unread counts.
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["thread", "created_at"])]

    def __str__(self):
        return f"{self.sender}: {self.body[:50] or '[voice note]'}"
