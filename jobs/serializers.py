from rest_framework import serializers
from .models import Job

#class JobSerializer(serializers.ModelSerializer):
    # We map the 'company_name' field from your Company model
    # source='company.company_name' links: Job -> Company -> company_name
    #display_company_name = serializers.ReadOnlyField(source='company.company_name')

    #class Meta:
        #model = Job
        #fields = [
            #'id', 'company', 'display_company_name', 'title', 'description', 
            #'required_skills', 'experience', 'location', 'job_type', 
            #'created_at', 'deadline'
        #]
        #read_only_fields = ['posted_by']

# Import the new serializer
from companies.serializers import CompanyDetailSerializer

class JobSerializer(serializers.ModelSerializer):
    # Old field we kept for compatibility
    company_name = serializers.ReadOnlyField(source='company.company_name')

    # 🚀 NEW FILED: This is the nested dynamic company detail object
    company_details = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'company', 'company_name', 'company_details', 'title', 
            'description', 'location', 'job_type', 'required_skills', 
            'experience', 'created_at', 'deadline'
        ]
        read_only_fields = ['posted_by']

    # 🚀 METHOD: This logic populates 'company_details' with the dynamic data
    def get_company_details(self, obj):
        company = obj.company
        serializer = CompanyDetailSerializer(
            company, 
            context={'current_job_id': obj.id}
        )
        return serializer.data


