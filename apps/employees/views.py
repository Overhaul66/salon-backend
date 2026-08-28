from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema

from apps.users.permissions import IsSalonManager
from apps.users.models import SalonEmployee
from .serializers import ManageEmployeeSerializer, CreateEmployeeSerializer, ResetEmployeePasswordSerializer
from .services import create_salon_employee, update_salon_employee, reset_employee_password
from .selectors import list_employees_for_manager

class EmployeeManagementViewSet(viewsets.ModelViewSet):
    serializer_class = ManageEmployeeSerializer
    permission_classes = (permissions.IsAuthenticated, IsSalonManager)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('salon', 'is_available')
    tags = ['employees']
    
    def get_queryset(self):
        manager = self.request.user.manager_profile
        return list_employees_for_manager(manager)
        
    @extend_schema(
        request=CreateEmployeeSerializer,
        responses={201: ManageEmployeeSerializer},
    )
    def create(self, request, *args, **kwargs):
        manager = request.user.manager_profile
        serializer = CreateEmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        
        try:
            employee = create_salon_employee(
                manager=manager,
                email=validated_data['email'],
                password=validated_data['password'],
                salon=validated_data['salon'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                phone=validated_data.get('phone', ''),
                bio=validated_data.get('bio', ''),
                services=validated_data.get('services'),
                profile_picture=validated_data.get('profile_picture')
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        response_serializer = self.get_serializer(employee)
        response = Response(response_serializer.data, status=status.HTTP_201_CREATED)
        response.custom_message = "Employee account created successfully."
        return response
        
    def perform_update(self, serializer):
        manager = self.request.user.manager_profile
        employee = self.get_object()
        
        validated_data = serializer.validated_data
        
        # Flatten user nested parameters
        user_data = validated_data.pop('user', {})
        for k, v in user_data.items():
            validated_data[k] = v
            
        updated = update_salon_employee(manager, employee, **validated_data)
        serializer.instance = updated
        
    @extend_schema(
        request=ResetEmployeePasswordSerializer,
        responses={200: None},
    )
    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        manager = request.user.manager_profile
        employee = self.get_object()
        serializer = ResetEmployeePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reset_employee_password(manager, employee, serializer.validated_data['password'])
        response = Response(status=status.HTTP_200_OK)
        response.custom_message = "Employee password has been reset successfully."
        return response
