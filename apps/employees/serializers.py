from rest_framework import serializers
from apps.users.models import SalonEmployee
from apps.salons.models import Salon, SalonService

class ManageEmployeeSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    phone = serializers.CharField(source='user.phone', required=False, allow_blank=True)
    is_active = serializers.BooleanField(source='user.is_active', required=False)
    salon_name = serializers.CharField(source='salon.name', read_only=True)
    services = serializers.PrimaryKeyRelatedField(many=True, queryset=SalonService.objects.all(), required=False)
    service_names = serializers.SerializerMethodField(read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)

    class Meta:
        model = SalonEmployee
        fields = (
            'id', 'email', 'first_name', 'last_name', 'phone', 'salon', 
            'salon_name', 'profile_picture', 'position', 'services', 'service_names', 'bio', 'is_available', 'employment_date', 
            'is_active', 'created_at'
        )
        read_only_fields = ('id', 'email', 'created_at')

    def get_service_names(self, obj):
        return list(obj.services.values_list('name', flat=True))


class CreateEmployeeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, default="", allow_blank=True)
    last_name = serializers.CharField(required=False, default="", allow_blank=True)
    phone = serializers.CharField(required=False, default="", allow_blank=True)
    salon_id = serializers.PrimaryKeyRelatedField(queryset=Salon.objects.all(), source='salon')
    service_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=SalonService.objects.all(), source='services', required=False)
    bio = serializers.CharField(required=False, default="", allow_blank=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)


class ResetEmployeePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
