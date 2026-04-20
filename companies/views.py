from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Company
from .serializers import CompanySerializer
from rest_framework import generics


# ✅ CREATE COMPANY
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Company
from .serializers import CompanySerializer

# ✅ GET ONLY THE LOGGED-IN HR'S COMPANY
class GetCompanies(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # FIX: Filter by created_by so users don't see each other's companies
        companies = Company.objects.filter(created_by=request.user)
        serializer = CompanySerializer(companies, many=True)
        return Response(serializer.data)

# ✅ CREATE COMPANY AND LINK TO USER
class CreateCompany(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "hr":
            return Response({"error": "Unauthorized"}, status=403)

        serializer = CompanySerializer(data=request.data)
        if serializer.is_valid():
            # Force the owner to be the current user
            serializer.save(created_by=request.user)
            return Response({"message": "Company created"}, status=201)
        return Response(serializer.errors, status=400)

# ✅ UPDATE ONLY OWN COMPANY
class UpdateCompany(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, company_id):
        company = Company.objects.filter(id=company_id, created_by=request.user).first()
        if not company:
            return Response({"error": "Not allowed"}, status=403)

        serializer = CompanySerializer(company, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Updated"})
        return Response(serializer.errors, status=400)
# ✅ GET SINGLE COMPANY
class GetSingleCompany(APIView):

    def get(self, request, company_id):

        company = Company.objects.filter(id=company_id).first()

        if not company:
            return Response({"error": "Company not found"}, status=404)

        serializer = CompanySerializer(company)

        return Response(serializer.data)


# ✅ UPDATE COMPANY



# ✅ DELETE COMPANY
class DeleteCompany(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, company_id):

        user = request.user

        company = Company.objects.filter(id=company_id, created_by=user).first()

        if not company:
            return Response({"error": "Not found or not allowed"}, status=404)

        company.delete()
        return Response({"message": "Company deleted"})
 # Ensure you have a CompanySerializer

class CompanyDetailView(generics.RetrieveAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    lookup_field = 'id'


class CreateCompanyView(generics.CreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    
    def perform_create(self, serializer):
        # 🔥 This line is the fix! 
        # It forces the 'created_by' field to be the current logged-in user.
        serializer.save(created_by=self.request.user)
    # companies/views.py
    def get_queryset(self):
        return Company.objects.filter(created_by=self.request.user)