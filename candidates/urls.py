from django.urls import path
from .views import AddEducation, GetEducation, DeleteEducation,UpdateEducation,CreateProfile,GetProfile,UpdateProfile,DeleteProfile

urlpatterns = [
    path("add-education/", AddEducation.as_view()),
    path("get-education/", GetEducation.as_view()),   # 🔥 remove user_id
    path("delete-education/<int:edu_id>/", DeleteEducation.as_view()),
    path("update-education/<int:edu_id>/", UpdateEducation.as_view()),
    path("create-profile/", CreateProfile.as_view()),
    path("get-profile/", GetProfile.as_view()),
    path("update-profile/", UpdateProfile.as_view()),
    path("delete-profile/", DeleteProfile.as_view()),
    #path("list/", GetApplications.as_view()),  # 🔥 THIS LINE

]