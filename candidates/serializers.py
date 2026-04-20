
from rest_framework import serializers
from .models import Education, CandidateProfile


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            'id',
            'level',
            'institution_name',
            'degree',
            'percentage',
            'city'
        ]


class CandidateProfileSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, read_only=True, source='user.educations')
    resume = serializers.FileField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = CandidateProfile
        fields = ['id', 'phone', 'skills', 'resume', 'created_at', 'educations']
        # Add this to allow CreateProfile to work with partial data for new users
        extra_kwargs = {
            'phone': {'required': False, 'allow_blank': True},
            'skills': {'required': False, 'allow_blank': True},
        }