from django.contrib import admin, messages
from django.contrib.contenttypes.prefetch import GenericPrefetch

from applications.models import PolicyFigure
from universities.models import Program, University

from .models import DataChange, ScrapeRun, ScrapeSource


@admin.register(ScrapeSource)
class ScrapeSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "scraper_key", "is_active", "last_run_at"]
    list_filter = ["is_active"]


@admin.register(ScrapeRun)
class ScrapeRunAdmin(admin.ModelAdmin):
    list_display = ["source", "status", "started_at", "records_scraped", "changes_detected"]
    list_select_related = ["source"]
    list_filter = ["status", "source"]
    readonly_fields = ["source", "status", "started_at", "finished_at",
                       "records_scraped", "changes_detected", "error"]


@admin.register(DataChange)
class DataChangeAdmin(admin.ModelAdmin):
    list_display = ["field_name", "target", "old_display", "new_display",
                    "risk", "status", "applied_automatically", "created_at"]
    list_filter = ["status", "risk", "applied_automatically"]
    search_fields = ["field_name"]
    readonly_fields = ["run", "content_type", "object_id", "field_name",
                       "old_display", "new_display", "new_value", "risk",
                       "applied_automatically", "applied_at"]
    actions = ["approve_changes", "reject_changes"]

    def get_queryset(self, request):
        # `target` is a GenericForeignKey — one query per row without a
        # prefetch. Program joins its university because its __str__ reads it.
        return super().get_queryset(request).prefetch_related(
            GenericPrefetch(
                "target",
                [
                    Program.objects.select_related("university"),
                    University.objects.all(),
                    PolicyFigure.objects.all(),
                ],
            )
        )

    @admin.action(description="Approve & apply selected changes")
    def approve_changes(self, request, queryset):
        applied = 0
        for change in queryset.filter(status=DataChange.Status.PENDING_REVIEW):
            change.apply(automatic=False)
            applied += 1
        self.message_user(request, f"Applied {applied} change(s).", messages.SUCCESS)

    @admin.action(description="Reject selected changes")
    def reject_changes(self, request, queryset):
        rejected = queryset.filter(status=DataChange.Status.PENDING_REVIEW).count()
        for change in queryset.filter(status=DataChange.Status.PENDING_REVIEW):
            change.reject()
        self.message_user(request, f"Rejected {rejected} change(s).", messages.WARNING)
