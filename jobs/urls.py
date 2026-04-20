from django.urls import path
from .views import CreateJob, GetJobs, GetSingleJob, UpdateJob, DeleteJob

urlpatterns = [
    path("create/", CreateJob.as_view()),
    path("list/", GetJobs.as_view()),
    path("detail/<int:job_id>/", GetSingleJob.as_view()),
    path("update/<int:job_id>/", UpdateJob.as_view()),
    path("delete/<int:job_id>/", DeleteJob.as_view()),
]