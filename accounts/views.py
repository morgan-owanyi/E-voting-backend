# accounts/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model, authenticate
from .serializers import UserRegisterSerializer, EmailOTPRequestSerializer, EmailOTPVerifySerializer, LoginSerializer
from .models import EmailOTP
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



User = get_user_model()

class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = []  # allow anyone to register

    def register(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

class RequestOTPView(generics.GenericAPIView):
    serializer_class = EmailOTPRequestSerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        user = User.objects.filter(email=email).first()
        otp = EmailOTP.create_otp(email=email, user=user)
        # NOTE: do not return otp.code in production. For now we return a message.
        return Response({"detail": "OTP created and should be emailed (step 2)."}, status=status.HTTP_201_CREATED)

class VerifyOTPView(generics.GenericAPIView):
    serializer_class = EmailOTPVerifySerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        code = ser.validated_data["code"]
        otp = EmailOTP.objects.filter(email=email, code=code, used=False).order_by("-created_at").first()
        if not otp or not otp.is_valid():
            return Response({"detail":"Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
        otp.mark_used()
        if otp.user:
            otp.user.is_email_verified = True
            otp.user.save()
        return Response({"detail":"Email verified."}, status=status.HTTP_200_OK)
# In production, we shall also want to send the OTP code via email in RequestOTPView.


class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(request, email=email, password=password)

        if user is None:
            return Response(
                {"message": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )
    

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims if needed
        token['email'] = user.email
        token['role'] = user.role
        return token

class LoginView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

