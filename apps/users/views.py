from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema, inline_serializer

from .services import register_user, change_user_password, request_password_reset, reset_user_password
from .serializers import (
    RegisterSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    CustomUserSerializer,
    MeUpdateSerializer,
)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = CustomUserSerializer(self.user, context={"request": self.context.get("request")}).data
        return data

# login view
@extend_schema(
    tags=['auth'],
    request=inline_serializer(
        'LoginRequest',
        fields={
            'email': serializers.EmailField(),
            'password': serializers.CharField(write_only=True),
        },
    ),
    responses={
        200: inline_serializer(
            'LoginResponse',
            fields={
                'access': serializers.CharField(),
                'refresh': serializers.CharField(),
                'user': CustomUserSerializer(),
            },
        ),
    },
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=['auth'],
    responses={200: CustomUserSerializer()},
)
@extend_schema(
    methods=['PATCH'],
    tags=['auth'],
    request=MeUpdateSerializer,
    responses={200: CustomUserSerializer()},
)
class MeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(
            CustomUserSerializer(request.user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        serializer = MeUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(
            CustomUserSerializer(request.user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
        response.custom_message = "Profile updated successfully."
        return response


@extend_schema(
    tags=['auth'],
    request=RegisterSerializer,
    responses={
        201: inline_serializer(
            'RegisterResponse',
            fields={
                'user': CustomUserSerializer(),
                'tokens': inline_serializer(
                    'RegisterTokens',
                    fields={
                        'refresh': serializers.CharField(),
                        'access': serializers.CharField(),
                    },
                ),
            },
        ),
    },
)
class RegisterView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        role = validated_data.pop('role')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        phone = validated_data.pop('phone', '')
        profile_picture = validated_data.pop('profile_picture', None)

        user = register_user(
            email=email,
            password=password,
            role=role,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            profile_picture=profile_picture,
            **validated_data
        )
        
        refresh = RefreshToken.for_user(user)
        response_data = {
            "user": CustomUserSerializer(user, context={"request": request}).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }
        
        response = Response(response_data, status=status.HTTP_201_CREATED)
        response.custom_message = "User registered successfully."
        return response


@extend_schema(
    tags=['auth'],
    request=inline_serializer(
        'LogoutRequest',
        fields={'refresh': serializers.CharField()},
    ),
    responses={200: None},
)
class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            response = Response(status=status.HTTP_200_OK)
            response.custom_message = "Successfully logged out."
            return response
        except Exception:
            return Response({"detail": "Token is invalid or expired."}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['auth'],
    request=inline_serializer(
        'ChangePasswordRequest',
        fields={
            'old_password': serializers.CharField(write_only=True),
            'new_password': serializers.CharField(write_only=True, min_length=8),
        },
    ),
    responses={200: None},
)
class ChangePasswordView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        change_user_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"]
        )
        
        response = Response(status=status.HTTP_200_OK)
        response.custom_message = "Password changed successfully."
        return response


@extend_schema(
    tags=['auth'],
    request=inline_serializer(
        'PasswordResetRequest',
        fields={'email': serializers.EmailField()},
    ),
    responses={
        200: inline_serializer(
            'PasswordResetResponse',
            fields={
                'uidb64': serializers.CharField(),
                'token': serializers.CharField(),
            },
        ),
    },
)
class PasswordResetRequestView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uid, token = request_password_reset(serializer.validated_data["email"])
        
        # Include token/uid in response for debug/testing ease.
        data = {}
        if uid and token:
            data = {"uidb64": uid, "token": token}
            
        response = Response(data, status=status.HTTP_200_OK)
        response.custom_message = "If the email exists, a password reset link has been generated."
        return response


@extend_schema(
    tags=['auth'],
    request=inline_serializer(
        'PasswordResetConfirmRequest',
        fields={
            'uidb64': serializers.CharField(),
            'token': serializers.CharField(),
            'new_password': serializers.CharField(write_only=True, min_length=8),
        },
    ),
    responses={200: None},
)
class PasswordResetConfirmView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reset_user_password(
            uidb64=serializer.validated_data["uidb64"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"]
        )
        
        response = Response(status=status.HTTP_200_OK)
        response.custom_message = "Password has been reset successfully."
        return response
