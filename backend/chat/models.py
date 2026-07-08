from django.db import models


class Conversation(models.Model):
    """An 'Ask Wayfara' AI chat session, phase-aware per the PRD."""

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="conversations"
    )
    title = models.CharField(max_length=200, blank=True)
    phase_context = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Journey phase the student was in when chatting"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Conversation #{self.pk}"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    class Feedback(models.TextChoices):
        UP = "up", "Thumbs up"
        DOWN = "down", "Thumbs down"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    feedback = models.CharField(
        max_length=5, choices=Feedback.choices, blank=True,
        help_text="Per-answer rating — feeds the AI-satisfaction KPI",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"
