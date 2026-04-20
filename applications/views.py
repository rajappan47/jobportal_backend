from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Application
from .serializers import ApplicationSerializer
from candidates.models import CandidateProfile
from jobs.models import Job

from django.conf import settings
from ai_engine.services import extract_text_from_file, analyze_application_ats


import os, shutil, threading
from django.conf import settings


# ✅ APPLY JOB
class ApplyJob(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        profile = CandidateProfile.objects.filter(user=user).first()
        if not profile:
            return Response({"error": "Create profile first"}, status=400)

        job_id = request.data.get("job")
        job = Job.objects.filter(id=job_id).first()

        if not job:
            return Response({"error": "Job not found"}, status=404)

        # 🚫 prevent duplicate
        if Application.objects.filter(candidate=profile, job=job).exists():
            return Response({"error": "Already applied"}, status=400)

        serializer = ApplicationSerializer(data=request.data)

        if serializer.is_valid():

            # 🔥 MATCH SCORE LOGIC
            skills = (profile.skills or "").lower()
            required = (job.required_skills or "").lower()

            match = 0
            for skill in required.split(","):
                if skill.strip() in skills:
                    match += 20

            match_score = min(match, 100)

            # 🔥 STATUS
            status_value = "shortlisted" if match_score >= 60 else "rejected"

            # 🔥 SUGGESTIONS
            suggestions = ""
            if match_score < 60:
                suggestions = f"Improve these skills: {job.required_skills}"

            serializer.save(
                candidate=profile,
                job=job,
                match_score=match_score,
                status=status_value,
                suggestions=suggestions
            )

            return Response({
                "message": "Applied successfully",
                "match_score": match_score,
                "status": status_value
            }, status=201)

        return Response(serializer.errors, status=400)


# ✅ GET MY APPLICATIONS (CANDIDATE)
class MyApplications(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        profile = CandidateProfile.objects.filter(user=user).first()

        if not profile:
            return Response({"error": "Profile not found"}, status=404)

        applications = Application.objects.filter(candidate=profile).order_by("-created_at")

        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)


# ✅ HR VIEW APPLICATIONS FOR A JOB
class JobApplications(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        user = request.user

        job = Job.objects.filter(id=job_id, posted_by=user).first()

        if not job:
            return Response({"error": "Not allowed"}, status=403)

        applications = Application.objects.filter(job=job)

        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)


# ✅ COMMON API (FIXED VERSION)
class GetApplications(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if hasattr(user, "role") and user.role == "hr":
            applications = Application.objects.filter(job__posted_by=user)

        else:
            # 🔥 FIX HERE
            profile = CandidateProfile.objects.filter(user=user).first()

            if not profile:
                return Response({"error": "Profile not found"}, status=404)

            applications = Application.objects.filter(candidate=profile)

        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)



# 2. THE BACKGROUND FUNCTION (Paste it here!)
def process_application_background(application, resume_path, jd_text):
    try:
        resume_text = extract_text_from_file(resume_path)
        analysis = analyze_application_ats(resume_text, jd_text)
        
        application.match_score = analysis.get("match_score", 0)
        application.suggestions = analysis.get("suggestions", "")
        application.status = "shortlisted" if analysis.get("is_shortlisted") else "rejected"
        application.save()
    except Exception as e:
        application.status = "rejected"
        application.suggestions = "Technical error during AI screening. Please try again."
        application.save()
        print(f"Background Process Error: {e}")

class ApplyToJob(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        user = request.user

        # ✅ Step 1: Automatically fetch Candidate Profile and Resume
        try:
            profile = CandidateProfile.objects.get(user=user)
        except CandidateProfile.DoesNotExist:
            return Response({"error": "Profile not found. Please complete your profile."}, status=400)

        # ✅ Step 2: Automatically fetch Job Description
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=404)

        if not profile.resume:
            return Response({"error": "Please upload a resume to your profile first."}, status=400)

        if Application.objects.filter(candidate=profile, job=job).exists():
            return Response({"error": "You have already applied for this position."}, status=400)

        # ✅ Step 3: Create a Snapshot of the Resume
        original_path = profile.resume.path
        file_name = os.path.basename(original_path)
        new_rel_path = f"applications/{file_name}"
        full_new_path = os.path.join(settings.MEDIA_ROOT, new_rel_path)

        os.makedirs(os.path.dirname(full_new_path), exist_ok=True)
        shutil.copy(original_path, full_new_path)

        # ✅ Step 4: Create Application Record (Initial status: applied)
        jd_combined = f"{job.title}\n{job.description}\n{job.required_skills}"
        application = Application.objects.create(
            candidate=profile,
            job=job,
            resume_file=new_rel_path,
            status='applied'
        )

        # ✅ Step 5: Trigger AI Processing in a Background Thread
        threading.Thread(
            target=process_application_background,
            args=(application, full_new_path, jd_combined)
        ).start()

        return Response({
            "message": "Application submitted! Our AI is evaluating your profile.",
            "status": "processing"
        }, status=status.HTTP_201_CREATED)



class HRDashboardApplications(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ✅ Filter only shortlisted candidates for jobs posted by this HR
        # Sorted by highest match_score first
        applications = Application.objects.filter(
            job__posted_by=request.user,
            status='shortlisted'
        ).select_related('candidate__user', 'job').order_by('-match_score')

        data = []

        for app in applications:
            data.append({
                "id": app.id,
                # Try to get full name from profile, fallback to username
                "candidate_name": app.candidate.name if hasattr(app.candidate, 'name') else app.candidate.user.username,
                "job_title": app.job.title,
                "score": round(app.match_score, 1), # Rounded for clean UI
                "resume": request.build_absolute_uri(app.resume_file.url) if app.resume_file else None,
                "applied_at": app.created_at.strftime("%Y-%m-%d"), # Formatted date
            })

        return Response(data)