from rest_framework import serializers
from .models import Salon, SalonImage, SalonService, BusinessHours

class BusinessHoursSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)
    
    class Meta:
        model = BusinessHours
        fields = ('id', 'weekday', 'weekday_display', 'opening_time', 'closing_time', 'is_closed')


class SalonImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalonImage
        fields = ('id', 'image', 'caption', 'order')


class SalonServiceSerializer(serializers.ModelSerializer):
    salon = serializers.UUIDField()
    
    class Meta:
        model = SalonService
        fields = ('id', 'salon', 'name', 'description', 'duration_minutes', 'price', 'is_active')


class SalonSerializer(serializers.ModelSerializer):
    images = SalonImageSerializer(many=True, read_only=True)
    services = SalonServiceSerializer(many=True, read_only=True)
    business_hours = BusinessHoursSerializer(many=True, read_only=True)
    manager_id = serializers.UUIDField(source='manager.id', read_only=True)

    class Meta:
        model = Salon
        fields = (
            'id', 'manager_id', 'name', 'slug', 'description', 'phone', 'email', 
            'address', 'city', 'country', 'latitude', 'longitude', 'logo', 
            'cover_image', 'opening_time', 'closing_time', 'gender_type', 
            'status', 'rating', 'images', 'services', 'business_hours', 'created_at'
        )
        read_only_fields = ('id', 'slug', 'rating', 'created_at', 'images', 'services', 'business_hours')
