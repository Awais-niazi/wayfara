"""MaxBodySizeMiddleware: oversized bodies die on the Content-Length header,
before Django spools the payload to disk."""

from django.test import TestCase

from .middleware import MAX_JSON_BODY_BYTES, MAX_UPLOAD_BODY_BYTES


class MaxBodySizeTests(TestCase):
    def test_oversized_json_body_rejected(self):
        resp = self.client.post(
            "/api/v1/profile/",
            data=b"x" * (MAX_JSON_BODY_BYTES + 1),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 413)
        self.assertIn("too large", resp.json()["detail"])

    def test_oversized_multipart_rejected_by_header_alone(self):
        # The middleware trusts Content-Length — no body needs to be sent for
        # the rejection, which is exactly the point.
        # Non-empty body so the test client sets CONTENT_TYPE; the declared
        # length (not the actual payload) is what triggers the rejection.
        resp = self.client.post(
            "/api/v1/documents/",
            data=b"x",
            content_type="multipart/form-data; boundary=x",
            CONTENT_LENGTH=str(MAX_UPLOAD_BODY_BYTES + 1),
        )
        self.assertEqual(resp.status_code, 413)

    def test_normal_bodies_pass_through(self):
        # Unauthenticated → 401 from DRF proves the middleware let it through.
        resp = self.client.post(
            "/api/v1/profile/", data=b"{}", content_type="application/json"
        )
        self.assertNotEqual(resp.status_code, 413)

    def test_multipart_ceiling_is_higher_than_json(self):
        # A 5 MB upload (legal document) must not hit the 1 MB JSON ceiling.
        resp = self.client.post(
            "/api/v1/documents/",
            data=b"x",
            content_type="multipart/form-data; boundary=x",
            CONTENT_LENGTH=str(5 * 1024 * 1024),
        )
        self.assertNotEqual(resp.status_code, 413)
