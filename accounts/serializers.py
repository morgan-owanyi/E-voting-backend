# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import EmailOTP

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("id","username","email","password","role")

    def create(self, validated_data):
        pwd = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(pwd)
        user.save()
        return user

class EmailOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class EmailOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=10)
