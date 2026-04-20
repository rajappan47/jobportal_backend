from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Education
from .serializers import EducationSerializer
from rest_framework.permissions import IsAuthenticated
from .models import CandidateProfile
from .serializers import CandidateProfileSerializer

# ✅ ADD
class AddEducation(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        user = request.user   # 🔥 automatic

        serializer = EducationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=user)
            return Response({"message": "Education added"}, status=201)

        return Response(serializer.errors, status=400)


# ✅ GET (only logged-in user data)
class GetEducation(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user   # 🔥 important

        educations = Education.objects.filter(user=user)

        serializer = EducationSerializer(educations, many=True)

        return Response(serializer.data)


#  DELETE (only own data)
class DeleteEducation(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, edu_id):

        user = request.user

        edu = Education.objects.filter(id=edu_id, user=user).first()

        if not edu:
            return Response({"error": "Not found or not allowed"}, status=404)

        edu.delete()
        return Response({"message": "Deleted successfully"})

class UpdateEducation(APIView):

    permission_classes = [IsAuthenticated]

    def put(self, request, edu_id):

        user = request.user

        # ✅ Only logged-in user's data
        edu = Education.objects.filter(id=edu_id, user=user).first()

        if not edu:
            return Response({"error": "Not found or not allowed"}, status=404)

        serializer = EducationSerializer(edu, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Education updated successfully"})

        return Response(serializer.errors, status=400)




# ✅ CREATE PROFILE
class CreateProfile(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        user = request.user

        # prevent duplicate profile
        if CandidateProfile.objects.filter(user=user).exists():
            return Response({"error": "Profile already exists"}, status=400)

        serializer = CandidateProfileSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=user)
            return Response({"message": "Profile created"}, status=201)

        return Response(serializer.errors, status=400)


# ✅ GET PROFILE
class GetProfile(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        profile = CandidateProfile.objects.filter(user=user).first()

        if not profile:
            return Response({"error": "Profile not found"}, status=404)

        serializer = CandidateProfileSerializer(profile)

        return Response(serializer.data)


# ✅ UPDATE PROFILE
class UpdateProfile(APIView):

    permission_classes = [IsAuthenticated]

    def put(self, request):

        user = request.user

        profile = CandidateProfile.objects.filter(user=user).first()

        if not profile:
            return Response({"error": "Profile not found"}, status=404)

        serializer = CandidateProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated"})

        return Response(serializer.errors, status=400)


# ✅ DELETE PROFILE
class DeleteProfile(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request):

        user = request.user

        profile = CandidateProfile.objects.filter(user=user).first()

        if not profile:
            return Response({"error": "Profile not found"}, status=404)

        profile.delete()
        return Response({"message": "Profile deleted"})