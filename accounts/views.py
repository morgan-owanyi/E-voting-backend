# accounts/views.py
# from rest_framework import generics, status
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from django.contrib.auth import get_user_model, authenticate
# from .serializers import UserRegisterSerializer, EmailOTPRequestSerializer, EmailOTPVerifySerializer, LoginSerializer
# from .models import EmailOTP
# from django.shortcuts import get_object_or_404
# from rest_framework.permissions import AllowAny
# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework_simplejwt.views import TokenObtainPairView
# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



# User = get_user_model()

# class RegisterView(generics.CreateAPIView):
#     serializer_class = UserRegisterSerializer
#     permission_classes = []  # allow anyone to register

#     def register(self, request, *args, **kwargs):
#         return super().create(request, *args, **kwargs)

# class RequestOTPView(generics.GenericAPIView):
#     serializer_class = EmailOTPRequestSerializer
#     permission_classes = []

#     def post(self, request, *args, **kwargs):
#         ser = self.get_serializer(data=request.data)
#         ser.is_valid(raise_exception=True)
#         email = ser.validated_data["email"]
#         user = User.objects.filter(email=email).first()
#         otp = EmailOTP.create_otp(email=email, user=user)
#         # NOTE: do not return otp.code in production. For now we return a message.
#         return Response({"detail": "OTP created and should be emailed (step 2)."}, status=status.HTTP_201_CREATED)

# class VerifyOTPView(generics.GenericAPIView):
#     serializer_class = EmailOTPVerifySerializer
#     permission_classes = []

#     def post(self, request, *args, **kwargs):
#         ser = self.get_serializer(data=request.data)
#         ser.is_valid(raise_exception=True)
#         email = ser.validated_data["email"]
#         code = ser.validated_data["code"]
#         otp = EmailOTP.objects.filter(email=email, code=code, used=False).order_by("-created_at").first()
#         if not otp or not otp.is_valid():
#             return Response({"detail":"Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
#         otp.mark_used()
#         if otp.user:
#             otp.user.is_email_verified = True
#             otp.user.save()
#         return Response({"detail":"Email verified."}, status=status.HTTP_200_OK)
# # In production, we shall also want to send the OTP code via email in RequestOTPView.


# class LoginView(APIView):
#     def post(self, request):
#         email = request.data.get("email")
#         password = request.data.get("password")

#         user = authenticate(request, email=email, password=password)

#         if user is None:
#             return Response(
#                 {"message": "Invalid credentials"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         refresh = RefreshToken.for_user(user)
#         return Response(
#             {
#                 "refresh": str(refresh),
#                 "access": str(refresh.access_token),
#             },
#             status=status.HTTP_200_OK,
#         )
    

# class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)
#         # Add custom claims if needed
#         token['email'] = user.email
#         token['role'] = user.role
#         return token

# class LoginView(TokenObtainPairView):
#     serializer_class = MyTokenObtainPairSerializer

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate
from .serializers import UserSerializer, LoginSerializer, RegisterSerializer

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            # Capture plain password before hashing
            plain_password = request.data.get('password', '')
            user = serializer.save()
            
            # Send welcome email to returning officers (async, non-blocking)
            if user.role == 'PRESIDING_OFFICER':
                import threading
                def send_email_async():
                    try:
                    email_body = f"""Hello {user.first_name or user.username},

Welcome to KuraVote!

Your account as a Returning Officer has been successfully created.

Login Credentials:
Email: {user.email}
Password: {plain_password}

Role: Returning Officer

You can now log in to the system at https://e-voting-frontend-tl80.onrender.com to manage elections and monitor voting activities.

Please change your password after your first login for security.

Thank you,
KuraVote Team"""
                    
                    send_mail(\n                        subject='Welcome to KuraVote - Returning Officer Account Created',\n                        message=email_body,\n                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kuravote.com'),\n                        recipient_list=[user.email],\n                        fail_silently=True,\n                        timeout=10  # Add timeout to prevent hanging\n                    )
                    except Exception:
                        pass  # Don't fail registration if email fails
                # Send email in background thread to avoid blocking
                threading.Thread(target=send_email_async, daemon=True).start()
            
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Authenticate user - EmailBackend expects 'email' parameter
            user = authenticate(request=request, email=email, password=password)
            
            if user:
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'token': token.key,
                    'user': UserSerializer(user).data
                })
            
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)




