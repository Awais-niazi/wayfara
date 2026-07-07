from rest_framework import generics

from .models import Student
from .serializers import ProfileSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        student, _ = Student.objects.get_or_create(user=self.request.user)
        return student
