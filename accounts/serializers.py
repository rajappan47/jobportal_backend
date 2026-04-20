from rest_framework import serializers
from .models import User
from django.contrib.auth.hashers import make_password

class UserRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'password', 'confirm_password', 'role']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        # 1. Password & Confirm Password match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})

        # 2. Email validation
        if "@" not in data['email']:
            raise serializers.ValidationError({"email": "Invalid email format"})

        # 3. Phone validation
        if len(data['phone']) != 10:
            raise serializers.ValidationError({"phone": "Phone number must be 10 digits"})

        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')

        # Hash password before saving
        validated_data['password'] = make_password(validated_data['password'])

        return User.objects.create(**validated_data)