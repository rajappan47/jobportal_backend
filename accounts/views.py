from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegisterSerializer

from django.contrib.auth import authenticate   # 🔥 ADD THIS
from rest_framework.authtoken.models import Token  # 🔥 KEEP THIS


# ✅ REGISTER
class RegisterUser(APIView):
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully"}, status=201)

        return Response(serializer.errors, status=400)


# ✅ LOGIN (FIXED 🔥)
class LoginUser(APIView):

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        print("EMAIL:", email)
        print("PASSWORD:", password)

        user = authenticate(request, username=email, password=password)
        print("USER:", user)
        if user is not None:
            token, _ = Token.objects.get_or_create(user=user)  # 🔥 IMPORTANT

            return Response({
                "token": token.key,   # 🔥 SEND TOKEN
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "name": user.name
                }
            })

        return Response(
            {"error": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )