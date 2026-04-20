from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Job
from .serializers import JobSerializer
from companies.models import Company


# 🔥 CREATE JOB (ONLY OWN COMPANY)
class CreateJob(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Security: Check if this HR actually has a company profile
        company = Company.objects.filter(created_by=user).first()

        if not company:
            return Response({"error": "Please create a Company Profile first"}, status=403)

        serializer = JobSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                posted_by=user,
                company=company # Force the job to be linked to Rajappan's company
            )
            return Response({"message": "Job created"}, status=201)
        return Response(serializer.errors, status=400)

# 🔥 GET JOBS (HR → own jobs, Candidate → all jobs)
#from rest_framework.permissions import IsAuthenticated

class GetJobs(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == "hr":
            jobs = Job.objects.filter(posted_by=user)  # only own jobs
        else:
            jobs = Job.objects.all()  # candidate sees all jobs

        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)


# 🔥 GET SINGLE JOB
class GetSingleJob(APIView):

    def get(self, request, job_id):

        job = Job.objects.filter(id=job_id).first()

        if not job:
            return Response({"error": "Job not found"}, status=404)

        serializer = JobSerializer(job)
        return Response(serializer.data)


# 🔥 UPDATE JOB (ONLY OWNER)
class UpdateJob(APIView):

    permission_classes = [IsAuthenticated]

    def put(self, request, job_id):

        user = request.user

        job = Job.objects.filter(id=job_id, posted_by=user).first()

        if not job:
            return Response({"error": "Not allowed"}, status=403)

        serializer = JobSerializer(job, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Updated"})

        return Response(serializer.errors, status=400)


# 🔥 DELETE JOB (ONLY OWNER)
class DeleteJob(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, job_id):

        user = request.user

        job = Job.objects.filter(id=job_id, posted_by=user).first()

        if not job:
            return Response({"error": "Not allowed"}, status=403)

        job.delete()
        return Response({"message": "Deleted"})