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


from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from datetime import datetime
from .models import Application



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
# applications/views.py

from django.db.models import Q

class ShortlistedApplications(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # We fetch all candidates who are progressing or completed (Hired)
        applications = Application.objects.filter(
            job__posted_by=request.user,
            status__in=['shortlisted', 'interview', 'hired']
        ).select_related('candidate__user', 'job').order_by('-match_score')

        jobs_dict = {}
        for app in applications:
            job_id = app.job.id
            if job_id not in jobs_dict:
                jobs_dict[job_id] = {
                    "job_id": job_id,
                    "job_title": app.job.title,
                    "candidates": []
                }
            
            user_profile = app.candidate.user 
            jobs_dict[job_id]["candidates"].append({
                "id": app.id,
                "candidate_name": user_profile.name or user_profile.email,
                "email": user_profile.email,
                "phone": getattr(user_profile, 'phone', 'N/A'),
                "match_score": round(app.match_score, 1),
                "status": app.status.lower(), 
                "resume_url": request.build_absolute_uri(app.resume_file.url) if app.resume_file else None,
                "suggestions": app.suggestions,
                "applied_date": app.created_at.strftime("%d %b %Y"),
                "location": "Chennai, TN"
            })

        return Response(list(jobs_dict.values()))



class UpdateApplicationStatus(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            application = Application.objects.get(id=pk)
            new_status = request.data.get("status")
            
            user_profile = application.candidate.user
            candidate_name = user_profile.name or user_profile.email
            job_title = application.job.title
            company_name = getattr(application.job.posted_by, 'company_name', 'Our Company')
            recipient_email = user_profile.email

            # --- CASE 1: INTERVIEW INVITATION (LAYOUT UNCHANGED) ---
            if new_status == 'interview':
                interview_date_raw = request.data.get("interview_date")
                if not interview_date_raw:
                    return Response({"error": "Interview date is required"}, status=400)

                dt_obj = datetime.strptime(interview_date_raw, '%Y-%m-%dT%H:%M')
                formatted_date = dt_obj.strftime('%A, %B %d at %I:%M %p')

                subject = f"Interview Invitation: {job_title} at {company_name}"
                html_content = f"""
                <div style="background-color: #f9fafb; padding: 40px 10px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #374151;">
                    <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                        <div style="background-color: #00b894; padding: 30px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Interview Invitation</h1>
                        </div>
                        <div style="padding: 40px 30px;">
                            <p style="font-size: 16px; line-height: 24px;">Hello <strong>{candidate_name}</strong>,</p>
                            <p style="font-size: 16px; line-height: 24px;">Thank you for your interest in the <strong>{job_title}</strong> position. We were impressed with your background and would like to invite you for a virtual interview.</p>
                            <div style="background-color: #f3f4f6; border-radius: 8px; padding: 20px; margin: 30px 0;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr><td style="padding-bottom: 10px; font-size: 14px; color: #6b7280; text-transform: uppercase;">Date & Time</td></tr>
                                    <tr><td style="font-size: 18px; font-weight: bold; color: #111827;">{formatted_date}</td></tr>
                                    <tr><td style="padding-top: 15px; padding-bottom: 5px; font-size: 14px; color: #6b7280; text-transform: uppercase;">Location</td></tr>
                                    <tr><td style="font-size: 16px; color: #111827;">Virtual Meeting (Link to be shared)</td></tr>
                                </table>
                            </div>
                            <p style="font-size: 15px; color: #6b7280;">Please confirm if this time works for you by replying to this email.</p>
                        </div>
                    </div>
                </div>
                """
                application.status = 'interview'
                application.interview_date = interview_date_raw
                application.save()

            # --- CASE 2: REJECTION (LAYOUT UNCHANGED) ---
            elif new_status == 'rejected':
                subject = f"Update regarding your application - {company_name}"
                html_content = f"""
                <div style="background-color: #f9fafb; padding: 40px 10px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #374151;">
                    <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                        <div style="padding: 40px 30px;">
                            <h2 style="color: #111827; margin-top: 0;">Application Update</h2>
                            <p style="font-size: 16px; line-height: 24px;">Dear <strong>{candidate_name}</strong>,</p>
                            <p style="font-size: 16px; line-height: 24px;">After careful consideration, we have decided to move forward with other candidates at this time.</p>
                            <p style="font-size: 16px; line-height: 24px;">We wish you the best of luck in your career search.</p>
                            <br><p style="font-size: 15px; font-weight: bold; margin: 0;">Sincerely,</p>
                            <p style="font-size: 15px; margin: 5px 0;">The Hiring Team</p>
                        </div>
                    </div>
                </div>
                """
                application.status = 'rejected'
                application.save()

            # --- CASE 3: HIRED (NEW PROFESSIONAL TEMPLATE) ---
            elif new_status == 'hired':
                if application.status != 'interview':
                    return Response({"error": "Candidate must be interviewed before hiring"}, status=400)
                
                subject = f"Congratulations! Job Offer for {job_title} at {company_name}"
                html_content = f"""
                <div style="background-color: #f0fdf4; padding: 40px 10px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1f2937;">
                    <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #d1fae5; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">
                        <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 40px; text-align: center;">
                            <div style="background: rgba(255,255,255,0.2); width: 60px; height: 60px; border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; line-height: 60px; font-size: 30px;">🎉</div>
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.025em;">You're Hired!</h1>
                        </div>
                        <div style="padding: 40px 35px;">
                            <p style="font-size: 18px; line-height: 28px; color: #111827;">Dear <strong>{candidate_name}</strong>,</p>
                            <p style="font-size: 16px; line-height: 26px;">We are absolutely thrilled to formally offer you the position of <strong>{job_title}</strong> at <strong>{company_name}</strong>!</p>
                            <p style="font-size: 16px; line-height: 26px;">Out of a highly competitive pool of applicants, your skills and passion truly stood out to our team. We believe you will be a fantastic addition to our culture and mission.</p>
                            
                            <div style="margin: 35px 0; border-left: 4px solid #10b981; padding-left: 20px; background: #f9fafb; padding: 20px; border-radius: 0 8px 8px 0;">
                                <h4 style="margin: 0 0 10px 0; color: #059669; text-transform: uppercase; font-size: 13px; letter-spacing: 0.05em;">Next Steps</h4>
                                <p style="margin: 0; font-size: 15px; color: #4b5563;">Our HR Onboarding team will reach out to you within 24 hours with your formal offer letter and documentation details.</p>
                            </div>

                            <p style="font-size: 16px; line-height: 26px;">Welcome aboard! We can't wait to see the amazing things you'll achieve with us.</p>
                            
                            <div style="margin-top: 40px; border-top: 1px solid #f3f4f6; padding-top: 25px;">
                                <p style="font-size: 15px; font-weight: bold; margin: 0; color: #111827;">Best Regards,</p>
                                <p style="font-size: 15px; margin: 5px 0; color: #6b7280;">The Hiring & Leadership Team</p>
                                <p style="font-size: 14px; color: #10b981; font-weight: 600;">{company_name}</p>
                            </div>
                        </div>
                        <div style="background-color: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #9ca3af;">
                            Sent via {company_name} Career Portal
                        </div>
                    </div>
                </div>
                """
                application.status = 'hired'
                application.save()

            # --- SEND EMAIL (Common Logic) ---
            if new_status in ['interview', 'rejected', 'hired']:
                text_content = strip_tags(html_content)
                email = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [recipient_email])
                email.attach_alternative(html_content, "text/html")
                email.send()

            return Response({"message": f"Candidate successfully {new_status}!"})

        except Exception as e:
            return Response({"error": str(e)}, status=500)