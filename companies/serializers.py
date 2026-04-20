from rest_framework import serializers
from .models import Company

from jobs.models import Job

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ['created_by']


# NEW SERIALIZER: We need this to get company specifics
class CompanyDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='company_name')
    # We create a placeholder field for other jobs; we'll populate this later
    other_jobs = serializers.SerializerMethodField()

    class Meta:
        model = Company
        # We need more specific fields than the generic serializer gave us
        fields = ['id', 'name', 'company_email', 'district', 'state', 'created_at', 'other_jobs']

    # This method finds other jobs posted by the SAME company
    def get_other_jobs(self, obj):
        # Find all jobs by this company, excluding the job we are currently looking at
        current_job_id = self.context.get('current_job_id')
        jobs = Job.objects.filter(company=obj).exclude(id=current_job_id)
        
        # Simple serialization of other jobs for the grid view
        other_jobs_list = []
        for job in jobs[:3]: # Limit to the first 3 jobs
            other_jobs_list.append({
                'id': job.id,
                'title': job.title,
                'location': job.location,
                'job_type': job.job_type,
            })
        return other_jobs_list