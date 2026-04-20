from django.urls import path
from .views import (
    CreateCompany,
    GetCompanies,
    GetSingleCompany,
    UpdateCompany,
    DeleteCompany,
    CompanyDetailView,
)

urlpatterns = [
    path("create/", CreateCompany.as_view()),
    path("list/", GetCompanies.as_view()),
    path("detail/<int:company_id>/", GetSingleCompany.as_view()),
    path("update/<int:company_id>/", UpdateCompany.as_view()),
    path("delete/<int:company_id>/", DeleteCompany.as_view()),
    path('detail/<int:id>/', CompanyDetailView.as_view(), name='company-detail'),
]