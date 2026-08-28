import datetime
from rest_framework import serializers
from .models import Appointment
from apps.salons.models import Salon, SalonService
from apps.users.serializers import CustomerSerializer, SalonEmployeeSerializer
from apps.salons.serializers import SalonSerializer, SalonServiceSerializer

class AppointmentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    salon = SalonSerializer(read_only=True)
    employee = SalonEmployeeSerializer(read_only=True)
    service = SalonServiceSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id', 'customer', 'salon', 'employee', 'service', 
            'appointment_date', 'start_time', 'end_time', 'status', 
            'booking_notes', 'cancel_reason', 'created_at'
        )
        read_only_fields = fields


class AppointmentCreateSerializer(serializers.Serializer):
    salon_id = serializers.PrimaryKeyRelatedField(queryset=Salon.objects.filter(status='ACTIVE'), source='salon')
    service_id = serializers.PrimaryKeyRelatedField(queryset=SalonService.objects.filter(is_active=True), source='service')
    appointment_date = serializers.DateField()
    start_time = serializers.TimeField()
    booking_notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        salon = attrs['salon']
        service = attrs['service']
        if service.salon != salon:
            raise serializers.ValidationError({"service_id": "This service does not belong to the selected salon."})
        
        today = datetime.date.today()
        now_time = datetime.datetime.now().time()
        if attrs['appointment_date'] < today:
            raise serializers.ValidationError({"appointment_date": "Cannot book appointments in the past."})
        elif attrs['appointment_date'] == today and attrs['start_time'] <= now_time:
            raise serializers.ValidationError({"start_time": "Cannot book appointments in the past."})
            
        return attrs


class AppointmentCancelSerializer(serializers.Serializer):
    cancel_reason = serializers.CharField(required=True, min_length=5)


class AppointmentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[('CONFIRMED', 'Confirmed'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed'), ('NO_SHOW', 'No Show'), ('DECLINED', 'Declined')])
