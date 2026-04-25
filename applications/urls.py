from django.urls import path
from .views import ApplyJob, MyApplications, JobApplications, GetApplications
from .views import ApplyToJob,HRDashboardApplications, ShortlistedApplications,UpdateApplicationStatus

urlpatterns = [
    path("apply/", ApplyJob.as_view()),
    path("my-applications/", MyApplications.as_view()),
    path("job/<int:job_id>/", JobApplications.as_view()),
    path("list/", GetApplications.as_view()),
    path("apply/<int:job_id>/", ApplyToJob.as_view(), name="apply-job"),
     path("hr-dashboard/", HRDashboardApplications.as_view()),
     path("shortlisted/", ShortlistedApplications.as_view()),
     path("update-status/<int:pk>/", UpdateApplicationStatus.as_view()),
]
