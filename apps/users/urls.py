from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    MeView,
    LogoutView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='auth_login'),
    path('me/', MeView.as_view(), name='auth_me'),
    path('refresh/', TokenRefreshView.as_view(), name='auth_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('password/change/', ChangePasswordView.as_view(), name='auth_change_password'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='auth_password_reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='auth_password_reset_confirm'),
]
