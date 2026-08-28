from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Salon, SalonImage, SalonService, BusinessHours, ServiceCatalog
from apps.common.fields import Base64ImageField

class ServiceCatalogSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = ServiceCatalog
        fields = ('id', 'name', 'description', 'duration_minutes', 'price', 'category', 'category_display', 'is_active')


class BusinessHoursSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = BusinessHours
        fields = ('id', 'weekday', 'weekday_display', 'opening_time', 'closing_time', 'is_closed')


class BusinessHoursCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessHours
        fields = ('weekday', 'opening_time', 'closing_time', 'is_closed')

    def validate(self, attrs):
        weekday = attrs.get('weekday')
        is_closed = attrs.get('is_closed', False)
        opening_time = attrs.get('opening_time')
        closing_time = attrs.get('closing_time')

        if weekday is None or weekday < 0 or weekday > 6:
            raise ValidationError({'weekday': 'Weekday must be between 0 and 6.'})

        if not is_closed and (opening_time is None or closing_time is None):
            raise ValidationError('Opening and closing times are required when the salon is open.')

        if is_closed:
            attrs['opening_time'] = opening_time or '00:00:00'
            attrs['closing_time'] = closing_time or '00:00:00'

        return attrs


class SalonImageSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = SalonImage
        fields = ('id', 'image', 'caption', 'order')


class SalonServiceSerializer(serializers.ModelSerializer):
    salon = serializers.PrimaryKeyRelatedField(queryset=Salon.objects.all())
    catalog_item = serializers.PrimaryKeyRelatedField(queryset=ServiceCatalog.objects.filter(is_active=True), required=False, allow_null=True)
    category = serializers.CharField(source='catalog_item.category', read_only=True, default='')
    category_display = serializers.CharField(source='catalog_item.get_category_display', read_only=True, default='')

    class Meta:
        model = SalonService
        fields = ('id', 'salon', 'catalog_item', 'name', 'description', 'duration_minutes', 'price', 'is_active', 'category', 'category_display')


class SalonSerializer(serializers.ModelSerializer):
    images = SalonImageSerializer(many=True, read_only=True)
    services = SalonServiceSerializer(many=True, read_only=True)
    business_hours = BusinessHoursSerializer(many=True, read_only=True)
    manager_id = serializers.UUIDField(source='manager.id', read_only=True)
    is_favourited = serializers.SerializerMethodField(read_only=True)
    logo = Base64ImageField(required=False, allow_null=True)
    cover_image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Salon
        fields = (
            'id', 'manager_id', 'name', 'slug', 'description', 'phone',
            'address', 'city', 'country', 'latitude', 'longitude', 'logo',
            'cover_image', 'opening_time', 'closing_time', 'gender_type',
            'status', 'rating', 'images', 'services', 'business_hours',
            'is_favourited', 'created_at'
        )
        read_only_fields = ('id', 'slug', 'rating', 'created_at', 'images', 'services', 'business_hours', 'is_favourited')

    def get_is_favourited(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'customer_profile'):
            return False
        return obj.favourited_by.filter(customer=request.user.customer_profile).exists()

    def validate(self, attrs):
        return super().validate(attrs)


class SalonCreateSerializer(SalonSerializer):
    business_hours = BusinessHoursCreateSerializer(many=True, required=False)

    class Meta(SalonSerializer.Meta):
        read_only_fields = ('id', 'slug', 'rating', 'created_at', 'images', 'services')

    def validate_business_hours(self, value):
        seen = set()
        for item in value:
            weekday = item.get('weekday')
            if weekday in seen:
                raise ValidationError(f'Duplicate weekday entry for {weekday}.')
            seen.add(weekday)
        return value

    def create(self, validated_data):
        business_hours = validated_data.pop('business_hours', [])
        salon = super().create(validated_data)
        for item in business_hours:
            BusinessHours.objects.update_or_create(
                salon=salon,
                weekday=item['weekday'],
                defaults={
                    'opening_time': item.get('opening_time'),
                    'closing_time': item.get('closing_time'),
                    'is_closed': item.get('is_closed', False),
                }
            )
        return salon

    def update(self, instance, validated_data):
        business_hours = validated_data.pop('business_hours', None)
        salon = super().update(instance, validated_data)
        if business_hours is not None:
            for item in business_hours:
                BusinessHours.objects.update_or_create(
                    salon=salon,
                    weekday=item['weekday'],
                    defaults={
                        'opening_time': item.get('opening_time'),
                        'closing_time': item.get('closing_time'),
                        'is_closed': item.get('is_closed', False),
                    }
                )
        return salon
