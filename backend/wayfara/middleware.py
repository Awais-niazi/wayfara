"""Request-body size gate.

The upload serializers cap files at 10 MB — but that check runs only after
Django has already received and spooled the entire body. This middleware
rejects on the declared Content-Length first, so an oversized POST costs one
header read instead of gigabytes of bandwidth and temp-disk churn.

Two ceilings: multipart (document/voice-note uploads) gets 10 MB + form
overhead; everything else is JSON and never legitimately approaches 1 MB.
Chunked requests without a Content-Length pass through — Django's handlers
enforce DATA_UPLOAD_MAX_MEMORY_SIZE on those.
"""

from django.http import JsonResponse

MAX_JSON_BODY_BYTES = 1 * 1024 * 1024
MAX_UPLOAD_BODY_BYTES = 12 * 1024 * 1024


class MaxBodySizeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            content_length = int(request.META.get("CONTENT_LENGTH") or 0)
        except (TypeError, ValueError):
            content_length = 0
        content_type = request.META.get("CONTENT_TYPE", "")
        limit = (
            MAX_UPLOAD_BODY_BYTES
            if content_type.startswith("multipart/")
            else MAX_JSON_BODY_BYTES
        )
        if content_length > limit:
            return JsonResponse(
                {"detail": f"Request body too large (max {limit // (1024 * 1024)} MB)."},
                status=413,
            )
        return self.get_response(request)
