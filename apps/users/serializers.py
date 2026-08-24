from rest_framework import serializers
from .models import CustomUser, Customer, SalonEmployee, SalonManager

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'profile_picture', 'role', 'is_active', 'is_verified', 'created_at', 'updated_at')
        read_only_fields = ('id', 'role', 'is_active', 'is_verified', 'created_at', 'updated_at')


class CustomerSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    
    class Meta:
        model = Customer
        fields = ('id', 'user', 'date_of_birth', 'gender', 'preferred_notification', 'created_at')


class SalonEmployeeSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    salon_name = serializers.CharField(source='salon.name', read_only=True)
    
    class Meta:
        model = SalonEmployee
        fields = ('id', 'user', 'salon', 'salon_name', 'position', 'bio', 'is_available', 'employment_date', 'created_at')


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, default="", allow_blank=True)
    last_name = serializers.CharField(required=False, default="", allow_blank=True)
    phone = serializers.CharField(required=False, default="", allow_blank=True)
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    
    # Profile fields (optional)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=Customer.GENDER_CHOICES, required=False, allow_null=True)
    preferred_notification = serializers.ChoiceField(choices=Customer.NOTIFICATION_CHOICES, required=False, default='EMAIL')

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone(self, value):
        # Blank phones are allowed (field is optional) - only check real numbers
        if value and CustomUser.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value
    


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
