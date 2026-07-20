"""Document pool tests: upload caps/types, scoping, download auth, delete."""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Document, Student

User = get_user_model()


def upload_file(name="transcript.pdf", content=b"%PDF-1.4 x", content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class DocumentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="docs@example.com")
        self.student = Student.objects.create(user=self.user)
        self.client.force_authenticate(self.user)

    def upload(self, **overrides):
        payload = {"doc_type": "transcript", "file": upload_file()}
        payload.update(overrides)
        return self.client.post(reverse("documents"), payload, format="multipart")

    def test_upload_and_list(self):
        resp = self.upload()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["doc_type"], "transcript")
        self.assertEqual(resp.data["status"], "uploaded")
        listing = self.client.get(reverse("documents"))
        self.assertEqual(len(listing.data), 1)

    def test_oversized_file_rejected(self):
        big = upload_file(content=b"x" * (10 * 1024 * 1024 + 1))
        resp = self.upload(file=big)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", resp.data)

    def test_wrong_type_rejected(self):
        for bad in (
            upload_file(name="virus.exe", content_type="application/octet-stream"),
            upload_file(name="notes.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ):
            resp = self.upload(file=bad)
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, bad.name)
        self.assertEqual(Document.objects.count(), 0)

    def test_unknown_doc_type_rejected(self):
        resp = self.upload(doc_type="tax_return")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_content_must_match_extension(self):
        # Extension and content-type say PDF/JPG, but the bytes don't — a
        # renamed executable must not enter the document pool.
        for fake in (
            upload_file(name="cv.pdf", content=b"MZ\x90\x00 not a pdf"),
            upload_file(name="photo.jpg", content=b"GIF89a nope", content_type="image/jpeg"),
            upload_file(name="scan.png", content=b"%PDF-1.4 wrong wrapper", content_type="image/png"),
        ):
            resp = self.upload(file=fake)
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, fake.name)
        self.assertEqual(Document.objects.count(), 0)

    def test_genuine_signatures_accepted(self):
        png = upload_file(
            name="passport.png",
            content=b"\x89PNG\r\n\x1a\n rest-of-image",
            content_type="image/png",
        )
        resp = self.upload(doc_type="passport", file=png)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        jpg = upload_file(
            name="photo.jpg", content=b"\xff\xd8\xff\xe0 jfif", content_type="image/jpeg"
        )
        resp = self.upload(doc_type="cv", file=jpg)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_download_is_owner_only(self):
        self.upload()
        doc = Document.objects.get()
        resp = self.client.get(reverse("document_download", args=[doc.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)  # local: streams

        stranger = User.objects.create_user(email="peek@example.com")
        Student.objects.create(user=stranger)
        self.client.force_authenticate(stranger)
        resp = self.client.get(reverse("document_download", args=[doc.pk]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_document_removes_blob(self):
        self.upload()
        doc = Document.objects.get()
        storage, name = doc.file.storage, doc.file.name
        self.assertTrue(storage.exists(name))
        resp = self.client.delete(reverse("document_detail", args=[doc.pk]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.exists())
        self.assertFalse(storage.exists(name))

    def test_cannot_delete_someone_elses(self):
        self.upload()
        doc = Document.objects.get()
        stranger = User.objects.create_user(email="del@example.com")
        Student.objects.create(user=stranger)
        self.client.force_authenticate(stranger)
        resp = self.client.delete(reverse("document_detail", args=[doc.pk]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Document.objects.exists())

    def tearDown(self):
        for doc in Document.objects.all():
            doc.file.delete(save=False)
