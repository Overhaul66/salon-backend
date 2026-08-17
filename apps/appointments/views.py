from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter, OpenApiTypes

from apps.users.permissions import IsSalonManager, IsSalonEmployee
from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentCancelSerializer,
    AppointmentStatusUpdateSerializer
)
from .services import create_appointment, cancel_appointment, update_appointment_status
from .selectors import get_customer_appointments, get_employee_appointments, get_manager_dashboard_data
from .permissions import AppointmentAccessPermission

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = (permissions.IsAuthenticated, AppointmentAccessPermission)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('salon', 'employee', 'status', 'appointment_date')
    tags = ['appointments']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return super().get_queryset()
            
        if user.role == 'CUSTOMER' and hasattr(user, 'customer_profile'):
            return get_customer_appointments(user.customer_profile)
            
        if user.role == 'SALON_EMPLOYEE' and hasattr(user, 'employee_profile'):
            return get_employee_appointments(user.employee_profile)
            
        if user.role == 'SALON_MANAGER' and hasattr(user, 'manager_profile'):
            from apps.salons.models import Salon
            salons = Salon.objects.filter(manager=user.manager_profile)
            return Appointment.objects.filter(salon__in=salons)
            
        return Appointment.objects.none()
        
    @extend_schema(
        request=AppointmentCreateSerializer,
        responses={201: AppointmentSerializer},
    )
    def create(self, request, *args, **kwargs):
        if request.user.role != 'CUSTOMER' or not hasattr(request.user, 'customer_profile'):
            return Response({"detail": "Only customers can book appointments."}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        customer = request.user.customer_profile
        validated_data = serializer.validated_data
        
        try:
            appointment = create_appointment(
                customer=customer,
                salon=validated_data['salon'],
                service=validated_data['service'],
                date=validated_data['appointment_date'],
                start_time=validated_data['start_time'],
                booking_notes=validated_data.get('booking_notes', '')
            )
        except DjangoValidationError as e:
            return Response(
                {"detail": "; ".join(e.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        response_serializer = self.get_serializer(appointment)
        response = Response(response_serializer.data, status=status.HTTP_201_CREATED)
        response.custom_message = "Appointment booked successfully."
        return response
        
    @extend_schema(
        request=AppointmentCancelSerializer,
        responses={200: AppointmentSerializer},
    )
    @action(detail=True, methods=['patch'], url_path='cancel', permission_classes=[permissions.IsAuthenticated, AppointmentAccessPermission])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cancelled = cancel_appointment(appointment, serializer.validated_data['cancel_reason'])
        response = Response(self.get_serializer(cancelled).data)
        response.custom_message = "Appointment cancelled successfully."
        return response


@extend_schema(
    tags=['manager'],
    responses={
        200: inline_serializer(
            'ManagerDashboardResponse',
            fields={
                'today_summary': inline_serializer(
                    'TodaySummary',
                    fields={
                        'pending': serializers.IntegerField(),
                        'confirmed': serializers.IntegerField(),
                        'completed': serializers.IntegerField(),
                        'revenue': serializers.DecimalField(max_digits=12, decimal_places=2),
                    },
                ),
                'total_revenue': serializers.DecimalField(max_digits=12, decimal_places=2),
                'salons_count': serializers.IntegerField(),
                'recent_appointments': AppointmentSerializer(many=True),
            },
        ),
    },
)
class ManagerDashboardView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsSalonManager)
    
    def get(self, request):
        manager = request.user.manager_profile
        data = get_manager_dashboard_data(manager)
        
        recent_serializer = AppointmentSerializer(data['recent_appointments'], many=True)
        data['recent_appointments'] = recent_serializer.data
        
        response = Response(data)
        response.custom_message = "Dashboard metrics fetched successfully."
        return response


@extend_schema(
    tags=['my'],
    parameters=[OpenApiParameter('date', OpenApiTypes.DATE, description='Filter by date (YYYY-MM-DD).')],
    responses={200: AppointmentSerializer(many=True)},
)
class EmployeeAppointmentsView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsSalonEmployee)
    
    def get(self, request):
        employee = request.user.employee_profile
        date_str = request.query_params.get('date')
        date = None
        if date_str:
            date = parse_date(date_str)
            
        appointments = get_employee_appointments(employee, date)
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=['my'],
    request=AppointmentStatusUpdateSerializer,
    responses={200: AppointmentSerializer},
)
class EmployeeAppointmentStatusView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsSalonEmployee)
    
    def patch(self, request, pk=None):
        try:
            employee = request.user.employee_profile
            appointment = Appointment.objects.get(id=pk, employee=employee)
        except Appointment.DoesNotExist:
            return Response({"detail": "Appointment not found or not assigned to you."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = AppointmentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated = update_appointment_status(appointment, serializer.validated_data['status'])
        response = Response(AppointmentSerializer(updated).data)
        response.custom_message = f"Appointment status updated to {updated.status}."
        return response
